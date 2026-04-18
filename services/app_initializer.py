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
from orchestrator.battle_router import BattleRouter


def initialize_battle_router() -> BattleRouter:
    """
    初始化并返回配置好的 BattleRouter 实例。

    流程：
        1. 创建 LLMClient（双模型路由：Kimi + Claude）
        2. 创建 KnowledgeLoader（选择性知识库加载）
        3. 创建 BattleRouter
        4. 注册 4 个核心 Agent（Speech / Cost / Proposal / Objection）

    Returns:
        BattleRouter: 可直接使用的战场路由器实例
    """
    llm_client = LLMClient()
    knowledge_loader = KnowledgeLoader()

    router = BattleRouter(llm_client, knowledge_loader)

    # 注册 4 个核心 Agent
    router.register_agent("speech", SpeechAgent(llm_client, knowledge_loader))
    router.register_agent("cost", CostAgent(llm_client, knowledge_loader))
    router.register_agent("proposal", ProposalAgent(llm_client, knowledge_loader))
    router.register_agent("objection", ObjectionAgent(llm_client, knowledge_loader))

    return router


def try_initialize_battle_router() -> tuple[bool, str]:
    """
    尝试初始化 BattleRouter，返回 (是否成功, 错误信息)。

    用于 app.py 启动时安全初始化，失败时返回友好错误信息。
    """
    try:
        router = initialize_battle_router()
        return True, ""
    except Exception as e:
        return False, str(e)
