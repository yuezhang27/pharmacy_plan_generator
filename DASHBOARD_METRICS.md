## 最终dashboard实现

已完成 StatsD 方案实现，改动总结如下：

## 实现总结

### 架构

```
Worker 子进程 --UDP--> statsd_exporter --/metrics--> Prometheus --> Grafana
                (9125)        (9102)
```

### 修改内容

1. **`careplan/statsd_metrics.py`**（新增）
   - 封装 StatsD 客户端，通过 UDP 发送指标
   - 指标：`careplan_completed`, `careplan_failed`, `celery_task_duration`, `celery_task_failure`, `celery_task_retry`, `llm_provider_usage`, `llm_api_latency`, `llm_api_error`

2. **`careplan/tasks.py`**
   - 使用 `statsd_metrics` 替代 `prometheus_client` 记录任务相关指标

3. **`careplan/llm_service.py`**
   - 使用 `statsd_metrics` 替代 `prometheus_client` 记录 LLM 相关指标

4. **`statsd_mapping.yml`**（新增）
   - 将 StatsD 指标映射为与 Grafana 一致的 Prometheus 指标名

5. **`docker-compose.yml`**
   - 新增 `statsd_exporter` 服务
   - `celery_worker` 增加 `STATSD_HOST`、`STATSD_PORT`，并依赖 `statsd_exporter`
   - 移除 celery worker 的 9090 端口（不再暴露本地 metrics）

6. **`pharmacy_plan/celery.py`**
   - 移除 `worker_ready` 中的 metrics 服务启动逻辑

7. **`prometheus.yml`**
   - 将 `pharmacy_celery` 改为抓取 `statsd_exporter:9102`

8. **`requirements.txt`**
   - 新增 `statsd==4.0.1`

9. **删除 `careplan/celery_metrics.py`**
   - 不再使用

### 业务影响

- Celery 仍为 prefork 模式，并发行为不变
- 仅将 worker 内指标上报方式从进程内 registry 改为 UDP 发送，对业务逻辑无影响
- 指标链路：Worker → StatsD UDP → statsd_exporter → Prometheus → Grafana

### 启动与验证

```bash
docker-compose up -d --build
```

## 执行 E2E 测试后，在 Grafana 中应能看到 `careplan_completed_total` 等指标。

| 类别         | 指标名称                               | 说明                                    | 能发现的问题                       | 告警阈值建议            |
| ------------ | -------------------------------------- | --------------------------------------- | ---------------------------------- | ----------------------- |
| **业务指标** | careplan_submitted_total               | 提交的 care plan 总数（按 source 分）   | 业务量、各接入源使用情况           | -                       |
|              | careplan_completed_total               | 成功生成的 care plan 数                 | 实际产出量、与 submitted 的差距    | -                       |
|              | careplan_failed_total                  | 生成失败的 care plan 数                 | 失败规模、是否需人工排查           | 1h 内 >10 或失败率 >20% |
|              | careplan_completion_rate               | completed / submitted                   | 整体成功率                         | <80%                    |
|              | careplan_time_to_complete_p95          | 从提交到完成的时间 P95                  | 用户等待体验、LLM/任务处理是否变慢 | >5min                   |
|              | duplication_block_total                | 被 Block 的重复提交次数                 | 重复提交、数据质量                 | -                       |
|              | duplication_warning_total              | 触发 Warning 的重复提交次数             | 潜在重复、需人工确认的量           | -                       |
|              | intake_source_distribution             | 各 intake 来源占比                      | 接入源使用分布                     | -                       |
|              | llm_provider_usage                     | 各 LLM 使用占比                         | 模型选择、成本分布                 | -                       |
| **性能指标** | api_generate_careplan_duration_seconds | POST /api/generate-careplan/ 响应时间   | 接口是否变慢、DB/校验瓶颈          | P95 >3s                 |
|              | api_careplan_status_duration_seconds   | GET /api/careplan/<id>/status/ 响应时间 | 轮询接口是否变慢                   | P95 >1s                 |
|              | api_search_duration_seconds            | GET /api/search-careplans/ 响应时间     | 搜索性能、DB 索引                  | P95 >2s                 |
|              | celery_task_duration_seconds           | generate_careplan_task 执行时长         | Celery/LLM 处理是否变慢            | P95 >2min               |
|              | llm_api_latency_seconds                | LLM 调用耗时                            | LLM 服务是否变慢                   | P95 >60s                |
|              | db_query_duration_seconds              | 数据库查询耗时                          | DB 性能、慢查询                    | P95 >500ms              |
|              | redis_operation_duration_seconds       | Redis 操作耗时                          | Redis 性能、网络                   | P95 >50ms               |
| **错误指标** | http_5xx_total                         | 5xx 错误数                              | 服务异常、未捕获错误               | 1h 内 >5                |
|              | http_4xx_total                         | 4xx 错误数（按 code 分）                | 客户端错误、配置问题               | -                       |
|              | validation_error_total                 | 数据格式校验失败次数                    | 输入质量、前端校验                 | 1h 内 >50               |
|              | block_error_total                      | Block 错误次数（按 code 分）            | 重复、业务规则冲突                 | -                       |
|              | celery_task_failure_total              | Celery 任务失败次数                     | 任务异常、重试耗尽                 | 1h 内 >5                |
|              | celery_task_retry_total                | Celery 任务重试次数                     | LLM 不稳定、临时故障               | 1h 内 >20               |
|              | llm_api_error_total                    | LLM API 调用失败次数                    | API key、限流、服务不可用          | 1h 内 >3                |
|              | db_connection_error_total              | 数据库连接失败次数                      | DB 不可用、连接池耗尽              | 任意一次                |
|              | redis_connection_error_total           | Redis 连接失败次数                      | Redis 不可用、Celery 不可用        | 任意一次                |
| **资源指标** | web_cpu_percent                        | Web 进程 CPU 使用率                     | 计算资源是否吃紧                   | >80% 持续 5min          |
|              | web_memory_bytes                       | Web 进程内存                            | 内存泄漏、OOM 风险                 | >1.5GB                  |
|              | celery_worker_cpu_percent              | Celery worker CPU                       | 任务处理能力                       | >90% 持续 5min          |
|              | celery_worker_memory_bytes             | Celery worker 内存                      | 任务内存占用                       | >2GB                    |
|              | celery_queue_length                    | careplan 队列长度                       | 积压、处理能力不足                 | >100                    |
|              | postgres_connections_active            | 活跃数据库连接数                        | 连接池、连接泄漏                   | >80% 最大连接数         |
|              | postgres_connections_idle              | 空闲连接数                              | 连接复用情况                       | -                       |
|              | redis_memory_used_bytes                | Redis 已用内存                          | 内存压力、数据增长                 | >512MB                  |
|              | redis_connected_clients                | Redis 连接数                            | 连接泄漏、并发                     | >100                    |
|              | disk_usage_percent                     | 磁盘使用率                              | 空间不足、日志膨胀                 | >85%                    |

---

## 指标说明补充

### 业务指标

- **completion_rate**：核心业务健康度，低说明生成链路有问题。
- **time_to_complete_p95**：用户等待体验，高说明 LLM 或任务处理变慢。
- **duplication_block/warning**：数据质量与重复风险，block 多说明重复提交频繁。

### 性能指标

- **api\_\*\_duration**：接口响应时间，用于发现慢接口和瓶颈。
- **celery_task_duration**：任务整体耗时，主要受 LLM 影响。
- **llm_api_latency**：直接反映 LLM 服务性能。

### 错误指标

- **5xx**：服务端异常，需优先处理。
- **celery_task_failure**：任务失败，可能影响业务完成率。
- **llm_api_error**：LLM 调用失败，影响生成成功率。
- **db/redis_connection_error**：基础设施问题，影响整体可用性。

### 资源指标

- **celery_queue_length**：积压严重时需扩容或排查慢任务。
- **postgres_connections**：连接过多可能导致新请求失败。
- **redis_memory**：内存过高可能影响 Celery 和缓存。

---

# Prometheus + Grafana 监控接入说明

Prometheus + Grafana 监控已接入，实现内容和使用方式如下。

## 实现内容

### 1. 指标埋点

- careplan/services.py：提交成功时增加 careplan_submitted_total（按 source 区分）
- careplan/tasks.py：完成/失败时增加 careplan_completed_total、careplan_failed_total，并记录 celery_task_duration_seconds、celery_task_failure_total、celery_task_retry_total
- careplan/llm_service.py：记录 llm_api_latency_seconds、llm_api_error_total、llm_provider_usage_total
- pharmacy_plan/exception_handler.py：记录 duplication_block_total、duplication_warning_total、block_error_total、validation_error_total
- careplan/middleware_metrics.py：记录 API 耗时和 HTTP 4xx/5xx（已注册到 settings.py）

### 2. Celery Worker 暴露指标

- careplan/celery_metrics.py：Worker 启动后在 9090 端口提供 /metrics
- pharmacy_plan/celery.py：通过 worker_ready 信号启动 metrics 服务

### 3. Docker 配置

- docker-compose.yml：新增 prometheus、grafana 服务，celery_worker 暴露 9090 端口
- prometheus.yml：抓取 web:8000/metrics 和 celery_worker:9090/metrics
- grafana/provisioning/：自动配置 Prometheus 数据源和 Pharmacy Care Plan 仪表盘

## 如何运行

### 启动全部服务

```bash
docker-compose up -d --build
```

### 访问地址

| 服务                             | 地址                                                           |
| -------------------------------- | -------------------------------------------------------------- |
| Grafana （账号：admin）          | [http://localhost:3000](http://localhost:3000)                 |
| Prometheus                       | [http://localhost:9091](http://localhost:9091)                 |
| Django 应用                      | [http://localhost:8000](http://localhost:8000)                 |
| Django metrics                   | [http://localhost:8000/metrics](http://localhost:8000/metrics) |
| Celery metrics（需worker启动后） | [http://localhost:9090/metrics](http://localhost:9090/metrics) |

### 连接关系

Prometheus 抓取:

- web:8000/metrics (Django API 指标)
- celery_worker:9090/metrics (Celery 任务指标)

Grafana 使用 Prometheus 作为数据源:

- 数据源（容器内）: [http://prometheus:9090](http://prometheus:9090)
- 仪表盘: Pharmacy Care Plan 监控（自动加载）

### 首次使用步骤

1. 执行 `docker-compose up -d --build`
2. 等待 web、celery_worker、prometheus、grafana 启动
3. 打开 [http://localhost:3000](http://localhost:3000，使用) 使用admin / admin 登录
4. 在左侧 Dashboards 中打开 Pharmacy Care Plan 监控

### 仅启动监控相关服务

```bash
docker-compose up -d web celery_worker prometheus grafana
```

数据库和 Redis 会一并启动（作为依赖）。
