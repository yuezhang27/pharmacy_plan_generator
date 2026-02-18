"""
Unit tests for Provider and Order duplicate detection.
"""
import pytest
from datetime import date
from unittest.mock import patch

from pharmacy_plan.exceptions import BlockError, WarningException

from careplan.models import Patient, Provider, CarePlan
from careplan.duplication_detection import check_provider, check_order


@pytest.mark.django_db
class TestCheckProvider:
    """Tests for check_provider."""

    def test_no_existing_returns_none(self):
        assert check_provider("1234567890", "Dr. Jane") is None

    def test_same_npi_same_name_returns_existing(self):
        p = Provider.objects.create(npi="1234567890", name="Dr. Jane")
        result = check_provider("1234567890", "Dr. Jane")
        assert result.id == p.id

    def test_same_npi_different_name_raises_block(self):
        Provider.objects.create(npi="1234567890", name="Dr. Jane")
        with pytest.raises(BlockError) as exc_info:
            check_provider("1234567890", "Dr. John")
        assert exc_info.value.code == "PROVIDER_NPI_NAME_MISMATCH"


@pytest.mark.django_db
class TestCheckOrder:
    """Tests for check_order."""

    def test_same_day_duplicate_raises_block(self):
        patient = Patient.objects.create(
            mrn="123456",
            first_name="John",
            last_name="Doe",
            dob=date(1990, 1, 15),
        )
        provider = Provider.objects.create(npi="1234567890", name="Dr. Jane")
        CarePlan.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis="D1",
            medication_name="Metformin",
            patient_records="r",
            status="completed",
        )
        with pytest.raises(BlockError) as exc_info:
            check_order(patient, "Metformin", confirm=False)
        assert exc_info.value.code == "ORDER_SAME_DAY_DUPLICATE"

    def test_diff_day_without_confirm_raises_warning(self):
        patient = Patient.objects.create(
            mrn="123456",
            first_name="John",
            last_name="Doe",
            dob=date(1990, 1, 15),
        )
        provider = Provider.objects.create(npi="1234567890", name="Dr. Jane")
        with patch("careplan.duplication_detection.date") as mock_date:
            mock_date.today.return_value = date(2025, 2, 12)
            CarePlan.objects.create(
                patient=patient,
                provider=provider,
                primary_diagnosis="D1",
                medication_name="Metformin",
                patient_records="r",
                status="completed",
            )
        with patch("careplan.duplication_detection.date") as mock_date:
            mock_date.today.return_value = date(2025, 2, 13)
            with pytest.raises(WarningException) as exc_info:
                check_order(patient, "Metformin", confirm=False)
            assert exc_info.value.code == "ORDER_DIFF_DAY_DUPLICATE"

    def test_diff_day_with_confirm_passes(self):
        patient = Patient.objects.create(
            mrn="123456",
            first_name="John",
            last_name="Doe",
            dob=date(1990, 1, 15),
        )
        provider = Provider.objects.create(npi="1234567890", name="Dr. Jane")
        with patch("careplan.duplication_detection.date") as mock_date:
            mock_date.today.return_value = date(2025, 2, 12)
            CarePlan.objects.create(
                patient=patient,
                provider=provider,
                primary_diagnosis="D1",
                medication_name="Metformin",
                patient_records="r",
                status="completed",
            )
        with patch("careplan.duplication_detection.date") as mock_date:
            mock_date.today.return_value = date(2025, 2, 13)
            check_order(patient, "Metformin", confirm=True)

    def test_no_duplicate_passes(self):
        patient = Patient.objects.create(
            mrn="123456",
            first_name="John",
            last_name="Doe",
            dob=date(1990, 1, 15),
        )
        check_order(patient, "Metformin", confirm=False)
