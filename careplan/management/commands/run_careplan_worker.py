"""
手写 Worker：从 Redis 拉任务 → 调 LLM 生成 → 存数据库
运行: python manage.py run_careplan_worker
"""
import redis
from django.conf import settings
from django.core.management.base import BaseCommand
from careplan.models import CarePlan
from careplan.llm_service import generate_careplan_with_llm


def process_one_task(r):
    """从 Redis 拉一个 careplan_id，处理完返回 True；无任务返回 False"""
    # BLPOP 阻塞等待，timeout=5 秒便于 Ctrl+C 退出
    result = r.blpop(settings.CAREPLAN_QUEUE_KEY, timeout=5)
    if not result:
        return False

    _, careplan_id_str = result
    careplan_id = int(careplan_id_str)

    try:
        careplan = CarePlan.objects.select_related('patient', 'provider').get(id=careplan_id)
    except CarePlan.DoesNotExist:
        return True  # 任务无效，跳过

    if careplan.status != 'pending':
        return True  # 已处理过，跳过

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
    except Exception as e:
        careplan.status = 'failed'
        careplan.error_message = str(e)
        careplan.save()

    return True


class Command(BaseCommand):
    help = '从 Redis 队列拉任务，调 LLM 生成 Care Plan，存数据库'

    def handle(self, *args, **options):
        r = redis.from_url(settings.REDIS_URL)
        self.stdout.write('Worker 启动，等待任务... (Ctrl+C 退出)')

        while True:
            try:
                processed = process_one_task(r)
                if processed:
                    self.stdout.write('处理完成一个任务')
            except KeyboardInterrupt:
                self.stdout.write('Worker 已退出')
                break
            except Exception as e:
                self.stderr.write(f'处理出错: {e}')
