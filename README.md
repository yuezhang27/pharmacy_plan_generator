# Pharmacy Care Plan Generator - MVP

最小可运行的 MVP 版本，包含前端、后端、PostgreSQL 数据库和 LLM 生成 care plan 的功能。

## 功能

- 前端表单输入患者、提供者、诊断和药物信息
- 后端 Django API 接收数据并生成 care plan
- PostgreSQL 数据库存储数据
- LLM (OpenAI) 生成 care plan
- Care plan 状态管理：pending → processing → completed/failed
- 只有 completed 状态时前端才显示 care plan
- 生成后的 care plan 可下载为文本文件
- 支持简单的 care plan 搜索与 CSV 报表导出（用于 pharma/compliance 报告）

## 运行步骤

### 1. 准备环境变量

**方式一：使用系统环境变量（推荐，如果已配置）**

如果你已经在系统环境变量中配置了 `OPENAI_API_KEY`，则无需创建 `.env` 文件。代码会自动从系统环境变量读取。

**方式二：使用 .env 文件**

如果使用 Docker 或想使用 `.env` 文件，可以创建 `.env` 文件（参考 `.env.example`）：

```bash
OPENAI_API_KEY=your_openai_api_key_here
POSTGRES_DB=pharmacy_db
POSTGRES_USER=pharmacy_user
POSTGRES_PASSWORD=pharmacy_pass
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

**注意**：

- 代码会优先从系统环境变量读取 `OPENAI_API_KEY`
- 如果系统环境变量已配置，则无需 `.env` 文件
- 使用 Docker 时，如果系统环境变量已配置，docker-compose.yml 会自动传递（通过 `${OPENAI_API_KEY}`）

### 2. 使用 Docker Compose 运行

```bash
# 启动服务（包括数据库和 web 服务）
docker-compose up --build

# 或者后台运行
docker-compose up -d --build
```

### 3. 初始化数据库

在另一个终端窗口中，运行数据库迁移：

```bash
# 等待几秒让数据库完全启动，然后创建迁移文件
docker-compose exec web python manage.py makemigrations

# 运行迁移
docker-compose exec web python manage.py migrate

# 创建超级用户（可选，用于访问 admin 界面）
docker-compose exec web python manage.py createsuperuser
```

### 4. 访问应用

- 前端界面：http://localhost:8000
- Admin 界面：http://localhost:8000/admin

## 使用说明

1. 打开浏览器访问 http://localhost:8000
2. 填写表单信息：
   - 患者信息（姓名、MRN、DOB）
   - 提供者信息（姓名、NPI）
   - 诊断信息（主要诊断、附加诊断）
   - 药物信息（药物名称、药物历史）
   - 患者记录（文本内容）
3. 点击 "Generate Care Plan" 按钮
4. 等待 LLM 生成 care plan（同步等待）
5. 生成完成后，页面会显示生成的 care plan，并提供「Download Care Plan」按钮下载文本文件
6. 页面下方的「Search & Export Care Plans」区域可以：
   - 根据患者姓名 / MRN / 提供者 / 药物 / 诊断进行简单搜索（仅搜索已 completed 的 care plan）
   - 点击「Export CSV」导出当前搜索条件下的 care plan 报表（CSV），包含：
     - 患者标识（MRN、姓名、DOB）
     - 提供者标识（姓名、NPI）
     - 药物、主要诊断
     - care plan 生成时间戳
     - duplication warning 占位列（目前未实现实际逻辑）

## Patient 重复检测原则

- **MRN 已存在，但输入的姓名或 DOB 与现有记录不一致**：即使用户选择「继续」，系统仍以**原有 MRN 关联的既有人口学信息**为准（MRN 是患者唯一标识符）。
- **输入的姓名或 DOB 与现有某人记录一致，但 MRN 不同**：用户选择「继续」时，系统以**新 MRN 关联的新人口学信息**为准，创建一条姓名和 DOB 相同、MRN 不同的新记录（可能是同名同生日不同人）。

## 项目结构

```
pharmacy_plan_generator/
├── careplan/              # Django app
│   ├── models.py         # 数据模型（Patient, Provider, CarePlan）
│   ├── views.py          # API 视图
│   ├── llm_service.py    # LLM 生成服务
│   └── templates/        # HTML 模板
├── pharmacy_plan/        # Django 项目配置
│   ├── settings.py       # 设置
│   └── urls.py           # URL 路由
├── docker-compose.yml    # Docker Compose 配置
├── Dockerfile            # Docker 镜像配置
└── requirements.txt      # Python 依赖
```

## 注意事项

- 这是一个最小 MVP，没有包含验证、错误处理、测试等
- 使用同步方式生成 care plan，会阻塞请求直到完成
- 需要有效的 OpenAI API key 才能生成 care plan
- 数据库数据会持久化在 Docker volume 中

## 运行测试

使用 Docker 运行单元测试和集成测试：

```bash
# 确保 Docker Desktop 已启动，然后运行
docker-compose run --rm test
```

测试包括：

- **Patient 重复检测**：`careplan/tests/test_duplication_patient.py`（目标 90% 覆盖率）
- **Provider/Order 重复检测**：`careplan/tests/test_duplication_provider_order.py`
- **错误处理**：`careplan/tests/test_errors.py`（验证错误输入产生对应错误响应）
- **集成测试**：`careplan/tests/test_integration.py`（完整 API 流程）

本地运行（需 PostgreSQL 或设置 `USE_SQLITE_FOR_TESTS=1`）：

```bash
USE_SQLITE_FOR_TESTS=1 pytest careplan/tests/
```

## Prometheus + Grafana 监控

项目已集成 Prometheus 和 Grafana，用于监控业务指标、性能指标和错误指标。

### 启动监控服务

```bash
# 启动全部服务（含 Prometheus、Grafana）
docker-compose up -d --build

# 或只启动监控相关服务
docker-compose up -d web celery_worker prometheus grafana
```

### 连接与访问

| 服务 | 地址 | 说明 |
|------|------|------|
| **Prometheus** | http://localhost:9091 | 抓取 web:8000/metrics 和 celery_worker:9090/metrics |
| **Grafana** | http://localhost:3000 | 默认账号 admin / admin |
| **Web metrics** | http://localhost:8000/metrics | Django 应用指标 |
| **StatsD exporter** | http://localhost:9102/metrics | Worker 指标（经 StatsD UDP 聚合） |

### Grafana 配置

1. 打开 http://localhost:3000，登录 admin / admin
2. 数据源已自动配置为 Prometheus（http://prometheus:9090）
3. 仪表盘 **Pharmacy Care Plan 监控** 已自动加载，可在左侧 Dashboards 中查看

### 指标说明

- **业务**：careplan_submitted_total、careplan_completed_total、careplan_failed_total、完成率、duplication_block/warning、llm_provider_usage
- **性能**：API 响应时间 P95（generate/status/search）、Celery 任务耗时、LLM 调用耗时
- **错误**：http_5xx/4xx、validation_error、block_error、celery_task_failure/retry、llm_api_error

详见 `DASHBOARD_METRICS.md`。

## 停止服务

```bash
docker-compose down
```

如果要删除数据库数据：

```bash
docker-compose down -v
```

---

## AWS Terraform 部署（按需使用）

将 Care Plan 部署到 AWS：RDS PostgreSQL + SQS + Lambda + API Gateway。适用于需要云端部署、Postman 测试完整流程的场景。

### 前置条件

- AWS CLI 已配置（`aws configure`）
- Terraform >= 1.0
- Python 3.11+（用于构建 Lambda 包）

### 未来每次需要部署时的完整流程

#### 1. 配置变量

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# 编辑 terraform.tfvars，设置 db_password（必填）
```

#### 2. 构建 Lambda 包

```bash
cd terraform
python scripts/build_lambdas.py
```

#### 3. 初始化与部署

```bash
terraform init
terraform plan
terraform apply
```

首次 apply 约需 10–15 分钟（RDS 创建较慢）。

#### 4. 获取 API URL

```bash
terraform output api_url
# 或
terraform output post_orders_url
terraform output get_order_url
```

#### 5. Postman 测试

**创建订单**

- Method: `POST`
- URL: `{api_url}/orders`（例如 `https://xxxxxx.execute-api.us-east-1.amazonaws.com/orders`）
- Body: `raw` → `JSON`，内容示例：

```json
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

- Method: `GET`
- URL: `{api_url}/orders/1`（将 `1` 替换为创建订单时返回的 id）

响应示例：`{"success": true, "data": {"id": 1, "status": "completed", "content": "=== Care Plan (Mock) ===", ...}}`

#### 6. 销毁资源

```bash
terraform destroy
```

销毁后，未来需要时只需重新执行上述 1–5 步即可。

### 架构说明

- 3 个 Lambda：create_order（写 RDS + 发 SQS）、generate_careplan（SQS 触发，Mock LLM 更新 RDS）、get_order（查 RDS）
- SQS DLQ：消息处理失败 3 次后进入 Dead Letter Queue
- **注意**：`terraform.tfvars` 含 `db_password`，已加入 .gitignore，不会提交

详见 `terraform/README.md`。

---

## Mock ENV

### Mock方式 1：不设置，默认 mock

`docker-compose up -d`

### Mock方式 2：显式设置

`set USE_MOCK_LLM=1 && docker compose up -d`

Prod 模式（真实调用 LLM）

### REAL PROD方式 1：启动时设置

`set USE_MOCK_LLM=0 && docker compose up -d`

## 测试

- 启动 Docker Desktop 后执行

`docker-compose run --rm test`
