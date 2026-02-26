"""
create_order Lambda: 创建订单，写入 RDS，发送 careplan_id 到 SQS
"""
import json
import os
import ssl
import pg8000
import boto3

DB_CONFIG = {
    "host": os.environ["DB_HOST"],
    "port": int(os.environ["DB_PORT"]),
    "database": os.environ["DB_NAME"],
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
    "ssl_context": ssl.create_default_context(),
}

SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]


def get_conn():
    return pg8000.connect(**DB_CONFIG)


def ensure_schema(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS careplan_patient (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            mrn VARCHAR(6) UNIQUE NOT NULL,
            dob DATE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS careplan_provider (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200),
            npi VARCHAR(10) UNIQUE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS careplan_careplan (
            id SERIAL PRIMARY KEY,
            patient_id INT NOT NULL REFERENCES careplan_patient(id),
            provider_id INT NOT NULL REFERENCES careplan_provider(id),
            primary_diagnosis VARCHAR(50),
            additional_diagnosis TEXT DEFAULT '',
            medication_name VARCHAR(200),
            medication_history TEXT DEFAULT '',
            patient_records TEXT NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            generated_content TEXT DEFAULT '',
            error_message TEXT DEFAULT '',
            llm_provider VARCHAR(50) DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    conn.commit()


def handler(event, context):
    try:
        return _handle(event)
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"success": False, "message": str(e), "error_type": type(e).__name__}),
        }


def _handle(event):
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"success": False, "message": "Invalid JSON"}),
        }

    required = ["patient_mrn", "patient_first_name", "patient_last_name", "patient_dob",
                "provider_npi", "provider_name", "primary_diagnosis", "medication_name", "patient_records"]
    for k in required:
        if not body.get(k):
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"success": False, "message": f"Missing field: {k}"}),
            }

    conn = get_conn()
    try:
        ensure_schema(conn)
        cur = conn.cursor()

        # Get or create provider
        cur.execute("SELECT id FROM careplan_provider WHERE npi = %s", (body["provider_npi"],))
        rows = cur.fetchall()
        if rows:
            provider_id = rows[0][0]
        else:
            cur.execute(
                "INSERT INTO careplan_provider (name, npi) VALUES (%s, %s) RETURNING id",
                (body["provider_name"], body["provider_npi"]),
            )
            provider_id = cur.fetchone()[0]

        # Get or create patient
        cur.execute("SELECT id FROM careplan_patient WHERE mrn = %s", (body["patient_mrn"],))
        rows = cur.fetchall()
        if rows:
            patient_id = rows[0][0]
        else:
            cur.execute(
                "INSERT INTO careplan_patient (first_name, last_name, mrn, dob) VALUES (%s, %s, %s, %s) RETURNING id",
                (body["patient_first_name"], body["patient_last_name"], body["patient_mrn"], body["patient_dob"]),
            )
            patient_id = cur.fetchone()[0]

        # Create careplan
        cur.execute(
            """INSERT INTO careplan_careplan
               (patient_id, provider_id, primary_diagnosis, additional_diagnosis, medication_name,
                medication_history, patient_records, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
               RETURNING id""",
            (
                patient_id,
                provider_id,
                body["primary_diagnosis"],
                body.get("additional_diagnosis", ""),
                body["medication_name"],
                body.get("medication_history", ""),
                body["patient_records"],
            ),
        )
        careplan_id = cur.fetchone()[0]
        conn.commit()

        # Send to SQS
        sqs = boto3.client("sqs")
        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps({"careplan_id": careplan_id}),
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "data": {"id": careplan_id, "status": "pending", "message": "Order created"},
            }),
        }
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()
