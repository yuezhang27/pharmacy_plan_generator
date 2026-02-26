# Terraform - AWS 一键部署

将 Pharmacy Care Plan 部署到 AWS：RDS PostgreSQL + SQS + Lambda + API Gateway。

## 前置条件

- AWS CLI 已配置（`aws configure`）
- Terraform >= 1.0
- Python 3.11+（用于构建 Lambda 包）

## 部署步骤

### 1. 配置变量

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# 编辑 terraform.tfvars，设置 db_password 等
```

### 2. 构建 Lambda 包（每次修改 Lambda 代码后必须执行）

```bash
cd terraform
python scripts/build_lambdas.py
```

### 3. 初始化与部署

```bash
terraform init
terraform plan
terraform apply
```

### 4. 获取 API URL

```bash
terraform output api_url
# 示例: https://xxxxxx.execute-api.us-east-1.amazonaws.com
```

### 5. Postman 测试

**创建订单**

```
POST {api_url}/orders
Content-Type: application/json

{
  "patient_mrn": "M001",
  "patient_first_name": "John",
  "patient_last_name": "Doe",
  "patient_dob": "1990-01-15",
  "provider_npi": "1234567890",
  "provider_name": "Dr. Smith",
  "primary_diagnosis": "Hypertension",
  "medication_name": "Lisinopril",
  "patient_records": "Patient history..."
}
```

响应示例：`{"success": true, "data": {"id": 1, "status": "pending", "message": "Order created"}}`

**查询订单**（等待 5–15 秒让 SQS 触发生成）

```
GET {api_url}/orders/1
```

响应示例：`{"success": true, "data": {"id": 1, "status": "completed", "content": "=== Care Plan (Mock) ===", ...}}`

## 架构

```
POST /orders  →  create_order Lambda  →  RDS (插入) + SQS (发送 careplan_id)
                                              ↓
GET /orders/{id}  ←  get_order Lambda  ←  SQS  →  generate_careplan Lambda  →  RDS (更新)
```

- **SQS DLQ**：消息处理失败 3 次后进入 Dead Letter Queue
- **RDS**：db.t3.micro，数据库名 `careplan`
- **Lambda**：首次创建订单时自动建表（careplan_patient, careplan_provider, careplan_careplan）

## 销毁

```bash
terraform destroy
```
