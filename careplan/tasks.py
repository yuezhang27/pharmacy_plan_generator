"""
Celery 异步任务：调用 LLM 生成 Care Plan，更新数据库
支持失败重试（最多 3 次，指数退避）
"""
from celery import shared_task
from careplan.models import CarePlan
from careplan.llm_service import generate_careplan_with_llm


@shared_task(bind=True, max_retries=3)
def generate_careplan_task(self, careplan_id):
    """
    从 DB 加载 CarePlan → 调 LLM 生成 → 更新 DB
    失败时指数退避重试：2^retries 秒（1次:2s, 2次:4s, 3次:8s）
    """
    try:
        careplan = CarePlan.objects.select_related('patient', 'provider').get(id=careplan_id)
    except CarePlan.DoesNotExist:
        return

    if careplan.status != 'pending':
        return

    careplan.status = 'processing'
    careplan.save()

    try:
        content = generate_careplan_with_llm(
            patient=careplan.patient,
            provider=careplan.provider,
            primary_diagnosis=careplan.primary_diagnosis,
            additional_diagnosis=careplan.additional_diagnosis or '',
            medication_name=careplan.medication_name,
            medication_history=careplan.medication_history or '',
            patient_records=careplan.patient_records,
        )
        careplan.status = 'completed'
        careplan.generated_content = content
        careplan.save()
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            careplan.status = 'failed'
            careplan.error_message = str(exc)
            careplan.save()
            raise
        # 指数退避：2^retries 秒
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
