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
