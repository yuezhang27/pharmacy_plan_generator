"""
数据校验和格式转换（前端 ↔ 后端）
"""
import json

from pharmacy_plan.exceptions import ValidationError


def parse_generate_careplan_request(body):
    """
    解析 POST body (JSON) -> dict
    JSON 格式错误时抛出 ValidationError
    """
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise ValidationError(
            message="Invalid JSON format",
            code="INVALID_JSON",
            detail={"error": str(e)},
        )
