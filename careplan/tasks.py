"""
Celery 异步任务：调用 LLM 生成 Care Plan，更新数据库
支持失败重试（最多 3 次，指数退避）
"""
import time

from celery import shared_task

from careplan.models import CarePlan
from careplan.llm_service import generate_careplan
from careplan.metrics import (
    CAREPLAN_COMPLETED,
    CAREPLAN_FAILED,
    CELERY_TASK_DURATION,
    CELERY_TASK_FAILURE,
    CELERY_TASK_RETRY,
)


@shared_task(bind=True, max_retries=3)
def generate_careplan_task(self, careplan_id):
    """
    从 DB 加载 CarePlan → 调 LLM 生成 → 更新 DB
    失败时指数退避重试：2^retries 秒（1次:2s, 2次:4s, 3次:8s）
    """
    start = time.perf_counter()
    try:
        careplan = CarePlan.objects.select_related('patient', 'provider').get(id=careplan_id)
    except CarePlan.DoesNotExist:
        return

    if careplan.status != 'pending':
        return

    careplan.status = 'processing'
    careplan.save()

    try:
        content = generate_careplan(
            patient=careplan.patient,
            provider=careplan.provider,
            primary_diagnosis=careplan.primary_diagnosis,
            additional_diagnosis=careplan.additional_diagnosis or '',
            medication_name=careplan.medication_name,
            medication_history=careplan.medication_history or '',
            patient_records=careplan.patient_records,
            llm_provider=careplan.llm_provider or None,
        )
        careplan.status = 'completed'
        careplan.generated_content = content
        careplan.save()
        CAREPLAN_COMPLETED.inc()
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            careplan.status = 'failed'
            careplan.error_message = str(exc)
            careplan.save()
            CAREPLAN_FAILED.inc()
            CELERY_TASK_FAILURE.inc()
            CELERY_TASK_DURATION.observe(time.perf_counter() - start)
            raise
        CELERY_TASK_RETRY.inc()
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    else:
        CELERY_TASK_DURATION.observe(time.perf_counter() - start)
