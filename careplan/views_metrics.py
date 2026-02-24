"""
Prometheus /metrics 端点
"""
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache

from prometheus_client import REGISTRY, generate_latest, CONTENT_TYPE_LATEST


@require_GET
@never_cache
def metrics(request):
    """Prometheus 抓取端点"""
    data = generate_latest(REGISTRY)
    return HttpResponse(data, content_type=CONTENT_TYPE_LATEST)
