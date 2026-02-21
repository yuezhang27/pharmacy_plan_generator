"""
Error tests: ensure incorrect inputs produce corresponding error responses.
"""
import json
import pytest
from django.test import Client
from unittest.mock import patch

from pharmacy_plan.exceptions import ValidationError, BlockError, WarningException


@pytest.mark.django_db
class TestGenerateCareplanErrors:
    """Error responses for generate-careplan API."""

    def test_invalid_json_returns_validation_error(self):
        client = Client()
        resp = client.post(
            "/api/generate-careplan/",
            data="not json",
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["success"] is False
        assert data["type"] == "validation"
        assert data["code"] == "INVALID_JSON"

    def test_method_not_allowed_returns_block_error(self):
        client = Client()
        resp = client.get("/api/generate-careplan/")
        assert resp.status_code == 405
        data = resp.json()
        assert data["success"] is False
        assert data["type"] == "block"
        assert data["code"] == "METHOD_NOT_ALLOWED"

    def test_provider_npi_name_mismatch_returns_409(self):
        from careplan.models import Provider

        Provider.objects.create(npi="1234567890", name="Dr. Jane")
        client = Client()
        payload = {
            "provider_npi": "1234567890",
            "provider_name": "Dr. John",
            "patient_mrn": "123456",
            "patient_first_name": "John",
            "patient_last_name": "Doe",
            "patient_dob": "1990-01-15",
            "primary_diagnosis": "E11.9",
            "medication_name": "Metformin",
            "patient_records": "r",
        }
        with patch("careplan.services.generate_careplan_task") as mock_task:
            mock_task.delay = lambda x: None
            resp = client.post(
                "/api/generate-careplan/",
                data=json.dumps(payload),
                content_type="application/json",
            )
        assert resp.status_code == 409
        data = resp.json()
        assert data["success"] is False
        assert data["type"] == "block"
        assert data["code"] == "PROVIDER_NPI_NAME_MISMATCH"

    def test_patient_mrn_mismatch_returns_200_with_warning(self):
        from careplan.models import Patient

        Patient.objects.create(
            mrn="123456",
            first_name="Jane",
            last_name="Doe",
            dob="1985-05-20",
        )
        client = Client()
        payload = {
            "provider_npi": "1234567890",
            "provider_name": "Dr. Jane",
            "patient_mrn": "123456",
            "patient_first_name": "John",
            "patient_last_name": "Doe",
            "patient_dob": "1990-01-15",
            "primary_diagnosis": "E11.9",
            "medication_name": "Metformin",
            "patient_records": "r",
        }
        with patch("careplan.services.generate_careplan_task") as mock_task:
            mock_task.delay = lambda x: None
            resp = client.post(
                "/api/generate-careplan/",
                data=json.dumps(payload),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["type"] == "warning"
        assert data["code"] == "PATIENT_MRN_MISMATCH"

    def test_careplan_not_found_returns_404(self):
        client = Client()
        resp = client.get("/api/careplan/99999/")
        assert resp.status_code == 404
        data = resp.json()
        assert data["success"] is False
        assert data["code"] == "NOT_FOUND"

    def test_careplan_status_not_found_returns_404(self):
        client = Client()
        resp = client.get("/api/careplan/99999/status/")
        assert resp.status_code == 404

    def test_order_same_day_duplicate_returns_409(self):
        from careplan.models import Patient, Provider, CarePlan

        patient = Patient.objects.create(
            mrn="123456",
            first_name="John",
            last_name="Doe",
            dob="1990-01-15",
        )
        provider = Provider.objects.create(npi="1234567890", name="Dr. Jane")
        CarePlan.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis="E11.9",
            medication_name="Metformin",
            patient_records="r",
            status="completed",
        )
        client = Client()
        payload = {
            "provider_npi": "1234567890",
            "provider_name": "Dr. Jane",
            "patient_mrn": "123456",
            "patient_first_name": "John",
            "patient_last_name": "Doe",
            "patient_dob": "1990-01-15",
            "primary_diagnosis": "E11.9",
            "medication_name": "Metformin",
            "patient_records": "r",
        }
        with patch("careplan.services.generate_careplan_task") as mock_task:
            mock_task.delay = lambda x: None
            resp = client.post(
                "/api/generate-careplan/",
                data=json.dumps(payload),
                content_type="application/json",
            )
        assert resp.status_code == 409
        data = resp.json()
        assert data["code"] == "ORDER_SAME_DAY_DUPLICATE"


@pytest.mark.django_db
class TestSerializersErrors:
    """Serializer/parse errors."""

    def test_parse_invalid_json_raises_validation_error(self):
        from careplan.serializers import parse_generate_careplan_request

        with pytest.raises(ValidationError) as exc_info:
            parse_generate_careplan_request(b"invalid")
        assert exc_info.value.code == "INVALID_JSON"


@pytest.mark.django_db
class TestErrorResponseFormat:
    """Ensure all error responses follow unified format (success, type, code, message)."""

    def test_error_has_unified_format(self):
        client = Client()
        resp = client.post(
            "/api/generate-careplan/",
            data="invalid json",
            content_type="application/json",
        )
        data = resp.json()
        assert "success" in data
        assert data["success"] is False
        assert "type" in data
        assert "code" in data
        assert "message" in data
