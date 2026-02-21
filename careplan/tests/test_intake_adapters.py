"""
Unit tests for intake adapters (multi-source data)
"""
import json
import pytest

from pharmacy_plan.exceptions import ValidationError

from careplan.intake import InternalOrder, get_adapter
from careplan.intake.adapters import WebFormAdapter, PharmaCorpAdapter


PARTNER_C_XML = """<?xml version="1.0" encoding="UTF-8"?>
<CareOrderRequest>
    <RequestMetadata>
        <SourceSystem>PharmaCorp_Portal</SourceSystem>
        <RequestId>REQ-2025-00012345</RequestId>
    </RequestMetadata>
    <PatientInformation>
        <MedicalRecordNumber>345678</MedicalRecordNumber>
        <PatientName>
            <FirstName>Robert</FirstName>
            <MiddleName>James</MiddleName>
            <LastName>Williams</LastName>
        </PatientName>
        <DateOfBirth>1972-11-30</DateOfBirth>
    </PatientInformation>
    <PrescriberInformation>
        <FullName>Dr. Michael Chen</FullName>
        <NPINumber>5678901234</NPINumber>
    </PrescriberInformation>
    <DiagnosisList>
        <PrimaryDiagnosis>
            <ICDCode>G70.01</ICDCode>
        </PrimaryDiagnosis>
        <SecondaryDiagnoses>
            <Diagnosis><ICDCode>I10</ICDCode></Diagnosis>
            <Diagnosis><ICDCode>E78.5</ICDCode></Diagnosis>
        </SecondaryDiagnoses>
    </DiagnosisList>
    <MedicationOrder>
        <DrugName>Octagam</DrugName>
    </MedicationOrder>
    <MedicationHistory>
        <Medication>
            <MedicationName>Pyridostigmine</MedicationName>
            <Dosage>60 mg</Dosage>
            <Route>Oral</Route>
            <Frequency>Every 6 hours</Frequency>
        </Medication>
    </MedicationHistory>
    <ClinicalDocumentation>
        <NarrativeText>58 y/o male with known MG presenting with acute exacerbation.</NarrativeText>
    </ClinicalDocumentation>
</CareOrderRequest>"""


class TestWebFormAdapter:
    """Web form JSON adapter."""

    def test_valid_json_transforms(self):
        payload = {
            "patient_mrn": "123456",
            "patient_first_name": "John",
            "patient_last_name": "Doe",
            "patient_dob": "1990-01-15",
            "provider_npi": "1234567890",
            "provider_name": "Dr. Jane",
            "primary_diagnosis": "E11.9",
            "medication_name": "Metformin",
            "patient_records": "Stable.",
        }
        adapter = WebFormAdapter()
        order = adapter.process(json.dumps(payload).encode())
        assert order.patient.mrn == "123456"
        assert order.patient.first_name == "John"
        assert order.provider.npi == "1234567890"
        assert order.careplan.medication_name == "Metformin"
        assert order.raw_data is not None

    def test_invalid_json_raises(self):
        adapter = WebFormAdapter()
        with pytest.raises(ValidationError) as exc_info:
            adapter.process(b"not json")
        assert exc_info.value.code == "INVALID_JSON"


class TestPharmaCorpAdapter:
    """PharmaCorp XML adapter."""

    def test_valid_xml_transforms(self):
        adapter = PharmaCorpAdapter()
        order = adapter.process(PARTNER_C_XML)
        assert order.patient.mrn == "345678"
        assert order.patient.first_name == "Robert"
        assert order.patient.last_name == "Williams"
        assert order.patient.dob == "1972-11-30"
        assert order.provider.npi == "5678901234"
        assert order.provider.name == "Dr. Michael Chen"
        assert order.careplan.primary_diagnosis == "G70.01"
        assert order.careplan.additional_diagnosis == "I10, E78.5"
        assert order.careplan.medication_name == "Octagam"
        assert "Pyridostigmine" in order.careplan.medication_history
        assert "MG" in order.careplan.patient_records
        assert order.raw_data == PARTNER_C_XML

    def test_to_create_careplan_dict(self):
        adapter = PharmaCorpAdapter()
        order = adapter.process(PARTNER_C_XML)
        d = order.to_create_careplan_dict(confirm=True)
        assert d["patient_mrn"] == "345678"
        assert d["provider_npi"] == "5678901234"
        assert d["confirm"] is True

    def test_invalid_xml_raises(self):
        adapter = PharmaCorpAdapter()
        with pytest.raises(ValidationError):
            adapter.process("<invalid")


class TestGetAdapter:
    """Factory function."""

    def test_webform_returns_adapter(self):
        adapter = get_adapter("webform")
        assert isinstance(adapter, WebFormAdapter)

    def test_pharmacorp_returns_adapter(self):
        adapter = get_adapter("pharmacorp_portal")
        assert isinstance(adapter, PharmaCorpAdapter)

    def test_unknown_source_raises(self):
        with pytest.raises(ValueError) as exc_info:
            get_adapter("unknown_hospital")
        assert "Unknown intake source" in str(exc_info.value)
