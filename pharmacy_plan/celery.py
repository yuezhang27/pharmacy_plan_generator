import os
from celery import Celery
from celery.signals import worker_ready

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmacy_plan.settings')

app = Celery('pharmacy_plan')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@worker_ready.connect
def setup_metrics_server(sender, **kwargs):
    """Worker 就绪后启动 Prometheus metrics HTTP 服务（daemon 线程）"""
    try:
        from careplan.celery_metrics import start_metrics_server
        start_metrics_server()
    except Exception:
        pass
