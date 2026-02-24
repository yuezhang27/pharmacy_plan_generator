# LLM 服务抽象层

业务代码只调用 `generate_careplan`，不关心具体 LLM 实现。支持 OpenAI、Claude，可配置切换。

## 配置

- **USE_MOCK_LLM**=1：使用 Mock（不调真实 API），默认
- **USE_MOCK_LLM**=0：使用真实 LLM
- **LLM_PROVIDER**：openai | claude，默认 openai
- **OPENAI_API_KEY**：OpenAI API Key
- **ANTHROPIC_API_KEY**：Claude API Key

## 前端选择

表单中「LLM Model」下拉框可选择 openai/claude，提交时传入 `llm_provider`，会存入 CarePlan 并在任务执行时使用。

## 新增 LLM

1. 在 `llm_providers/` 中新增 Service 类，继承 `BaseLLMService`
2. 实现 `generate(system_message, user_message, **kwargs) -> str`
3. 在 `factory.py` 的 `_SERVICE_REGISTRY` 中注册
