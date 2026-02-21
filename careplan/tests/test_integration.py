"""
Integration tests: full API flow.
"""
import json
import pytest
from django.test import Client
from unittest.mock import patch

from careplan.models import Patient, Provider, CarePlan


@pytest.mark.django_db
class TestGenerateCareplanIntegration:
    """Integration tests for generate careplan flow."""

    def test_create_careplan_success(self):
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
            "patient_records": "Patient stable.",
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
        assert data["success"] is True
        assert "careplan_id" in data["data"]
        assert data["data"]["status"] == "pending"

        careplan_id = data["data"]["careplan_id"]
        assert CarePlan.objects.filter(id=careplan_id).exists()
        assert Patient.objects.filter(mrn="123456").exists()
        assert Provider.objects.filter(npi="1234567890").exists()

    def test_create_with_confirm_bypasses_warning(self):
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
            "confirm": True,
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
        assert data["success"] is True
        assert "careplan_id" in data["data"]


@pytest.mark.django_db
class TestCareplanStatusIntegration:
    """Integration tests for careplan status polling."""

    def test_status_pending(self):
        patient = Patient.objects.create(
            mrn="123456",
            first_name="John",
            last_name="Doe",
            dob="1990-01-15",
        )
        provider = Provider.objects.create(npi="1234567890", name="Dr. Jane")
        cp = CarePlan.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis="E11.9",
            medication_name="Metformin",
            patient_records="r",
            status="pending",
        )
        client = Client()
        resp = client.get(f"/api/careplan/{cp.id}/status/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "pending"

    def test_status_completed(self):
        patient = Patient.objects.create(
            mrn="123456",
            first_name="John",
            last_name="Doe",
            dob="1990-01-15",
        )
        provider = Provider.objects.create(npi="1234567890", name="Dr. Jane")
        cp = CarePlan.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis="E11.9",
            medication_name="Metformin",
            patient_records="r",
            status="completed",
            generated_content="Generated content here",
        )
        client = Client()
        resp = client.get(f"/api/careplan/{cp.id}/status/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "completed"
        assert "content" in data["data"]


@pytest.mark.django_db
class TestSearchCareplansIntegration:
    """Integration tests for search API."""

    def test_search_empty(self):
        client = Client()
        resp = client.get("/api/search-careplans/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["results"] == []

    def test_search_with_results(self):
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
        resp = client.get("/api/search-careplans/?q=John")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]["results"]) >= 1
