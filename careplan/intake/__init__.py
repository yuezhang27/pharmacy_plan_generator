"""
多数据源接入：Adapter 模式
将不同来源（JSON/XML、不同字段命名）统一转换为 InternalOrder，
业务逻辑只认识 InternalOrder，新增数据源只需新增 Adapter。
"""
from .types import InternalOrder, PatientInfo, ProviderInfo, CarePlanInfo
from .adapters import BaseIntakeAdapter
from .factory import get_adapter

__all__ = [
    "InternalOrder",
    "PatientInfo",
    "ProviderInfo",
    "CarePlanInfo",
    "BaseIntakeAdapter",
    "get_adapter",
]
