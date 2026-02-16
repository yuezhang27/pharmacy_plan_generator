"""
数据校验和格式转换（前端 ↔ 后端）
当前不做校验，仅做格式转换
"""
import json


def parse_generate_careplan_request(body):
    """
    解析 POST body (JSON) -> dict
    """
    return json.loads(body)
