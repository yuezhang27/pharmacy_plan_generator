"""
重复检测逻辑
- Provider: NPI 相同 + 名字不同 → 必须阻止
- Patient: MRN 相同 + 名字/DOB 不同 → 警告；名字+DOB 相同 + MRN 不同 → 警告
- Order (CarePlan): 同一患者 + 同一药物 + 同一天 → 必须阻止；不同天 → 警告（confirm 可跳过）
"""
from datetime import date, datetime

from .models import Patient, Provider, CarePlan


class DuplicationError(Exception):
    def __init__(self, message, status_code=409):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _parse_dob(dob):
    if isinstance(dob, date) and not isinstance(dob, datetime):
        return dob
    if isinstance(dob, datetime):
        return dob.date()
    if isinstance(dob, str):
        return datetime.strptime(dob[:10], '%Y-%m-%d').date()
    return dob


def check_provider(npi, name):
    """
    NPI 相同 + 名字相同 → 返回现有 provider
    NPI 相同 + 名字不同 → 抛出 DuplicationError (409)
    """
    existing = Provider.objects.filter(npi=npi).first()
    if not existing:
        return None
    if existing.name == name:
        return existing
    raise DuplicationError("NPI 已存在但提供者姓名不一致，必须修正", status_code=409)


def check_patient(mrn, first_name, last_name, dob, confirm=False):
    """
    MRN 相同 + 名字和 DOB 都相同 → 返回现有 patient
    MRN 相同 + 名字或 DOB 不同 → 警告；confirm 则复用现有
    名字+DOB 相同 + MRN 不同 → 警告；confirm 则创建新
    """
    dob = _parse_dob(dob)
    existing_by_mrn = Patient.objects.filter(mrn=mrn).first()
    existing_by_name_dob = Patient.objects.filter(
        first_name=first_name,
        last_name=last_name,
        dob=dob
    ).exclude(mrn=mrn).first()

    if existing_by_mrn:
        if (existing_by_mrn.first_name == first_name and
                existing_by_mrn.last_name == last_name and
                existing_by_mrn.dob == dob):
            return existing_by_mrn
        if not confirm:
            raise DuplicationError(
                "MRN 已存在但患者姓名或出生日期不一致，请确认后继续",
                status_code=409
            )
        return existing_by_mrn

    if existing_by_name_dob:
        if not confirm:
            raise DuplicationError(
                "姓名和出生日期已存在但 MRN 不同，请确认后继续",
                status_code=409
            )
        return None

    return None


def check_order(patient, medication_name, confirm=False):
    """
    同一患者 + 同一药物 + 同一天 → 抛出 DuplicationError (409)
    同一患者 + 同一药物 + 不同天 → 警告；confirm 则跳过
    """
    today = date.today()
    same_day = CarePlan.objects.filter(
        patient=patient,
        medication_name=medication_name,
        created_at__date=today
    ).exists()
    if same_day:
        raise DuplicationError(
            "同一患者同日已有相同药物订单，无法重复提交（必须阻止）",
            status_code=409
        )

    diff_day = CarePlan.objects.filter(
        patient=patient,
        medication_name=medication_name
    ).exclude(created_at__date=today).exists()
    if diff_day and not confirm:
        raise DuplicationError(
            "同一患者已有相同药物订单（不同日期），请确认后继续",
            status_code=409
        )
