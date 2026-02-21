# 多数据源 Adapter

将不同医院/诊所的订单格式统一转换为 `InternalOrder`，业务逻辑只认识 `InternalOrder`。

## 使用示例

```python
from careplan.intake import get_adapter
from careplan.services import create_careplan

# 根据来源获取 Adapter
adapter = get_adapter("pharmacorp_portal")
order = adapter.process(xml_bytes, source="pharmacorp_portal")

# 业务逻辑只认识 InternalOrder
data = order.to_create_careplan_dict(confirm=False)
result = create_careplan(data)

# 排查问题时可用 order.raw_data 查看原始数据
```

## 新增数据源

1. 在 `adapters.py` 中新增 Adapter 类，继承 `BaseIntakeAdapter`
2. 实现 `parse()` 和 `transform()`
3. 在 `factory.py` 的 `_ADAPTER_REGISTRY` 中注册

业务代码（如 `create_careplan`）无需修改。
