"""
App启动初始化 — 实例化所有Agent并注册到BattleRouter

在 app.py 启动时调用，将配置好的 BattleRouter 存入 session_state。
"""
import sys
import os
import streamlit as st

# 确保项目根目录在路径中（适配 Streamlit 运行环境）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm_client import LLMClient
from services.knowledge_loader import KnowledgeLoader
from agents.speech_agent import SpeechAgent
from agents.cost_agent import CostAgent
from agents.proposal_agent import ProposalAgent
from agents.objection_agent import ObjectionAgent
from agents.content_agent import ContentAgent
from agents.knowledge_agent import KnowledgeAgent
from orchestrator.battle_router import BattleRouter


def initialize_all_agents() -> dict:
    """
    初始化所有核心组件和 Agent，返回包含全部实例的字典。

    流程：
        1. 创建 LLMClient（双模型路由：Kimi + Claude）
        2. 创建 KnowledgeLoader（选择性知识库加载）
        3. 创建 BattleRouter 并注册 4 个核心 Agent
        4. 创建独立 Agent（ContentAgent / KnowledgeAgent）供其他页面使用

    Returns:
        dict: 包含以下键值：
            - battle_router: BattleRouter 实例
            - llm_client: LLMClient 实例
            - knowledge_loader: KnowledgeLoader 实例
            - content_agent: ContentAgent 实例
            - knowledge_agent: KnowledgeAgent 实例
            - objection_agent: ObjectionAgent 实例
    """
    llm_client = LLMClient()
    knowledge_loader = KnowledgeLoader()

    router = BattleRouter(llm_client, knowledge_loader)

    # 注册 4 个核心 Agent
    router.register_agent("speech", SpeechAgent(llm_client, knowledge_loader))
    router.register_agent("cost", CostAgent(llm_client, knowledge_loader))
    router.register_agent("proposal", ProposalAgent(llm_client, knowledge_loader))

    objection_agent = ObjectionAgent(llm_client, knowledge_loader)
    router.register_agent("objection", objection_agent)

    # 创建独立 Agent 供其他页面使用
    content_agent = ContentAgent(llm_client, knowledge_loader)
    knowledge_agent = KnowledgeAgent(llm_client, knowledge_loader)

    return {
        "battle_router": router,
        "llm_client": llm_client,
        "knowledge_loader": knowledge_loader,
        "content_agent": content_agent,
        "knowledge_agent": knowledge_agent,
        "objection_agent": objection_agent,
    }


def initialize_battle_router() -> BattleRouter:
    """
    初始化并返回配置好的 BattleRouter 实例。

    保留向后兼容：内部调用 initialize_all_agents()，仅返回 BattleRouter。

    Returns:
        BattleRouter: 可直接使用的战场路由器实例
    """
    agents = initialize_all_agents()
    return agents["battle_router"]


def try_initialize_battle_router() -> tuple[bool, str | dict]:
    """
    尝试初始化所有 Agent，返回 (是否成功, 错误信息或全部实例字典)。

    成功时返回 (True, dict)，dict 包含 battle_router / llm_client /
    knowledge_loader / content_agent / knowledge_agent / objection_agent。
    失败时返回 (False, 错误信息字符串)。
    """
    try:
        agents = initialize_all_agents()
        return True, agents
    except Exception as e:
        return False, str(e)


# ──────────────────────────────────────────────────────────────
# 便捷查询：按名称获取已初始化的 Agent 实例
# ──────────────────────────────────────────────────────────────
_AGENT_CACHE: dict = {}


def get_agent_by_name(agent_name: str):
    """
    按 agent_name 获取已初始化的 Agent 实例。

    仅支持注册到 AgentRegistry 的核心 Agent，
    其他 Agent（如 pipeline_* 系列）需通过 pipeline_agent.py 使用。

    Args:
        agent_name: Agent 名称，如 "speech", "cost", "proposal", "objection",
                   "content", "knowledge", "design"

    Returns:
        Agent 实例，或 None（未注册时）
    """
    global _AGENT_CACHE
    if not _AGENT_CACHE:
        all_agents = initialize_all_agents()
        _AGENT_CACHE = {
            "speech":     all_agents["battle_router"]._agents.get("speech"),
            "cost":       all_agents["battle_router"]._agents.get("cost"),
            "proposal":   all_agents["battle_router"]._agents.get("proposal"),
            "objection":  all_agents["battle_router"]._agents.get("objection"),
            "content":    all_agents["content_agent"],
            "knowledge":  all_agents["knowledge_agent"],
            "design":     None,  # DesignAgent 需单独实例化
        }
    return _AGENT_CACHE.get(agent_name)
