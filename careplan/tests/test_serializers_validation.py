"""
Unit tests for format validation in serializers.
"""
import json
import pytest
from django.test import Client
from unittest.mock import patch

from pharmacy_plan.exceptions import ValidationError

from careplan.serializers import (
    # parse_generate_careplan_request,
    validate_generate_careplan_data,
)


def valid_payload():
    return {
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


class TestValidateGenerateCareplanData:
    """Tests for validate_generate_careplan_data."""

    def test_valid_data_passes(self):
        validate_generate_careplan_data(valid_payload())

    def test_non_dict_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_generate_careplan_data([])
        assert exc_info.value.code == "INVALID_REQUEST"

    def test_missing_required_field(self):
        data = valid_payload()
        del data["provider_npi"]
        with pytest.raises(ValidationError) as exc_info:
            validate_generate_careplan_data(data)
        assert exc_info.value.code == "VALIDATION_ERROR"
        errors = exc_info.value.detail["errors"]
        assert any(e["field"] == "provider_npi" for e in errors)

    def test_invalid_npi_not_10_digits(self):
        data = valid_payload()
        data["provider_npi"] = "12345"
        with pytest.raises(ValidationError) as exc_info:
            validate_generate_careplan_data(data)
        errors = exc_info.value.detail["errors"]
        assert any("NPI" in e.get("message", "") for e in errors)

    def test_invalid_npi_contains_letters(self):
        data = valid_payload()
        data["provider_npi"] = "123456789a"
        with pytest.raises(ValidationError) as exc_info:
            validate_generate_careplan_data(data)
        errors = exc_info.value.detail["errors"]
        assert any("NPI" in e.get("message", "") for e in errors)

    def test_invalid_mrn_not_6_digits(self):
        data = valid_payload()
        data["patient_mrn"] = "12345"
        with pytest.raises(ValidationError) as exc_info:
            validate_generate_careplan_data(data)
        errors = exc_info.value.detail["errors"]
        assert any("MRN" in e.get("message", "") for e in errors)

    def test_invalid_dob_format(self):
        data = valid_payload()
        data["patient_dob"] = "01-15-1990"
        with pytest.raises(ValidationError) as exc_info:
            validate_generate_careplan_data(data)
        errors = exc_info.value.detail["errors"]
        assert any("YYYY-MM-DD" in e.get("message", "") for e in errors)

    def test_invalid_dob_not_a_date(self):
        data = valid_payload()
        data["patient_dob"] = "1990-02-30"
        with pytest.raises(ValidationError) as exc_info:
            validate_generate_careplan_data(data)
        errors = exc_info.value.detail["errors"]
        assert any("合法日期" in e.get("message", "") for e in errors)

    def test_invalid_icd10_format(self):
        data = valid_payload()
        data["primary_diagnosis"] = "D1"
        with pytest.raises(ValidationError) as exc_info:
            validate_generate_careplan_data(data)
        errors = exc_info.value.detail["errors"]
        assert any("ICD-10" in e.get("message", "") for e in errors)

    def test_valid_icd10_formats(self):
        for code in ["A00", "E11.9", "A18.32", "Z99.89"]:
            data = valid_payload()
            data["primary_diagnosis"] = code
            validate_generate_careplan_data(data)

    def test_empty_required_string(self):
        data = valid_payload()
        data["patient_first_name"] = "   "
        with pytest.raises(ValidationError) as exc_info:
            validate_generate_careplan_data(data)
        errors = exc_info.value.detail["errors"]
        assert any(e["field"] == "patient_first_name" for e in errors)


# class TestParseGenerateCareplanRequest:
#     """Tests for parse_generate_careplan_request with validation."""

#     def test_valid_json_and_format_returns_data(self):
#         data = parse_generate_careplan_request(json.dumps(valid_payload()).encode())
#         assert data["provider_npi"] == "1234567890"
#         assert data["patient_mrn"] == "123456"

#     def test_invalid_json_raises(self):
#         with pytest.raises(ValidationError) as exc_info:
#             parse_generate_careplan_request(b"not json")
#         assert exc_info.value.code == "INVALID_JSON"

#     def test_valid_json_invalid_format_raises(self):
#         payload = valid_payload()
#         payload["provider_npi"] = "123"
#         with pytest.raises(ValidationError) as exc_info:
#             parse_generate_careplan_request(json.dumps(payload).encode())
#         assert exc_info.value.code == "VALIDATION_ERROR"


@pytest.mark.django_db
class TestFormatValidationAPI:
    """API-level tests for format validation."""

    def test_invalid_npi_returns_400(self):
        client = Client()
        payload = valid_payload()
        payload["provider_npi"] = "123"
        with patch("careplan.services.generate_careplan_task") as m:
            m.delay = lambda x: None
            resp = client.post(
                "/api/generate-careplan/",
                data=json.dumps(payload),
                content_type="application/json",
            )
        assert resp.status_code == 400
        data = resp.json()
        assert data["success"] is False
        assert data["type"] == "validation"
        assert "errors" in data["detail"]

    def test_valid_format_succeeds(self):
        client = Client()
        with patch("careplan.services.generate_careplan_task") as m:
            m.delay = lambda x: None
            resp = client.post(
                "/api/generate-careplan/",
                data=json.dumps(valid_payload()),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
