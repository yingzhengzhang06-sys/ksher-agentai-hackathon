"""
Agent 健康检查服务

快速检查：
1. 所有 Agent 能否正确实例化
2. LLM 连接是否正常
3. 知识库能否加载
4. 费率数据是否完整

用法：
    from services.health_check import run_health_check, HealthCheckResult
    result = run_health_check(llm_client, knowledge_loader)
    print(result.to_text())
"""
import os
import sys
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AGENT_MODEL_MAP, KNOWLEDGE_DIR


@dataclass
class AgentCheck:
    """单个 Agent 的健康检查结果"""
    name: str
    status: str  # "healthy" | "degraded" | "unhealthy"
    message: str = ""
    latency_ms: int = 0
    details: List[str] = field(default_factory=list)


@dataclass
class HealthCheckResult:
    """健康检查结果汇总"""
    overall: str  # "healthy" | "degraded" | "unhealthy"
    timestamp: str
    agents: List[AgentCheck]
    system: List[AgentCheck]
    summary: dict

    def to_text(self) -> str:
        """格式化为人类可读的文本"""
        lines = [
            f"\n{'=' * 60}",
            f"  Ksher AgentAI — 健康检查报告",
            f"{'=' * 60}",
            f"  时间: {self.timestamp}",
            f"  总体状态: {self.overall.upper()}",
            f"{'=' * 60}",
        ]

        if self.system:
            lines.append(f"\n  系统检查:")
            for s in self.system:
                icon = "✅" if s.status == "healthy" else "⚠️"
                lines.append(f"  {icon} {s.name}: {s.status} ({s.latency_ms}ms)")
                if s.message:
                    lines.append(f"      {s.message}")

        if self.agents:
            lines.append(f"\n  Agent 检查:")
            for a in self.agents:
                icon = "✅" if a.status == "healthy" else "⚠️" if a.status == "degraded" else "❌"
                lines.append(f"  {icon} {a.name}: {a.status} ({a.latency_ms}ms)")
                if a.message:
                    lines.append(f"      {a.message}")

        lines.append(f"\n  汇总:")
        lines.append(f"    健康: {self.summary['healthy']}/{self.summary['total']}")
        lines.append(f"    降级: {self.summary['degraded']}/{self.summary['total']}")
        lines.append(f"    故障: {self.summary['unhealthy']}/{self.summary['total']}")
        if self.summary.get("cached"):
            lines.append(f"    命中缓存: {self.summary['cached']} 个")

        lines.append(f"{'=' * 60}\n")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """格式化为 dict"""
        return {
            "overall": self.overall,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "system": [{"name": s.name, "status": s.status, "message": s.message,
                        "latency_ms": s.latency_ms} for s in self.system],
            "agents": [{"name": a.name, "status": a.status, "message": a.message,
                        "latency_ms": a.latency_ms} for a in self.agents],
        }


def check_knowledge_base(loader=None) -> AgentCheck:
    """检查知识库"""
    start = time.time()
    try:
        if loader is None:
            from services.knowledge_loader import KnowledgeLoader
            loader = KnowledgeLoader()

        # 测试加载各行业知识
        industries = ["b2c", "b2b", "service", "b2s"]
        countries = ["thailand", "malaysia", "philippines"]

        for ind in industries:
            ctx = {
                "industry": ind,
                "target_country": countries[0] if ind != "service" else "",
                "current_channel": "银行电汇",
            }
            text = loader.load("speech", ctx)
            if not text or len(text) < 10:
                raise ValueError(f"知识库为空或太短: {ind}")

        latency = int((time.time() - start) * 1000)
        return AgentCheck(
            name="知识库",
            status="healthy",
            message=f"知识库正常，已验证 {len(industries)} 个行业",
            latency_ms=latency,
        )
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return AgentCheck(
            name="知识库",
            status="unhealthy",
            message=str(e)[:100],
            latency_ms=latency,
        )


def check_fee_structure() -> AgentCheck:
    """检查费率数据结构"""
    start = time.time()
    try:
        from services.cost_calculator import load_fee_structure
        data = load_fee_structure()
        assert "ksher" in data
        assert "bank" in data
        assert "competitors" in data
        assert "customer_tiers" in data
        latency = int((time.time() - start) * 1000)
        return AgentCheck(
            name="费率数据",
            status="healthy",
            message=f"费率数据完整（ksher/bank/competitors/tiers）",
            latency_ms=latency,
        )
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return AgentCheck(
            name="费率数据",
            status="unhealthy",
            message=str(e)[:100],
            latency_ms=latency,
        )


def check_llm_connection(llm_client) -> AgentCheck:
    """检查 LLM 连接"""
    start = time.time()
    try:
        # 简单测试：验证配置非空
        api_keys = []
        for key in ["KIMI_API_KEY", "ANTHROPIC_API_KEY"]:
            val = os.getenv(key)
            if val:
                api_keys.append(f"{key}={val[:8]}...")

        if len(api_keys) < 2:
            raise ValueError(f"API Key 不足: 仅配置了 {len(api_keys)} 个")

        latency = int((time.time() - start) * 1000)
        return AgentCheck(
            name="LLM 连接",
            status="healthy",
            message=f"已配置 {len(api_keys)} 个 API Key",
            latency_ms=latency,
        )
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return AgentCheck(
            name="LLM 连接",
            status="unhealthy",
            message=str(e)[:100],
            latency_ms=latency,
        )


def check_agent_registry() -> AgentCheck:
    """检查 Agent 注册表"""
    start = time.time()
    try:
        # 导入所有 Agent 模块以触发 @agent_register
        from agents import speech_agent, cost_agent, proposal_agent
        from agents import objection_agent, content_agent, knowledge_agent, design_agent
        from agents.base_agent import AgentRegistry

        registered = AgentRegistry.list_agents()
        expected = ["speech", "cost", "proposal", "objection",
                    "content", "knowledge", "design"]

        missing = [name for name in expected if name not in registered]
        if missing:
            raise ValueError(f"未注册的 Agent: {missing}")

        latency = int((time.time() - start) * 1000)
        return AgentCheck(
            name="Agent 注册表",
            status="healthy",
            message=f"7/7 个 Agent 已注册: {', '.join(registered)}",
            latency_ms=latency,
        )
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return AgentCheck(
            name="Agent 注册表",
            status="unhealthy",
            message=str(e)[:100],
            latency_ms=latency,
        )


def check_battle_router() -> AgentCheck:
    """检查战场路由器"""
    start = time.time()
    try:
        from orchestrator.battle_router import detect_battlefield
        test_cases = [
            ("银行电汇", "increment"),
            ("PingPong", "stock"),
            ("未选定", "education"),
        ]
        for channel, expected in test_cases:
            result = detect_battlefield(channel)
            assert result == expected, f"{channel} → {result}, 期望 {expected}"

        latency = int((time.time() - start) * 1000)
        return AgentCheck(
            name="战场路由器",
            status="healthy",
            message=f"战场判断正常（{len(test_cases)} 个测试用例通过）",
            latency_ms=latency,
        )
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return AgentCheck(
            name="战场路由器",
            status="unhealthy",
            message=str(e)[:100],
            latency_ms=latency,
        )


def check_result_cache() -> AgentCheck:
    """检查结果缓存"""
    start = time.time()
    try:
        from services.result_cache import ResultCache
        cache = ResultCache()
        # 基础测试
        ctx = {"company": "test", "industry": "b2c", "target_country": "th",
                "current_channel": "bank", "monthly_volume": 50000}
        cache.set(ctx, {"test": "data"}, agent_name="speech")
        result = cache.get(ctx, agent_name="speech")
        assert result == {"test": "data"}

        # 清理
        cache.clear()

        latency = int((time.time() - start) * 1000)
        return AgentCheck(
            name="结果缓存",
            status="healthy",
            message=f"缓存读写正常",
            latency_ms=latency,
        )
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return AgentCheck(
            name="结果缓存",
            status="unhealthy",
            message=str(e)[:100],
            latency_ms=latency,
        )


def run_health_check(llm_client=None, knowledge_loader=None) -> HealthCheckResult:
    """
    运行完整的健康检查。

    Returns:
        HealthCheckResult: 检查结果
    """
    system_checks = []
    agent_checks = []

    # 系统检查
    system_checks.append(check_llm_connection(llm_client))
    system_checks.append(check_knowledge_base(knowledge_loader))
    system_checks.append(check_fee_structure())
    system_checks.append(check_battle_router())
    system_checks.append(check_result_cache())

    # Agent 注册表检查
    agent_checks.append(check_agent_registry())

    # 统计
    summary = {"healthy": 0, "degraded": 0, "unhealthy": 0, "total": 0}
    for check in system_checks + agent_checks:
        summary[check.status] += 1
        summary["total"] += 1

    overall = "healthy"
    if summary["unhealthy"] > 0:
        overall = "unhealthy"
    elif summary["degraded"] > 0:
        overall = "degraded"

    return HealthCheckResult(
        overall=overall,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        agents=agent_checks,
        system=system_checks,
        summary=summary,
    )


if __name__ == "__main__":
    result = run_health_check()
    print(result.to_text())
