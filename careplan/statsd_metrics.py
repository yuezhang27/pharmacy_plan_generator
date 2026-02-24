"""
Worker 进程指标：通过 StatsD UDP 发送，由 statsd_exporter 暴露给 Prometheus
不依赖进程内存，多进程 prefork 下可正确聚合
"""
import os

import statsd

# 从环境变量读取，默认 statsd_exporter 容器名
_STATSD_HOST = os.getenv("STATSD_HOST", "statsd_exporter")
_STATSD_PORT = int(os.getenv("STATSD_PORT", "9125"))
_PREFIX = "careplan"

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = statsd.StatsClient(_STATSD_HOST, _STATSD_PORT, prefix=_PREFIX)
    return _client


def careplan_completed():
    _get_client().incr("completed")


def careplan_failed():
    _get_client().incr("failed")


def celery_task_duration_seconds(seconds: float):
    _get_client().timing("celery_task_duration", int(seconds * 1000))


def celery_task_failure():
    _get_client().incr("celery_task_failure")


def celery_task_retry():
    _get_client().incr("celery_task_retry")


def llm_provider_usage(provider: str):
    # 用 metric 名携带 provider，由 statsd_exporter mapping 转为 label
    _get_client().incr(f"llm_provider_usage.{provider}")


def llm_api_latency_seconds(seconds: float):
    _get_client().timing("llm_api_latency", int(seconds * 1000))


def llm_api_error():
    _get_client().incr("llm_api_error")
