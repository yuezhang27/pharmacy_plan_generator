"""
LLM 生成 Care Plan 统一入口
业务代码只调用 generate_careplan，不关心具体 LLM 实现
"""
import time

from .llm_providers import get_llm_service
from .statsd_metrics import (
    llm_api_error,
    llm_api_latency_seconds,
    llm_provider_usage,
)

SYSTEM_PROMPT = (
    "You are a clinical pharmacist assistant. "
    "Generate detailed, professional care plans for patients."
)


def _build_user_prompt(
    patient,
    provider,
    primary_diagnosis,
    additional_diagnosis,
    medication_name,
    medication_history,
    patient_records,
) -> str:
    return f"""Generate a pharmacist care plan for the following patient information.

Patient Information:
- Name: {patient.first_name} {patient.last_name}
- MRN: {patient.mrn}
- DOB: {patient.dob}

Provider Information:
- Name: {provider.name}
- NPI: {provider.npi}

Diagnosis:
- Primary: {primary_diagnosis}
- Additional: {additional_diagnosis if additional_diagnosis else 'None'}

Medication:
- Name: {medication_name}
- History: {medication_history if medication_history else 'None'}

Patient Records:
{patient_records}

Please generate a comprehensive care plan with the following sections:

1. Problem list / Drug therapy problems
2. Goals (SMART goals)
3. Pharmacist interventions
4. Monitoring plan

Format the output clearly with section headers."""


def generate_careplan(
    patient,
    provider,
    primary_diagnosis,
    additional_diagnosis,
    medication_name,
    medication_history,
    patient_records,
    *,
    llm_provider: str | None = None,
):
    """
    统一入口：根据配置调用对应 LLM 生成 care plan
    llm_provider: 可选，指定使用的 LLM（openai/claude），不传则用 settings.LLM_PROVIDER
    """
    service = get_llm_service(provider=llm_provider)
    provider_id = getattr(service, "provider_id", "unknown")
    user_prompt = _build_user_prompt(
        patient=patient,
        provider=provider,
        primary_diagnosis=primary_diagnosis,
        additional_diagnosis=additional_diagnosis,
        medication_name=medication_name,
        medication_history=medication_history,
        patient_records=patient_records,
    )
    start = time.perf_counter()
    try:
        result = service.generate(
            system_message=SYSTEM_PROMPT,
            user_message=user_prompt,
            temperature=0.7,
            max_tokens=2000,
        )
        llm_api_latency_seconds(time.perf_counter() - start)
        llm_provider_usage(provider_id)
        return result
    except Exception:
        llm_api_error()
        raise
