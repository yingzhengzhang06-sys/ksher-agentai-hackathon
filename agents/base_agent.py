"""
Agent 抽象基类 — 所有 Agent 的父类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Generator, Optional
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AGENT_TEMPERATURE


class BaseAgent(ABC):
    """
    所有 Agent 的抽象基类。

    子类必须实现：
        - generate(context) → dict: 同步生成结构化结果
        - build_system_prompt(knowledge) → str: 构建系统提示词
        - build_user_message(context) → str: 构建用户消息

    可选重写：
        - stream(context): 流式生成（默认通过 LLM 流式接口实现）
        - parse_response(text) → dict: 解析 LLM 返回的文本为结构化 dict
    """

    agent_name: str = "base"
    temperature: float = 0.7

    def __init__(self, llm_client, knowledge_loader):
        """
        Args:
            llm_client: LLMClient 实例（提供 stream_text / call_sync）
            knowledge_loader: KnowledgeLoader 实例（提供 load 方法）
        """
        self.llm_client = llm_client
        self.knowledge_loader = knowledge_loader
        # 如果子类显式定义了 temperature（非继承基类默认值），则保留；否则从配置查找
        class_temp = getattr(self.__class__, 'temperature', None)
        if class_temp is None or class_temp == BaseAgent.temperature:
            self.temperature = AGENT_TEMPERATURE.get(self.agent_name, 0.7)

    @abstractmethod
    def generate(self, context: dict) -> dict:
        """
        同步生成，返回结构化结果 dict。

        Args:
            context: 客户上下文（包含 industry, target_country, monthly_volume 等）

        Returns:
            dict: 结构化输出（各 Agent 格式见 INTERFACES.md）
        """
        pass

    def stream(self, context: dict) -> Generator[str, None, None]:
        """
        流式生成，yield 文本 chunk（UI 直接消费）。

        默认实现：调用 LLM 流式接口，先加载知识库构建 prompt，然后流式输出。
        子类可重写以实现自定义流式行为。

        Args:
            context: 客户上下文

        Yields:
            str: 纯文本 chunk
        """
        # 1. 加载知识库
        knowledge = self.knowledge_loader.load(self.agent_name, context)

        # 2. 构建 Prompt
        system = self.build_system_prompt(knowledge)
        user_msg = self.build_user_message(context)

        # 3. 流式调用 LLM
        yield from self.llm_client.stream_text(
            agent_name=self.agent_name,
            system=system,
            user_msg=user_msg,
            temperature=self.temperature,
        )

    @abstractmethod
    def build_system_prompt(self, knowledge: str) -> str:
        """
        构建 System Prompt（含知识库注入内容）。

        Args:
            knowledge: 从 KnowledgeLoader 加载的知识库文本

        Returns:
            str: System Prompt 文本
        """
        pass

    @abstractmethod
    def build_user_message(self, context: dict) -> str:
        """
        构建 User Message（客户上下文）。

        Args:
            context: 客户上下文 dict

        Returns:
            str: User Message 文本
        """
        pass

    def _call_llm_sync(self, context: dict) -> str:
        """
        内部辅助：同步调用 LLM，返回完整文本。

        Args:
            context: 客户上下文

        Returns:
            str: LLM 返回的完整文本
        """
        knowledge = self.knowledge_loader.load(self.agent_name, context)
        system = self.build_system_prompt(knowledge)
        user_msg = self.build_user_message(context)

        return self.llm_client.call_sync(
            agent_name=self.agent_name,
            system=system,
            user_msg=user_msg,
            temperature=self.temperature,
        )

    def _safe_parse_json(self, text: str) -> Optional[dict]:
        """
        安全解析 JSON，处理 markdown 代码块包裹的情况。

        Args:
            text: 可能包含 JSON 的文本

        Returns:
            dict or None: 解析成功返回 dict，失败返回 None
        """
        if not text:
            return None

        # 尝试直接解析
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # 尝试提取 markdown 代码块中的 JSON
        import re
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    continue

        return None

    def _build_context_summary(self, context: dict) -> str:
        """
        将客户上下文格式化为易读的摘要文本。

        Args:
            context: 客户上下文

        Returns:
            str: 格式化后的摘要
        """
        lines = []
        mapping = {
            "company": "公司",
            "industry": "行业",
            "target_country": "目标国家",
            "monthly_volume": "月交易量（USD）",
            "current_channel": "当前收款渠道",
            "pain_points": "痛点",
            "battlefield": "战场类型",
        }
        for key, label in mapping.items():
            val = context.get(key)
            if val is not None:
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val)
                lines.append(f"- {label}：{val}")
        return "\n".join(lines)

    def _wrap_json_prompt(self, output_format: dict) -> str:
        """
        包装 JSON 输出要求的提示词后缀。

        Args:
            output_format: 期望的输出格式示例（dict）

        Returns:
            str: JSON 格式要求文本
        """
        return (
            f"\n\n请严格按以下 JSON 格式输出，不要包含其他文字：\n"
            f"```json\n{json.dumps(output_format, ensure_ascii=False, indent=2)}\n```\n"
            f"注意：只输出纯 JSON，不要 markdown 标记外的任何解释文字。"
        )


class AgentRegistry:
    """
    Agent 注册表 — 管理所有 Agent 实例的创建和获取。
    """

    _agents: Dict[str, BaseAgent] = {}

    @classmethod
    def register(cls, name: str, agent_class: type):
        """注册 Agent 类。"""
        cls._agents[name] = agent_class

    @classmethod
    def create(cls, name: str, llm_client, knowledge_loader) -> BaseAgent:
        """
        创建 Agent 实例。

        Args:
            name: Agent 名称
            llm_client: LLMClient 实例
            knowledge_loader: KnowledgeLoader 实例

        Returns:
            BaseAgent: Agent 实例
        """
        agent_class = cls._agents.get(name)
        if not agent_class:
            raise ValueError(f"未注册的 Agent: {name}。已注册: {list(cls._agents.keys())}")
        return agent_class(llm_client, knowledge_loader)

    @classmethod
    def list_agents(cls) -> list:
        """返回所有已注册的 Agent 名称。"""
        return list(cls._agents.keys())


# 便捷装饰器：自动注册 Agent
def agent_register(name: str):
    """装饰器：自动将 Agent 类注册到 AgentRegistry。"""
    def decorator(cls):
        cls.agent_name = name
        AgentRegistry.register(name, cls)
        return cls
    return decorator


if __name__ == "__main__":
    print("=" * 60)
    print("BaseAgent 模块测试")
    print("=" * 60)
    print(f"已注册 Agent: {AgentRegistry.list_agents()}")
    print(f"Agent 温度配置: {AGENT_TEMPERATURE}")
