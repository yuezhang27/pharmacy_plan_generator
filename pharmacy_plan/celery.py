import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmacy_plan.settings')

app = Celery('pharmacy_plan')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
