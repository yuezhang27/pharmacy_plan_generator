"""
业务逻辑：调 LLM、放队列、操作数据库
"""
from datetime import datetime
import csv
from django.db.models import Q
from django.http import HttpResponse

from pharmacy_plan.exceptions import BlockError

from .models import Patient, Provider, CarePlan
from .tasks import generate_careplan_task
from .duplication_detection import check_provider, check_patient, check_order


def create_careplan(data):
    """
    创建 CarePlan，投递 Celery 任务，返回提交结果
    先执行重复检测，通过后再创建
    """
    confirm = data.get('confirm') is True

    provider = check_provider(data['provider_npi'], data['provider_name'])
    if provider is None:
        provider, _ = Provider.objects.get_or_create(
            npi=data['provider_npi'],
            defaults={'name': data['provider_name']}
        )

    patient = check_patient(
        data['patient_mrn'],
        data['patient_first_name'],
        data['patient_last_name'],
        data['patient_dob'],
        confirm=confirm
    )
    if patient is None:
        patient, _ = Patient.objects.get_or_create(
            mrn=data['patient_mrn'],
            defaults={
                'first_name': data['patient_first_name'],
                'last_name': data['patient_last_name'],
                'dob': datetime.strptime(data['patient_dob'], '%Y-%m-%d').date()
            }
        )

    check_order(patient, data['medication_name'], confirm=confirm)

    careplan = CarePlan.objects.create(
        patient=patient,
        provider=provider,
        primary_diagnosis=data['primary_diagnosis'],
        additional_diagnosis=data.get('additional_diagnosis', ''),
        medication_name=data['medication_name'],
        medication_history=data.get('medication_history', ''),
        patient_records=data['patient_records'],
        status='pending'
    )

    generate_careplan_task.delay(careplan.id)

    return {
        "success": True,
        "data": {
            "message": "已收到",
            "careplan_id": careplan.id,
            "status": careplan.status,
        },
    }


def get_careplan_detail(careplan_id):
    """
    获取单个 care plan 详情（仅 completed 有内容）
    """
    try:
        careplan = CarePlan.objects.select_related('patient', 'provider').get(id=careplan_id)
    except CarePlan.DoesNotExist:
        raise BlockError(
            message="Care plan not found",
            code="NOT_FOUND",
            http_status=404,
        )

    if careplan.status != 'completed':
        raise BlockError(
            message=careplan.error_message if careplan.status == 'failed' else "Care plan is not ready yet",
            code="NOT_READY",
            detail={"status": careplan.status},
            http_status=400,
        )

    return {
        "success": True,
        "data": {
            "id": careplan.id,
            "status": careplan.status,
            "content": careplan.generated_content,
            "patient": {
                "first_name": careplan.patient.first_name,
                "last_name": careplan.patient.last_name,
                "mrn": careplan.patient.mrn,
            },
            "medication": careplan.medication_name,
            "created_at": careplan.created_at.isoformat(),
        },
    }


def get_careplan_status(careplan_id):
    """
    获取 care plan 状态（供轮询）
    """
    try:
        careplan = CarePlan.objects.get(id=careplan_id)
    except CarePlan.DoesNotExist:
        raise BlockError(
            message="Care plan not found",
            code="NOT_FOUND",
            http_status=404,
        )

    data = {"success": True, "data": {"status": careplan.status}}
    if careplan.status == "completed":
        data["data"]["content"] = careplan.generated_content
    elif careplan.status == "failed":
        data["data"]["error"] = careplan.error_message or "Generation failed"

    return data


def get_careplan_download(careplan_id):
    """
    获取 care plan 下载内容
    返回 (content, filename)
    """
    try:
        careplan = CarePlan.objects.select_related("patient").get(id=careplan_id)
    except CarePlan.DoesNotExist:
        raise BlockError(
            message="Care plan not found",
            code="NOT_FOUND",
            http_status=404,
        )

    if careplan.status != "completed" or not careplan.generated_content:
        raise BlockError(
            message="Care plan is not completed yet",
            code="NOT_READY",
            http_status=400,
        )

    filename = f"careplan_{careplan.patient.mrn}_{careplan.medication_name}.txt"
    return careplan.generated_content, filename


def search_careplans(q, export=False):
    """
    搜索 care plans
    export=False: 返回 list of dicts
    export=True: 返回 HttpResponse (CSV)
    """
    queryset = (
        CarePlan.objects
        .filter(status='completed')
        .select_related('patient', 'provider')
        .order_by('-created_at')
    )

    if q:
        queryset = queryset.filter(
            Q(patient__first_name__icontains=q)
            | Q(patient__last_name__icontains=q)
            | Q(patient__mrn__icontains=q)
            | Q(provider__name__icontains=q)
            | Q(provider__npi__icontains=q)
            | Q(medication_name__icontains=q)
            | Q(primary_diagnosis__icontains=q)
        )

    if export:
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="careplans_report.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'patient_mrn', 'patient_first_name', 'patient_last_name', 'patient_dob',
            'provider_name', 'provider_npi', 'medication_name', 'primary_diagnosis',
            'careplan_created_at', 'duplication_warning',
        ])
        for cp in queryset:
            writer.writerow([
                cp.patient.mrn, cp.patient.first_name, cp.patient.last_name, cp.patient.dob.isoformat(),
                cp.provider.name, cp.provider.npi, cp.medication_name, cp.primary_diagnosis,
                cp.created_at.isoformat(), '',
            ])
        return response

    items = []
    for cp in queryset[:50]:
        items.append({
            "id": cp.id,
            "patient_name": f"{cp.patient.first_name} {cp.patient.last_name}",
            "patient_mrn": cp.patient.mrn,
            "provider_name": cp.provider.name,
            "provider_npi": cp.provider.npi,
            "medication_name": cp.medication_name,
            "primary_diagnosis": cp.primary_diagnosis,
            "created_at": cp.created_at.isoformat(),
            "download_url": f"/download-careplan/{cp.id}/",
        })
    return {"success": True, "data": {"results": items}}
