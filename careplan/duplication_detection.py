"""
重复检测逻辑
- Provider: NPI 相同 + 名字不同 → 必须阻止 (BlockError)
- Patient: MRN 相同 + 名字/DOB 不同 → 警告 (WarningException)；名字+DOB 相同 + MRN 不同 → 警告
- Order (CarePlan): 同一患者 + 同一药物 + 同一天 → 必须阻止；不同天 → 警告（confirm 可跳过）
"""
from datetime import date, datetime

from pharmacy_plan.exceptions import BlockError, WarningException

from .models import Patient, Provider, CarePlan


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
    raise BlockError(
        message="NPI 已存在但提供者姓名不一致，必须修正",
        code="PROVIDER_NPI_NAME_MISMATCH",
    )


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
            raise WarningException(
                message="MRN 已存在但患者姓名或出生日期不一致，请确认后继续",
                code="PATIENT_MRN_MISMATCH",
            )
        return existing_by_mrn

    if existing_by_name_dob:
        if not confirm:
            raise WarningException(
                message="姓名和出生日期已存在但 MRN 不同，请确认后继续",
                code="PATIENT_NAME_DOB_DUPLICATE",
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
        raise BlockError(
            message="同一患者同日已有相同药物订单，无法重复提交",
            code="ORDER_SAME_DAY_DUPLICATE",
        )

    diff_day = CarePlan.objects.filter(
        patient=patient,
        medication_name=medication_name
    ).exclude(created_at__date=today).exists()
    if diff_day and not confirm:
        raise WarningException(
            message="同一患者已有相同药物订单（不同日期），请确认后继续",
            code="ORDER_DIFF_DAY_DUPLICATE",
        )
