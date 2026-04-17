"""
战场路由 + 作战包编排器

两阶段半并行执行：
  阶段1：Speech + Cost + Objection 并行（3个Agent互不依赖）
  阶段2：Proposal 串行（依赖Cost的输出）
"""
import concurrent.futures
import time
from typing import Dict, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CHANNEL_BATTLEFIELD_MAP, BATTLEFIELD_TYPES


def detect_battlefield(current_channel: str) -> str:
    """
    根据客户当前收款渠道判断战场类型。

    Args:
        current_channel: 客户当前使用的收款渠道

    Returns:
        str: 战场类型 — "increment" | "stock" | "education"
    """
    battlefield = CHANNEL_BATTLEFIELD_MAP.get(current_channel)
    if battlefield:
        return battlefield

    # 模糊匹配
    channel_lower = current_channel.lower()
    for key, bf in CHANNEL_BATTLEFIELD_MAP.items():
        if key.lower() in channel_lower or channel_lower in key.lower():
            return bf

    # 默认教育战场
    return "education"


def enrich_context(context: dict) -> dict:
    """
    增强客户上下文：自动判断战场类型并注入策略指引。

    Args:
        context: 原始客户上下文

    Returns:
        dict: 增强后的上下文（添加 battlefield 和 battlefield_info）
    """
    enriched = dict(context)
    current_channel = enriched.get("current_channel", "")

    # 判断战场类型
    battlefield = detect_battlefield(current_channel)
    enriched["battlefield"] = battlefield
    enriched["battlefield_info"] = BATTLEFIELD_TYPES.get(battlefield, {})

    return enriched


def generate_battle_pack(context: dict, agents: dict) -> dict:
    """
    生成作战包 — 两阶段半并行执行。

    阶段1（并行）：SpeechAgent + CostAgent + ObjectionAgent
    阶段2（串行）：ProposalAgent（依赖 CostAgent 的输出）

    Args:
        context: 客户画像 + 战场判断结果（需先经过 enrich_context 处理）
        agents: {
            "speech": SpeechAgent 实例,
            "cost": CostAgent 实例,
            "proposal": ProposalAgent 实例,
            "objection": ObjectionAgent 实例,
        }

    Returns:
        dict: {
            "speech": {...},
            "cost": {...},
            "proposal": {...},
            "objection": {...},
            "metadata": {
                "generated_at": timestamp,
                "battlefield": str,
                "execution_time_ms": int,
            }
        }
    """
    start_time = time.time()

    # 确保上下文已增强
    if "battlefield" not in context:
        context = enrich_context(context)

    battlefield = context["battlefield"]
    result = {
        "speech": {},
        "cost": {},
        "proposal": {},
        "objection": {},
        "metadata": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "battlefield": battlefield,
            "battlefield_label": BATTLEFIELD_TYPES.get(battlefield, {}).get("label", ""),
            "execution_time_ms": 0,
        }
    }

    # ==================== 阶段1：并行执行 ====================
    phase1_agents = {}
    if "speech" in agents:
        phase1_agents["speech"] = agents["speech"]
    if "cost" in agents:
        phase1_agents["cost"] = agents["cost"]
    if "objection" in agents:
        phase1_agents["objection"] = agents["objection"]

    def run_agent(name: str, agent):
        """运行单个 Agent，返回 (name, result)。"""
        try:
            output = agent.generate(context)
            return name, output
        except Exception as e:
            return name, {"error": str(e), "_agent": name}

    # 使用线程池并行执行
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(run_agent, name, agent): name
            for name, agent in phase1_agents.items()
        }
        for future in concurrent.futures.as_completed(futures):
            name, output = future.result()
            result[name] = output

    # ==================== 阶段2：串行执行（依赖 Cost）====================
    if "proposal" in agents:
        proposal_agent = agents["proposal"]
        # 将 CostAgent 的输出注入 Proposal 的上下文
        proposal_context = dict(context)
        proposal_context["cost_analysis"] = result.get("cost", {})
        proposal_context["speech_output"] = result.get("speech", {})
        proposal_context["objection_output"] = result.get("objection", {})

        try:
            result["proposal"] = proposal_agent.generate(proposal_context)
        except Exception as e:
            result["proposal"] = {"error": str(e), "_agent": "proposal"}

    # 计算执行时间
    elapsed_ms = int((time.time() - start_time) * 1000)
    result["metadata"]["execution_time_ms"] = elapsed_ms

    return result


def generate_battle_pack_sync(context: dict, agents: dict) -> dict:
    """
    同步顺序生成作战包（无并行，用于调试或资源受限环境）。

    执行顺序：Speech → Cost → Objection → Proposal
    """
    start_time = time.time()

    if "battlefield" not in context:
        context = enrich_context(context)

    battlefield = context["battlefield"]
    result = {
        "speech": {},
        "cost": {},
        "proposal": {},
        "objection": {},
        "metadata": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "battlefield": battlefield,
            "battlefield_label": BATTLEFIELD_TYPES.get(battlefield, {}).get("label", ""),
            "execution_time_ms": 0,
            "mode": "sync_sequential",
        }
    }

    # 顺序执行
    for name in ["speech", "cost", "objection"]:
        if name in agents:
            try:
                result[name] = agents[name].generate(context)
            except Exception as e:
                result[name] = {"error": str(e), "_agent": name}

    # Proposal（依赖前面结果）
    if "proposal" in agents:
        proposal_context = dict(context)
        proposal_context["cost_analysis"] = result.get("cost", {})
        proposal_context["speech_output"] = result.get("speech", {})
        proposal_context["objection_output"] = result.get("objection", {})
        try:
            result["proposal"] = agents["proposal"].generate(proposal_context)
        except Exception as e:
            result["proposal"] = {"error": str(e), "_agent": "proposal"}

    elapsed_ms = int((time.time() - start_time) * 1000)
    result["metadata"]["execution_time_ms"] = elapsed_ms

    return result


def generate_streaming_battle_pack(context: dict, agents: dict, on_chunk=None):
    """
    流式生成作战包 — 逐 Agent 流式输出。

    用于实时向 UI 推送每个 Agent 的生成进度。

    Args:
        context: 客户上下文
        agents: Agent 字典
        on_chunk: 回调函数 (agent_name, chunk) -> None

    Yields:
        dict: {"agent": str, "status": str, "chunk": str}
    """
    if "battlefield" not in context:
        context = enrich_context(context)

    # 阶段1：流式生成 Speech
    if "speech" in agents:
        yield {"agent": "speech", "status": "streaming", "chunk": ""}
        chunks = []
        for chunk in agents["speech"].stream(context):
            chunks.append(chunk)
            if on_chunk:
                on_chunk("speech", chunk)
            yield {"agent": "speech", "status": "chunk", "chunk": chunk}
        yield {"agent": "speech", "status": "complete", "chunk": ""}

    # 阶段1：Cost（同步，因为需要结构化数据）
    if "cost" in agents:
        yield {"agent": "cost", "status": "generating", "chunk": ""}
        try:
            cost_result = agents["cost"].generate(context)
            yield {"agent": "cost", "status": "complete", "data": cost_result}
        except Exception as e:
            yield {"agent": "cost", "status": "error", "error": str(e)}

    # 阶段1：流式生成 Objection
    if "objection" in agents:
        yield {"agent": "objection", "status": "streaming", "chunk": ""}
        for chunk in agents["objection"].stream(context):
            if on_chunk:
                on_chunk("objection", chunk)
            yield {"agent": "objection", "status": "chunk", "chunk": chunk}
        yield {"agent": "objection", "status": "complete", "chunk": ""}

    # 阶段2：Proposal（串行，依赖 Cost）
    if "proposal" in agents:
        yield {"agent": "proposal", "status": "generating", "chunk": ""}
        proposal_context = dict(context)
        # 前面可能已生成 cost，这里需要注入
        try:
            proposal_result = agents["proposal"].generate(proposal_context)
            yield {"agent": "proposal", "status": "complete", "data": proposal_result}
        except Exception as e:
            yield {"agent": "proposal", "status": "error", "error": str(e)}


class BattleRouter:
    """
    战场路由器 — 面向对象封装，维护 Agent 实例和上下文状态。
    """

    def __init__(self, llm_client, knowledge_loader):
        """
        Args:
            llm_client: LLMClient 实例
            knowledge_loader: KnowledgeLoader 实例
        """
        self.llm_client = llm_client
        self.knowledge_loader = knowledge_loader
        self._agents: Dict[str, any] = {}
        self._context: Optional[dict] = None
        self._last_pack: Optional[dict] = None

    def register_agent(self, name: str, agent):
        """注册 Agent 实例。"""
        self._agents[name] = agent

    def set_context(self, context: dict):
        """设置客户上下文。"""
        self._context = enrich_context(context)

    def route(self) -> dict:
        """
        执行完整作战包生成。

        Returns:
            dict: 作战包结果
        """
        if not self._context:
            raise ValueError("请先调用 set_context() 设置客户上下文")
        if not self._agents:
            raise ValueError("请先注册至少一个 Agent")

        self._last_pack = generate_battle_pack(self._context, self._agents)
        return self._last_pack

    def route_sync(self) -> dict:
        """同步顺序执行（无并行）。"""
        if not self._context:
            raise ValueError("请先调用 set_context() 设置客户上下文")

        self._last_pack = generate_battle_pack_sync(self._context, self._agents)
        return self._last_pack

    def get_battlefield(self) -> str:
        """获取当前战场类型。"""
        if not self._context:
            return "education"
        return self._context.get("battlefield", "education")

    def get_last_pack(self) -> Optional[dict]:
        """获取上一次生成的作战包。"""
        return self._last_pack

    def get_agent(self, name: str):
        """获取指定 Agent 实例。"""
        return self._agents.get(name)


if __name__ == "__main__":
    print("=" * 60)
    print("BattleRouter 模块测试")
    print("=" * 60)

    # 测试战场判断
    test_channels = [
        "银行电汇",
        "招商银行",
        "PingPong",
        "万里汇",
        "XTransfer",
        "未选定",
        "未知渠道",
    ]
    print("\n战场类型判断测试：")
    for ch in test_channels:
        bf = detect_battlefield(ch)
        label = BATTLEFIELD_TYPES.get(bf, {}).get("label", bf)
        print(f"  {ch:12} → {bf:10} ({label})")

    # 测试上下文增强
    print("\n上下文增强测试：")
    ctx = {
        "company": "TestCo",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 50000,
        "current_channel": "银行电汇",
        "pain_points": ["手续费高", "到账慢"],
    }
    enriched = enrich_context(ctx)
    print(f"  原始渠道：{ctx['current_channel']}")
    print(f"  战场类型：{enriched['battlefield']}")
    print(f"  战场标签：{enriched['battlefield_info'].get('label')}")

    print("\n✅ BattleRouter 模块测试完成")
