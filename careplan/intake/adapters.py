"""
多数据源 Adapter：解析、转换、校验
"""
import json
import re
from datetime import datetime
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from typing import Any

from pharmacy_plan.exceptions import ValidationError

from .types import InternalOrder, PatientInfo, ProviderInfo, CarePlanInfo

# 与 serializers 一致的格式校验
_NPI_PATTERN = re.compile(r"^\d{10}$")
_MRN_PATTERN = re.compile(r"^\d{6}$")
_ICD10_PATTERN = re.compile(r"^[A-Za-z][0-9]{2}(\.[0-9A-Za-z]{1,4})?$")


class BaseIntakeAdapter(ABC):
    """
    抽象基类：所有数据源 Adapter 的父类
    新增数据源时只需继承此类并实现 parse/transform/validate
    """

    source_id: str = "unknown"  # 子类覆盖，如 "webform", "pharmacorp_portal"

    def process(self, raw: bytes | str, source: str | None = None) -> InternalOrder:
        """
        完整流程：parse -> transform -> validate
        返回 InternalOrder，失败时抛出 ValidationError
        """
        parsed = self.parse(raw)
        order = self.transform(parsed)
        self.validate(order)
        order.source = source or self.source_id
        order.raw_data = raw
        return order

    @abstractmethod
    def parse(self, raw: bytes | str) -> Any:
        """
        解析原始数据（JSON/XML 等）为 Python 结构
        解析失败时抛出 ValidationError
        """
        pass

    @abstractmethod
    def transform(self, parsed: Any) -> InternalOrder:
        """
        将解析后的结构转换为 InternalOrder
        """
        pass

    def validate(self, order: InternalOrder) -> None:
        """
        验证转换后的 InternalOrder
        与 serializers 格式校验一致：NPI 10 位、MRN 6 位、DOB、ICD-10
        """
        errors = []
        if not order.patient.mrn or not _MRN_PATTERN.match(order.patient.mrn.strip()):
            errors.append({"field": "patient.mrn", "message": "MRN 必须为 6 位数字"})
        if not order.provider.npi or not _NPI_PATTERN.match(order.provider.npi.strip()):
            errors.append({"field": "provider.npi", "message": "NPI 必须为 10 位数字"})
        if not order.patient.dob:
            errors.append({"field": "patient.dob", "message": "出生日期格式应为 YYYY-MM-DD"})
        else:
            s = order.patient.dob.strip()[:10]
            if len(s) != 10 or s[4] != "-" or s[7] != "-":
                errors.append({"field": "patient.dob", "message": "出生日期格式应为 YYYY-MM-DD"})
            else:
                try:
                    datetime.strptime(s, "%Y-%m-%d").date()
                except ValueError:
                    errors.append({"field": "patient.dob", "message": "出生日期必须是合法日期"})
        if not order.careplan.primary_diagnosis:
            errors.append({"field": "careplan.primary_diagnosis", "message": "主要诊断不能为空"})
        elif not _ICD10_PATTERN.match(order.careplan.primary_diagnosis.strip()):
            errors.append({"field": "careplan.primary_diagnosis", "message": "主要诊断需符合 ICD-10 格式（如 A00, E11.9）"})
        if not order.careplan.medication_name:
            errors.append({"field": "careplan.medication_name", "message": "药物名称不能为空"})
        if not order.careplan.patient_records:
            errors.append({"field": "careplan.patient_records", "message": "患者记录不能为空"})
        if errors:
            raise ValidationError(
                message="数据格式校验失败",
                code="VALIDATION_ERROR",
                detail={"errors": errors},
            )


class WebFormAdapter(BaseIntakeAdapter):
    """
    现有 Web 表单 JSON 格式
    字段：patient_first_name, patient_mrn, provider_npi 等（与 create_careplan 一致）
    """

    source_id = "webform"

    def parse(self, raw: bytes | str) -> dict:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValidationError(
                message="Invalid JSON format",
                code="INVALID_JSON",
                detail={"error": str(e)},
            )

    def transform(self, parsed: dict) -> InternalOrder:
        return InternalOrder(
            patient=PatientInfo(
                mrn=str(parsed.get("patient_mrn", "")).strip(),
                first_name=str(parsed.get("patient_first_name", "")).strip(),
                last_name=str(parsed.get("patient_last_name", "")).strip(),
                dob=str(parsed.get("patient_dob", ""))[:10],
            ),
            provider=ProviderInfo(
                npi=str(parsed.get("provider_npi", "")).strip(),
                name=str(parsed.get("provider_name", "")).strip(),
            ),
            careplan=CarePlanInfo(
                primary_diagnosis=str(parsed.get("primary_diagnosis", "")).strip(),
                additional_diagnosis=str(parsed.get("additional_diagnosis", "")).strip(),
                medication_name=str(parsed.get("medication_name", "")).strip(),
                medication_history=str(parsed.get("medication_history", "")).strip(),
                patient_records=str(parsed.get("patient_records", "")).strip(),
            ),
            source=self.source_id,
            request_flags={
                "confirm": parsed.get("confirm") is True,
                "llm_provider": (parsed.get("llm_provider") or "").strip() or None,
            },
        )


class MedCenterJsonAdapter(BaseIntakeAdapter):
    """
    MedCenter 开放 API JSON 格式
    字段：pt (mrn, fname, lname, dob), provider (name, npi_num), dx (primary, secondary),
    rx (med_name), med_hx, clinical_notes
    """

    source_id = "medcenter"

    def _dob_mmddyyyy_to_iso(self, s: str) -> str:
        """将 MM/DD/YYYY 转为 YYYY-MM-DD"""
        if not s or not isinstance(s, str):
            return ""
        s = s.strip()
        try:
            dt = datetime.strptime(s[:10], "%m/%d/%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return s[:10]  # 原样返回前 10 字符，由 validate 报错

    def parse(self, raw: bytes | str) -> dict:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValidationError(
                message="Invalid JSON format",
                code="INVALID_JSON",
                detail={"error": str(e)},
            )

    def transform(self, parsed: dict) -> InternalOrder:
        pt = parsed.get("pt") or {}
        provider = parsed.get("provider") or {}
        dx = parsed.get("dx") or {}
        rx = parsed.get("rx") or {}

        mrn = str(pt.get("mrn", "")).strip()
        fname = str(pt.get("fname", "")).strip()
        lname = str(pt.get("lname", "")).strip()
        dob_raw = str(pt.get("dob", ""))
        dob = self._dob_mmddyyyy_to_iso(dob_raw)

        npi = str(provider.get("npi_num", "")).strip()
        provider_name = str(provider.get("name", "")).strip()

        primary = str(dx.get("primary", "")).strip()
        secondary_raw = dx.get("secondary")
        if isinstance(secondary_raw, list):
            additional = ", ".join(str(x).strip() for x in secondary_raw if x)
        else:
            additional = str(secondary_raw or "").strip()

        med_name = str(rx.get("med_name", "")).strip()

        med_hx_raw = parsed.get("med_hx") or []
        if isinstance(med_hx_raw, list):
            medication_history = "; ".join(str(x) for x in med_hx_raw if x)
        else:
            medication_history = str(med_hx_raw or "")

        clinical_notes = str(parsed.get("clinical_notes", "")).strip()
        allergies_raw = parsed.get("allergies") or []
        if isinstance(allergies_raw, list) and allergies_raw:
            allergies_str = "Allergies: " + ", ".join(str(a) for a in allergies_raw)
            patient_records = f"{allergies_str}\n\n{clinical_notes}" if clinical_notes else allergies_str
        else:
            patient_records = clinical_notes or "(No clinical notes)"

        return InternalOrder(
            patient=PatientInfo(mrn=mrn, first_name=fname, last_name=lname, dob=dob),
            provider=ProviderInfo(npi=npi, name=provider_name),
            careplan=CarePlanInfo(
                primary_diagnosis=primary,
                additional_diagnosis=additional,
                medication_name=med_name,
                medication_history=medication_history,
                patient_records=patient_records,
            ),
            source=self.source_id,
            request_flags={
                "confirm": parsed.get("confirm") is True,
                "llm_provider": (parsed.get("llm_provider") or "").strip() or None,
            },
        )


class PharmaCorpAdapter(BaseIntakeAdapter):
    """
    PharmaCorp Portal XML 格式（partner_c_data 示例）
    字段：MedicalRecordNumber, PatientName/FirstName, NPINumber, ICDCode 等
    """

    source_id = "pharmacorp_portal"

    def _text(self, elem: ET.Element | None, default: str = "") -> str:
        if elem is None:
            return default
        return (elem.text or "").strip()

    def parse(self, raw: bytes | str) -> ET.Element:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as e:
            raise ValidationError(
                message="Invalid XML format",
                code="INVALID_XML",
                detail={"error": str(e)},
            )
        if root.tag != "CareOrderRequest":
            raise ValidationError(
                message="Expected CareOrderRequest root element",
                code="INVALID_XML",
                detail={"root": root.tag},
            )
        return root

    def transform(self, parsed: ET.Element) -> InternalOrder:
        ns = {}  # 无 namespace

        # Patient
        pi = parsed.find("PatientInformation", ns)
        mrn = self._text(pi.find("MedicalRecordNumber", ns)) if pi is not None else ""
        pn = pi.find("PatientName", ns) if pi is not None else None
        first = self._text(pn.find("FirstName", ns)) if pn is not None else ""
        last = self._text(pn.find("LastName", ns)) if pn is not None else ""
        dob = self._text(pi.find("DateOfBirth", ns))[:10] if pi is not None else ""

        # Provider
        pr = parsed.find("PrescriberInformation", ns)
        npi = self._text(pr.find("NPINumber", ns)) if pr is not None else ""
        name = self._text(pr.find("FullName", ns)) if pr is not None else ""

        # Diagnosis
        dl = parsed.find("DiagnosisList", ns)
        primary_icd = ""
        secondary_icds = []
        if dl is not None:
            pd = dl.find("PrimaryDiagnosis", ns)
            if pd is not None:
                primary_icd = self._text(pd.find("ICDCode", ns))
            sd = dl.find("SecondaryDiagnoses", ns)
            if sd is not None:
                for d in sd.findall("Diagnosis", ns):
                    icd = self._text(d.find("ICDCode", ns))
                    if icd:
                        secondary_icds.append(icd)
        additional = ", ".join(secondary_icds)

        # Medication
        mo = parsed.find("MedicationOrder", ns)
        drug = self._text(mo.find("DrugName", ns)) if mo is not None else ""

        # Medication History
        mh = parsed.find("MedicationHistory", ns)
        med_lines = []
        if mh is not None:
            for m in mh.findall("Medication", ns):
                name_med = self._text(m.find("MedicationName", ns))
                dose = self._text(m.find("Dosage", ns))
                route = self._text(m.find("Route", ns))
                freq = self._text(m.find("Frequency", ns))
                med_lines.append(f"{name_med} {dose} {route} {freq}")
        medication_history = "; ".join(med_lines)

        # Clinical Documentation -> patient_records
        cd = parsed.find("ClinicalDocumentation", ns)
        narrative = self._text(cd.find("NarrativeText", ns)) if cd is not None else ""

        return InternalOrder(
            patient=PatientInfo(mrn=mrn, first_name=first, last_name=last, dob=dob),
            provider=ProviderInfo(npi=npi, name=name),
            careplan=CarePlanInfo(
                primary_diagnosis=primary_icd,
                additional_diagnosis=additional,
                medication_name=drug,
                medication_history=medication_history,
                patient_records=narrative or "(No clinical documentation)",
            ),
            source=self.source_id,
        )
