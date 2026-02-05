from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q
import csv
import json
from datetime import datetime
from .models import Patient, Provider, CarePlan
from .llm_service import generate_careplan_with_llm

def index(request):
    return render(request, 'careplan/index.html')

@csrf_exempt
def generate_careplan(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        
        # Get or create patient
        patient, _ = Patient.objects.get_or_create(
            mrn=data['patient_mrn'],
            defaults={
                'first_name': data['patient_first_name'],
                'last_name': data['patient_last_name'],
                'dob': datetime.strptime(data['patient_dob'], '%Y-%m-%d').date()
            }
        )

        # Get or create provider
        provider, _ = Provider.objects.get_or_create(
            npi=data['provider_npi'],
            defaults={'name': data['provider_name']}
        )

        # Create care plan with pending status
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

        # Update to processing
        careplan.status = 'processing'
        careplan.save()

        # Generate care plan with LLM
        try:
            generated_content = generate_careplan_with_llm(
                patient=patient,
                provider=provider,
                primary_diagnosis=careplan.primary_diagnosis,
                additional_diagnosis=careplan.additional_diagnosis,
                medication_name=careplan.medication_name,
                medication_history=careplan.medication_history,
                patient_records=careplan.patient_records
            )
            
            careplan.status = 'completed'
            careplan.generated_content = generated_content
            careplan.save()
            
            return JsonResponse({
                'success': True,
                'careplan_id': careplan.id,
                'status': careplan.status,
                'content': generated_content
            })
        except Exception as e:
            careplan.status = 'failed'
            careplan.error_message = str(e)
            careplan.save()
            
            return JsonResponse({
                'success': False,
                'error': str(e),
                'careplan_id': careplan.id,
                'status': careplan.status
            }, status=500)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def get_careplan(request, careplan_id):
    try:
        careplan = CarePlan.objects.get(id=careplan_id)
        
        if careplan.status != 'completed':
            return JsonResponse({
                'status': careplan.status,
                'error': careplan.error_message if careplan.status == 'failed' else 'Care plan is not ready yet'
            }, status=400)
        
        return JsonResponse({
            'id': careplan.id,
            'status': careplan.status,
            'content': careplan.generated_content,
            'patient': {
                'first_name': careplan.patient.first_name,
                'last_name': careplan.patient.last_name,
                'mrn': careplan.patient.mrn
            },
            'medication': careplan.medication_name,
            'created_at': careplan.created_at.isoformat()
        })
    except CarePlan.DoesNotExist:
        return JsonResponse({'error': 'Care plan not found'}, status=404)


def download_careplan(request, careplan_id):
    """
    下载单个 care plan 的文本文件（只在 completed 状态下有内容）。
    不做额外校验或权限控制，最小可用版本。
    """
    try:
        careplan = CarePlan.objects.get(id=careplan_id)
    except CarePlan.DoesNotExist:
        return HttpResponse("Care plan not found", status=404)

    if careplan.status != 'completed' or not careplan.generated_content:
        return HttpResponse("Care plan is not completed yet", status=400)

    filename = f"careplan_{careplan.patient.mrn}_{careplan.medication_name}.txt"
    response = HttpResponse(careplan.generated_content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def search_careplans(request):
    """
    最简单的 search + 导出功能：
    - GET /api/search-careplans/?q=xxx       返回 JSON 列表
    - GET /api/search-careplans/?q=xxx&export=1  返回 CSV 报表
    只搜索已 completed 的 care plan。
    """
    q = (request.GET.get('q') or '').strip()

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

    # 导出 CSV 报表
    if request.GET.get('export') == '1':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="careplans_report.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'patient_mrn',
            'patient_first_name',
            'patient_last_name',
            'patient_dob',
            'provider_name',
            'provider_npi',
            'medication_name',
            'primary_diagnosis',
            'careplan_created_at',
            'duplication_warning',  # 目前不实现逻辑，先留空
        ])

        for cp in queryset:
            writer.writerow([
                cp.patient.mrn,
                cp.patient.first_name,
                cp.patient.last_name,
                cp.patient.dob.isoformat(),
                cp.provider.name,
                cp.provider.npi,
                cp.medication_name,
                cp.primary_diagnosis,
                cp.created_at.isoformat(),
                '',  # duplication_warning 占位
            ])

        return response

    # 返回 JSON 用于前端简单展示
    items = []
    for cp in queryset[:50]:  # 最多返回 50 条，足够 MVP 使用
        items.append({
            'id': cp.id,
            'patient_name': f"{cp.patient.first_name} {cp.patient.last_name}",
            'patient_mrn': cp.patient.mrn,
            'provider_name': cp.provider.name,
            'provider_npi': cp.provider.npi,
            'medication_name': cp.medication_name,
            'primary_diagnosis': cp.primary_diagnosis,
            'created_at': cp.created_at.isoformat(),
            'download_url': f'/download-careplan/{cp.id}/',
        })

    return JsonResponse({'results': items})
