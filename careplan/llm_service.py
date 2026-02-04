import os
from django.conf import settings
from openai import OpenAI

def generate_careplan_with_llm(patient, provider, primary_diagnosis, additional_diagnosis, 
                                medication_name, medication_history, patient_records):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
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

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a clinical pharmacist assistant. Generate detailed, professional care plans for patients."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    
    return response.choices[0].message.content
