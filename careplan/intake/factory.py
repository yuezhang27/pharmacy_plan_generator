"""
工厂函数：根据来源返回对应 Adapter
新增数据源时在此注册，业务代码无需修改
"""
from typing import Dict, Type

from .adapters import BaseIntakeAdapter, WebFormAdapter, PharmaCorpAdapter

# 来源标识 -> Adapter 类
_ADAPTER_REGISTRY: Dict[str, Type[BaseIntakeAdapter]] = {
    "webform": WebFormAdapter,
    "pharmacorp_portal": PharmaCorpAdapter,
    "pharmacorp": PharmaCorpAdapter,  # 别名
}


def get_adapter(source: str) -> BaseIntakeAdapter:
    """
    根据来源返回对应的 Adapter 实例
    source: 如 "webform", "pharmacorp_portal"
    """
    adapter_cls = _ADAPTER_REGISTRY.get(source.lower())
    if adapter_cls is None:
        raise ValueError(f"Unknown intake source: {source}. Known: {list(_ADAPTER_REGISTRY.keys())}")
    return adapter_cls()


def register_adapter(source: str, adapter_cls: Type[BaseIntakeAdapter]) -> None:
    """注册新 Adapter（可选，用于动态扩展）"""
    _ADAPTER_REGISTRY[source.lower()] = adapter_cls
