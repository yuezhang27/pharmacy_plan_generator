"""
Prometheus 指标中间件：记录请求耗时、状态码、错误类型
"""
import time

from .metrics import (
    API_GENERATE_DURATION,
    API_STATUS_DURATION,
    API_SEARCH_DURATION,
    HTTP_4XX,
    HTTP_5XX,
)
from pharmacy_plan.exceptions import ValidationError, BlockError, WarningException


class MetricsMiddleware:
    """记录 HTTP 请求指标"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        try:
            response = self.get_response(request)
            self._record(request, response.status_code, time.perf_counter() - start)
            return response
        except Exception as exc:
            duration = time.perf_counter() - start
            status = self._status_from_exception(exc)
            self._record(request, status, duration)
            raise

    def _status_from_exception(self, exc):
        if isinstance(exc, (ValidationError, BlockError, WarningException)):
            return getattr(exc, "http_status", 400)
        return 500

    def _record(self, request, status, duration):
        path = getattr(request, "path", "") or ""
        if status >= 500:
            HTTP_5XX.inc()
        elif status >= 400:
            HTTP_4XX.labels(code=str(status)).inc()

        if path == "/api/generate-careplan/" and request.method == "POST":
            API_GENERATE_DURATION.observe(duration)
        elif "/api/careplan/" in path and "/status/" in path:
            API_STATUS_DURATION.observe(duration)
        elif path == "/api/search-careplans/":
            API_SEARCH_DURATION.observe(duration)
