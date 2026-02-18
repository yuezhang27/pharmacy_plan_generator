"""
Unit tests for Patient duplicate detection (check_patient).
Target: 90%+ coverage of duplication_detection.check_patient and _parse_dob.
"""
import pytest
from datetime import date, datetime

from pharmacy_plan.exceptions import WarningException

from careplan.models import Patient
from careplan.duplication_detection import check_patient, _parse_dob


@pytest.mark.django_db
class TestParseDob:
    """Tests for _parse_dob helper."""

    def test_parse_date_object(self):
        d = date(1990, 1, 15)
        assert _parse_dob(d) == date(1990, 1, 15)

    def test_parse_datetime_object(self):
        dt = datetime(1990, 1, 15, 10, 30, 0)
        assert _parse_dob(dt) == date(1990, 1, 15)

    def test_parse_string_iso_format(self):
        assert _parse_dob("1990-01-15") == date(1990, 1, 15)

    def test_parse_string_with_time(self):
        assert _parse_dob("1990-01-15T10:30:00") == date(1990, 1, 15)

    def test_parse_string_first_10_chars(self):
        assert _parse_dob("1990-01-15extra") == date(1990, 1, 15)


@pytest.mark.django_db
class TestCheckPatientNoExisting:
    """No existing patient - should return None."""

    def test_new_patient_returns_none(self):
        result = check_patient("123456", "John", "Doe", "1990-01-15")
        assert result is None

    def test_new_patient_with_confirm_returns_none(self):
        result = check_patient("123456", "John", "Doe", "1990-01-15", confirm=True)
        assert result is None


@pytest.mark.django_db
class TestCheckPatientSameMrnSameNameDob:
    """MRN + name + DOB all match - return existing patient."""

    def test_exact_match_returns_existing(self):
        Patient.objects.create(
            mrn="123456",
            first_name="John",
            last_name="Doe",
            dob=date(1990, 1, 15),
        )
        result = check_patient("123456", "John", "Doe", "1990-01-15")
        assert result is not None
        assert result.mrn == "123456"
        assert result.first_name == "John"
        assert result.last_name == "Doe"

    def test_exact_match_with_confirm_returns_existing(self):
        p = Patient.objects.create(
            mrn="123456",
            first_name="John",
            last_name="Doe",
            dob=date(1990, 1, 15),
        )
        result = check_patient("123456", "John", "Doe", "1990-01-15", confirm=True)
        assert result.id == p.id


@pytest.mark.django_db
class TestCheckPatientMrnMismatch:
    """MRN exists but name/DOB different - WarningException unless confirm."""

    def test_mrn_mismatch_without_confirm_raises_warning(self):
        Patient.objects.create(
            mrn="123456",
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 5, 20),
        )
        with pytest.raises(WarningException) as exc_info:
            check_patient("123456", "John", "Doe", "1990-01-15", confirm=False)
        assert exc_info.value.code == "PATIENT_MRN_MISMATCH"
        assert "MRN" in exc_info.value.message

    def test_mrn_mismatch_with_confirm_returns_existing(self):
        p = Patient.objects.create(
            mrn="123456",
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 5, 20),
        )
        result = check_patient("123456", "John", "Doe", "1990-01-15", confirm=True)
        assert result.id == p.id
        assert result.mrn == "123456"


@pytest.mark.django_db
class TestCheckPatientNameDobDuplicate:
    """Same name+DOB but different MRN - WarningException unless confirm."""

    def test_name_dob_duplicate_without_confirm_raises_warning(self):
        Patient.objects.create(
            mrn="111111",
            first_name="John",
            last_name="Doe",
            dob=date(1990, 1, 15),
        )
        with pytest.raises(WarningException) as exc_info:
            check_patient("222222", "John", "Doe", "1990-01-15", confirm=False)
        assert exc_info.value.code == "PATIENT_NAME_DOB_DUPLICATE"
        assert "姓名" in exc_info.value.message or "MRN" in exc_info.value.message

    def test_name_dob_duplicate_with_confirm_returns_none(self):
        Patient.objects.create(
            mrn="111111",
            first_name="John",
            last_name="Doe",
            dob=date(1990, 1, 15),
        )
        result = check_patient("222222", "John", "Doe", "1990-01-15", confirm=True)
        assert result is None


@pytest.mark.django_db
class TestCheckPatientEdgeCases:
    """Edge cases for coverage."""

    def test_dob_as_date_object(self):
        Patient.objects.create(
            mrn="123456",
            first_name="John",
            last_name="Doe",
            dob=date(1990, 1, 15),
        )
        result = check_patient("123456", "John", "Doe", date(1990, 1, 15))
        assert result is not None

    def test_dob_as_datetime_object(self):
        Patient.objects.create(
            mrn="123456",
            first_name="John",
            last_name="Doe",
            dob=date(1990, 1, 15),
        )
        result = check_patient(
            "123456", "John", "Doe", datetime(1990, 1, 15, 12, 0, 0)
        )
        assert result is not None
