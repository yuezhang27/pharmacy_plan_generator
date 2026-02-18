"""
Pytest configuration and shared fixtures.
"""
import pytest
from datetime import date, datetime


@pytest.fixture
def sample_patient_data():
    """Sample patient data for tests."""
    return {
        "patient_mrn": "123456",
        "patient_first_name": "John",
        "patient_last_name": "Doe",
        "patient_dob": "1990-01-15",
    }


@pytest.fixture
def sample_provider_data():
    """Sample provider data for tests."""
    return {
        "provider_npi": "1234567890",
        "provider_name": "Dr. Jane Smith",
    }


@pytest.fixture
def full_careplan_payload(sample_patient_data, sample_provider_data):
    """Full payload for generate careplan API."""
    return {
        **sample_patient_data,
        **sample_provider_data,
        "primary_diagnosis": "Diabetes",
        "medication_name": "Metformin",
        "patient_records": "Patient has been stable.",
    }
