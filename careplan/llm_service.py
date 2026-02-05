import os
from django.conf import settings
from openai import OpenAI


def generate_careplan_with_llm(patient, provider, primary_diagnosis, additional_diagnosis,
                               medication_name, medication_history, patient_records):
    # 优先从系统环境变量读取，如果没有则从 settings 读取
    api_key = os.getenv('OPENAI_API_KEY') or settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables or settings")

    # 使用 openai>=1.x 官方推荐的新客户端
    client = OpenAI(api_key=api_key)
    
    prompt = f"""Generate a pharmacist care plan for the following patient information.

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

    # 使用 chat.completions.create（openai>=1.x）
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a clinical pharmacist assistant. "
                    "Generate detailed, professional care plans for patients."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
    )

    return response.choices[0].message.content
