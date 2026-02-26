"""
get_order Lambda: 查询订单，返回 careplan 详情
"""
import json
import os
import ssl
import pg8000

DB_CONFIG = {
    "host": os.environ["DB_HOST"],
    "port": int(os.environ["DB_PORT"]),
    "database": os.environ["DB_NAME"],
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
    "ssl_context": ssl.create_default_context(),
}


def get_conn():
    return pg8000.connect(**DB_CONFIG)


def handler(event, context):
    path_params = event.get("pathParameters") or {}
    order_id = path_params.get("id")
    if not order_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"success": False, "message": "Missing id"}),
        }

    try:
        order_id = int(order_id)
    except ValueError:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"success": False, "message": "Invalid id"}),
        }

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT c.id, c.status, c.generated_content, c.error_message, c.medication_name, c.created_at,
                      p.first_name, p.last_name, p.mrn
               FROM careplan_careplan c
               JOIN careplan_patient p ON c.patient_id = p.id
               WHERE c.id = %s""",
            (order_id,),
        )
        row = cur.fetchone()
        if not row:
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"success": False, "message": "Order not found"}),
            }

        # row: (id, status, generated_content, error_message, medication_name, created_at, first_name, last_name, mrn)
        data = {
            "id": row[0],
            "status": row[1],
            "medication_name": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
            "patient": {
                "first_name": row[6],
                "last_name": row[7],
                "mrn": row[8],
            },
        }
        if row[1] == "completed":
            data["content"] = row[2]
        elif row[1] == "failed":
            data["error"] = (row[3] or "Generation failed")

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"success": True, "data": data}),
        }
    finally:
        conn.close()
