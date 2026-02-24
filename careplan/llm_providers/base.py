"""
LLM 服务抽象基类
业务代码只依赖此接口，不关心具体实现
"""
from abc import ABC, abstractmethod


class BaseLLMService(ABC):
    """
    抽象基类：所有 LLM 服务的父类
    新增 LLM 时只需继承此类并实现 generate
    """

    provider_id: str = "unknown"  # 子类覆盖，如 "openai", "claude"

    @abstractmethod
    def generate(
        self,
        system_message: str,
        user_message: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        调用 LLM 生成文本
        :param system_message: 系统提示（角色设定）
        :param user_message: 用户提示（实际任务内容）
        :param temperature: 随机度 0-1
        :param max_tokens: 最大生成 token 数
        :return: 生成的文本内容
        """
        pass
