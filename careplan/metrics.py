"""
Prometheus 指标定义（与 DASHBOARD_METRICS.md 对应）
"""
from prometheus_client import Counter, Histogram, Gauge

# 业务指标
CAREPLAN_SUBMITTED = Counter(
    "careplan_submitted_total",
    "提交的 care plan 总数",
    ["source"],
)
CAREPLAN_COMPLETED = Counter(
    "careplan_completed_total",
    "成功生成的 care plan 数",
)
CAREPLAN_FAILED = Counter(
    "careplan_failed_total",
    "生成失败的 care plan 数",
)
DUPLICATION_BLOCK = Counter(
    "duplication_block_total",
    "被 Block 的重复提交次数",
    ["code"],
)
DUPLICATION_WARNING = Counter(
    "duplication_warning_total",
    "触发 Warning 的重复提交次数",
    ["code"],
)
LLM_PROVIDER_USAGE = Counter(
    "llm_provider_usage_total",
    "各 LLM 使用次数",
    ["provider"],
)

# 性能指标（Histogram 自动提供 _count, _sum, _bucket）
API_GENERATE_DURATION = Histogram(
    "api_generate_careplan_duration_seconds",
    "POST /api/generate-careplan/ 响应时间",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0),
)
API_STATUS_DURATION = Histogram(
    "api_careplan_status_duration_seconds",
    "GET /api/careplan/<id>/status/ 响应时间",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
)
API_SEARCH_DURATION = Histogram(
    "api_search_duration_seconds",
    "GET /api/search-careplans/ 响应时间",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 3.0),
)
CELERY_TASK_DURATION = Histogram(
    "celery_task_duration_seconds",
    "generate_careplan_task 执行时长",
    buckets=(10, 30, 60, 90, 120, 180, 300),
)
LLM_API_LATENCY = Histogram(
    "llm_api_latency_seconds",
    "LLM 调用耗时",
    buckets=(5, 10, 20, 30, 45, 60, 90, 120),
)

# 错误指标
HTTP_5XX = Counter("http_5xx_total", "5xx 错误数")
HTTP_4XX = Counter("http_4xx_total", "4xx 错误数", ["code"])
VALIDATION_ERROR = Counter("validation_error_total", "数据格式校验失败次数")
BLOCK_ERROR = Counter("block_error_total", "Block 错误次数", ["code"])
CELERY_TASK_FAILURE = Counter("celery_task_failure_total", "Celery 任务失败次数")
CELERY_TASK_RETRY = Counter("celery_task_retry_total", "Celery 任务重试次数")
LLM_API_ERROR = Counter("llm_api_error_total", "LLM API 调用失败次数")
