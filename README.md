# Pharmacy Care Plan Generator - MVP

最小可运行的 MVP 版本，包含前端、后端、PostgreSQL 数据库和 LLM 生成 care plan 的功能。

## 功能

- 前端表单输入患者、提供者、诊断和药物信息
- 后端 Django API 接收数据并生成 care plan
- PostgreSQL 数据库存储数据
- LLM (OpenAI) 生成 care plan
- Care plan 状态管理：pending → processing → completed/failed
- 只有 completed 状态时前端才显示 care plan

## 运行步骤

### 1. 准备环境变量

创建 `.env` 文件（参考 `.env.example`）：

```bash
OPENAI_API_KEY=your_openai_api_key_here
POSTGRES_DB=pharmacy_db
POSTGRES_USER=pharmacy_user
POSTGRES_PASSWORD=pharmacy_pass
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

**重要**：将 `OPENAI_API_KEY` 替换为你的实际 OpenAI API key。

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
5. 生成完成后，页面会显示生成的 care plan

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

## 停止服务

```bash
docker-compose down
```

如果要删除数据库数据：

```bash
docker-compose down -v
```
