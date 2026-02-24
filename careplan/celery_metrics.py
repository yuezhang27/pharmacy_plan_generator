"""
Celery Worker 启动时暴露 Prometheus /metrics 端点
Worker 与 Web 是独立进程，需单独启动 HTTP 服务供 Prometheus 抓取
"""
from prometheus_client import start_http_server

METRICS_PORT = 9090


def start_metrics_server():
    """在 daemon 线程启动 metrics HTTP 服务（非阻塞）"""
    import careplan.metrics  # noqa: F401 - 确保 metrics 已注册
    start_http_server(METRICS_PORT)
