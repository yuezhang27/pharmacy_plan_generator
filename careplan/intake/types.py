"""
内部标准格式：业务逻辑唯一认识的格式
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PatientInfo:
    """患者信息（内部标准）"""
    mrn: str
    first_name: str
    last_name: str
    dob: str  # YYYY-MM-DD


@dataclass
class ProviderInfo:
    """提供者信息（内部标准）"""
    npi: str
    name: str


@dataclass
class CarePlanInfo:
    """Care Plan 订单信息（内部标准）"""
    primary_diagnosis: str
    medication_name: str
    patient_records: str
    additional_diagnosis: str = ""
    medication_history: str = ""


@dataclass
class InternalOrder:
    """
    内部标准订单格式
    业务逻辑（如 create_careplan）只认识此格式
    """
    patient: PatientInfo
    provider: ProviderInfo
    careplan: CarePlanInfo
    source: str  # 数据来源标识，如 "webform", "pharmacorp_portal"
    raw_data: Any = field(default=None, repr=False)  # 保留原始数据用于排查

    def to_create_careplan_dict(self, confirm: bool = False) -> dict:
        """转换为 create_careplan 所需的 dict 格式"""
        return {
            "patient_mrn": self.patient.mrn,
            "patient_first_name": self.patient.first_name,
            "patient_last_name": self.patient.last_name,
            "patient_dob": self.patient.dob,
            "provider_npi": self.provider.npi,
            "provider_name": self.provider.name,
            "primary_diagnosis": self.careplan.primary_diagnosis,
            "additional_diagnosis": self.careplan.additional_diagnosis,
            "medication_name": self.careplan.medication_name,
            "medication_history": self.careplan.medication_history,
            "patient_records": self.careplan.patient_records,
            "confirm": confirm,
        }
