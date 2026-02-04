from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
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
