"""
数据校验和格式转换（前端 ↔ 后端）
"""
import json
import re
from datetime import datetime

from pharmacy_plan.exceptions import ValidationError

# 必填字段
REQUIRED_FIELDS = [
    "provider_npi",
    "provider_name",
    "patient_mrn",
    "patient_first_name",
    "patient_last_name",
    "patient_dob",
    "primary_diagnosis",
    "medication_name",
    "patient_records",
]

# NPI: 10 位数字
NPI_PATTERN = re.compile(r"^\d{10}$")

# MRN: 6 位数字
MRN_PATTERN = re.compile(r"^\d{6}$")

# ICD-10: 1 字母 + 2 数字 + 可选 . + 1-4 位字母数字（如 A00, E11.9, A18.32）
ICD10_PATTERN = re.compile(r"^[A-Za-z][0-9]{2}(\.[0-9A-Za-z]{1,4})?$")


def _validate_npi(value):
    """NPI 必须 10 位数字"""
    if not value or not isinstance(value, str):
        return "NPI 必须为 10 位数字"
    if not NPI_PATTERN.match(value.strip()):
        return "NPI 必须为 10 位数字"
    return None


def _validate_mrn(value):
    """MRN 必须 6 位数字"""
    if not value or not isinstance(value, str):
        return "MRN 必须为 6 位数字"
    if not MRN_PATTERN.match(value.strip()):
        return "MRN 必须为 6 位数字"
    return None


def _validate_dob(value):
    """DOB 必须为 YYYY-MM-DD 格式的合法日期"""
    if not value or not isinstance(value, str):
        return "出生日期格式应为 YYYY-MM-DD"
    s = value.strip()[:10]
    if len(s) != 10 or s[4] != "-" or s[7] != "-":
        return "出生日期格式应为 YYYY-MM-DD"
    try:
        datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return "出生日期必须是合法日期"
    return None


def _validate_icd10(value):
    """primary_diagnosis 需符合 ICD-10 格式"""
    if not value or not isinstance(value, str):
        return "主要诊断需符合 ICD-10 格式（如 A00, E11.9）"
    if not ICD10_PATTERN.match(value.strip()):
        return "主要诊断需符合 ICD-10 格式（如 A00, E11.9）"
    return None


def _validate_required_string(value, field_name):
    """必填字符串：非空"""
    if value is None or (isinstance(value, str) and not value.strip()):
        return f"{field_name} 不能为空"
    return None


def validate_generate_careplan_data(data):
    """
    校验 generate careplan 请求数据格式。
    失败时抛出 ValidationError，detail 包含所有错误。
    """
    if not isinstance(data, dict):
        raise ValidationError(
            message="请求体必须是 JSON 对象",
            code="INVALID_REQUEST",
            detail={"errors": [{"field": "_", "message": "请求体必须是 JSON 对象"}]},
        )

    errors = []

    # 必填字段
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append({"field": field, "message": "该字段为必填"})
        elif field in ("provider_name", "patient_first_name", "patient_last_name", "medication_name", "patient_records"):
            msg = _validate_required_string(data[field], field)
            if msg:
                errors.append({"field": field, "message": msg})

    # 格式校验（仅当字段存在时）
    validators = [
        ("provider_npi", _validate_npi),
        ("patient_mrn", _validate_mrn),
        ("patient_dob", _validate_dob),
        ("primary_diagnosis", _validate_icd10),
    ]
    for field, validator in validators:
        if field in data and data[field] is not None:
            msg = validator(data[field])
            if msg:
                errors.append({"field": field, "message": msg})

    if errors:
        raise ValidationError(
            message="数据格式校验失败",
            code="VALIDATION_ERROR",
            detail={"errors": errors},
        )


def parse_generate_careplan_request(body):
    """
    解析 POST body (JSON) -> dict
    JSON 格式错误时抛出 ValidationError
    解析成功后调用格式校验，校验失败时抛出 ValidationError
    """
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise ValidationError(
            message="Invalid JSON format",
            code="INVALID_JSON",
            detail={"error": str(e)},
        )

    validate_generate_careplan_data(data)
    return data
