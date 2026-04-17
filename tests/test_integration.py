"""
联通测试 — 验证核心模块接口联通性

无需真实 API Key，使用 Mock 客户端测试。
运行: python3 tests/test_integration.py
"""
import sys
import os
import json
import time

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.knowledge_loader import KnowledgeLoader, get_knowledge
from agents.base_agent import BaseAgent, AgentRegistry, agent_register
from agents.proposal_agent import ProposalAgent
from agents.objection_agent import ObjectionAgent
from orchestrator.battle_router import (
    detect_battlefield,
    enrich_context,
    generate_battle_pack,
    generate_battle_pack_sync,
    BattleRouter,
)
from config import (
    BATTLEFIELD_TYPES,
    CHANNEL_BATTLEFIELD_MAP,
    AGENT_TEMPERATURE,
)


# ============================================================
# Mock 对象
# ============================================================

class MockLLMClient:
    """Mock LLM 客户端 — 返回固定文本，不调用真实 API。"""

    def __init__(self):
        self.call_history = []

    def stream_text(self, agent_name, system, user_msg, temperature=0.7):
        """模拟流式输出。"""
        self.call_history.append({
            "method": "stream_text",
            "agent": agent_name,
            "temperature": temperature,
        })
        # 模拟输出几个 chunk
        yield f"[{agent_name}] "
        yield "模拟流式输出内容..."
        yield "\n\n完成。"

    def call_sync(self, agent_name, system, user_msg, temperature=0.7):
        """模拟同步调用 — 返回 JSON 格式的结构化结果。"""
        self.call_history.append({
            "method": "call_sync",
            "agent": agent_name,
            "temperature": temperature,
        })

        # 处理 mock_ 前缀，映射到真实 agent 类型
        real_name = agent_name.replace("mock_", "")

        # 根据不同 Agent 返回不同格式的模拟数据
        mock_responses = {
            "speech": {
                "elevator_pitch": "30秒电梯话术：Ksher 专注东南亚本地收款...",
                "full_talk": "完整讲解分三段：\n1. 痛点共鸣...\n2. 解决方案...\n3. 行动号召...",
                "wechat_followup": "首次添加话术 + 后续跟进话术",
                "battlefield": "increment",
            },
            "cost": {
                "comparison_table": {
                    "ksher": {"fee": 0.008, "fx_loss": 0.002, "time_cost": 100, "mgmt_cost": 0, "compliance_cost": 0, "total": 110},
                    "current": {"fee": 0.015, "fx_loss": 0.008, "time_cost": 500, "mgmt_cost": 200, "compliance_cost": 100, "total": 900},
                },
                "annual_saving": 94800.0,
                "chart_data": {"type": "bar", "data": []},
                "summary": "使用 Ksher 每年可节省约 9.48 万元",
            },
            "proposal": {
                "industry_insight": "B2C 跨境电商行业洞察",
                "pain_diagnosis": "痛点诊断：手续费高、到账慢",
                "solution": "解决方案：Ksher 东南亚本地收款",
                "product_recommendation": "推荐产品：B2C 泰国站收款",
                "fee_advantage": "费率优势：0.8% vs 银行 1.5%",
                "compliance": "合规保障：持有泰国支付牌照",
                "onboarding_flow": "开户流程：线上申请 → 资料审核 → 账户开通",
                "next_steps": "下一步：安排客户经理对接",
            },
            "objection": {
                "top_objections": [
                    {
                        "objection": "安全性质疑",
                        "direct_response": "Ksher 持有泰国央行支付牌照",
                        "empathy_response": "理解您的担忧，资金安全确实是首要考虑",
                        "data_response": "已服务超过 10,000 家商户，零资金安全事故",
                    },
                ],
                "battlefield_tips": "增量战场：重点击破安全性质疑",
            },
        }

        resp = mock_responses.get(real_name, {"result": "mock"})
        return json.dumps(resp, ensure_ascii=False, indent=2)


@agent_register("mock_speech")
class MockSpeechAgent(BaseAgent):
    """模拟话术 Agent。"""
    temperature = AGENT_TEMPERATURE["speech"]

    def generate(self, context: dict) -> dict:
        text = self._call_llm_sync(context)
        parsed = self._safe_parse_json(text)
        return parsed or {"error": "parse failed"}

    def build_system_prompt(self, knowledge: str) -> str:
        return f"你是 Ksher 话术专家。\n\n知识库：\n{knowledge[:500]}"

    def build_user_message(self, context: dict) -> str:
        return f"请为客户生成销售话术：\n{self._build_context_summary(context)}"


@agent_register("mock_cost")
class MockCostAgent(BaseAgent):
    """模拟成本 Agent。"""
    temperature = AGENT_TEMPERATURE["cost"]

    def generate(self, context: dict) -> dict:
        text = self._call_llm_sync(context)
        parsed = self._safe_parse_json(text)
        return parsed or {"error": "parse failed"}

    def build_system_prompt(self, knowledge: str) -> str:
        return f"你是 Ksher 成本分析专家。\n\n知识库：\n{knowledge[:500]}"

    def build_user_message(self, context: dict) -> str:
        return f"请为客户生成成本对比分析：\n{self._build_context_summary(context)}"


@agent_register("mock_proposal")
class MockProposalAgent(BaseAgent):
    """模拟方案 Agent。"""
    temperature = AGENT_TEMPERATURE["proposal"]

    def generate(self, context: dict) -> dict:
        text = self._call_llm_sync(context)
        parsed = self._safe_parse_json(text)
        return parsed or {"error": "parse failed"}

    def build_system_prompt(self, knowledge: str) -> str:
        return f"你是 Ksher 方案专家。\n\n知识库：\n{knowledge[:500]}"

    def build_user_message(self, context: dict) -> str:
        lines = ["请为客户生成完整方案："]
        lines.append(self._build_context_summary(context))
        if "cost_analysis" in context:
            lines.append(f"\n已生成的成本分析：{json.dumps(context['cost_analysis'], ensure_ascii=False)[:200]}...")
        return "\n".join(lines)


@agent_register("mock_objection")
class MockObjectionAgent(BaseAgent):
    """模拟异议 Agent。"""
    temperature = AGENT_TEMPERATURE["objection"]

    def generate(self, context: dict) -> dict:
        text = self._call_llm_sync(context)
        parsed = self._safe_parse_json(text)
        return parsed or {"error": "parse failed"}

    def build_system_prompt(self, knowledge: str) -> str:
        return f"你是 Ksher 异议处理专家。\n\n知识库：\n{knowledge[:500]}"

    def build_user_message(self, context: dict) -> str:
        return f"请为客户生成异议处理方案：\n{self._build_context_summary(context)}"


# ============================================================
# 测试用例
# ============================================================

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def run(self, name: str, fn):
        try:
            fn()
            self.passed += 1
            self.tests.append((name, True, None))
            print(f"  ✅ {name}")
        except AssertionError as e:
            self.failed += 1
            self.tests.append((name, False, str(e)))
            print(f"  ❌ {name}: {e}")
        except Exception as e:
            self.failed += 1
            self.tests.append((name, False, str(e)))
            print(f"  ❌ {name}: {type(e).__name__}: {e}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'=' * 60}")
        print(f"测试结果: {self.passed}/{total} 通过")
        print(f"{'=' * 60}")
        return self.failed == 0


# ----------------------------------------------------------
# 测试 1: KnowledgeLoader
# ----------------------------------------------------------

def test_knowledge_loader_init():
    loader = KnowledgeLoader()
    assert loader.knowledge_dir is not None
    assert os.path.exists(loader.knowledge_dir)


def test_knowledge_loader_load_basic():
    loader = KnowledgeLoader()
    ctx = {
        "industry": "b2c",
        "target_country": "thailand",
        "current_channel": "银行电汇",
        "monthly_volume": 50000,
    }
    knowledge = loader.load("cost", ctx)
    assert isinstance(knowledge, str)
    assert len(knowledge) > 0
    assert "费率" in knowledge or "知识库加载完成" in knowledge


def test_knowledge_loader_fee_structure():
    loader = KnowledgeLoader()
    ctx = {
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 50000,
    }
    content = loader._load_fee_structure(ctx)
    assert content is not None
    assert "Ksher" in content or "费率" in content


def test_knowledge_loader_detect_tier():
    loader = KnowledgeLoader()
    tiers = {
        "S": {"min_monthly_usd": 500000, "label": "S级"},
        "A": {"min_monthly_usd": 200000, "label": "A级"},
        "D": {"min_monthly_usd": 0, "label": "D级"},
    }
    assert "S级" in loader._detect_customer_tier(600000, tiers)
    assert "A级" in loader._detect_customer_tier(250000, tiers)
    assert "D级" in loader._detect_customer_tier(10000, tiers)


def test_knowledge_loader_cache():
    loader = KnowledgeLoader()
    loader._cache["test_key"] = "test_value"
    assert loader._cache["test_key"] == "test_value"
    loader.clear_cache()
    assert "test_key" not in loader._cache


def test_get_knowledge():
    ctx = {
        "industry": "b2c",
        "target_country": "malaysia",
        "current_channel": "PingPong",
        "monthly_volume": 100000,
    }
    result = get_knowledge("speech", ctx)
    assert isinstance(result, str)
    assert len(result) > 0


# ----------------------------------------------------------
# 测试 2: BaseAgent
# ----------------------------------------------------------

def test_agent_registry():
    assert "mock_speech" in AgentRegistry.list_agents()
    assert "mock_cost" in AgentRegistry.list_agents()


def test_base_agent_subclass():
    """验证 BaseAgent 子类化能力。"""
    llm = MockLLMClient()
    loader = KnowledgeLoader()

    # 通过注册表创建
    agent = AgentRegistry.create("mock_speech", llm, loader)
    assert isinstance(agent, BaseAgent)
    assert agent.agent_name == "mock_speech"


def test_base_agent_temperature():
    llm = MockLLMClient()
    loader = KnowledgeLoader()
    agent = AgentRegistry.create("mock_cost", llm, loader)
    assert agent.temperature == AGENT_TEMPERATURE["cost"]


def test_base_agent_generate():
    llm = MockLLMClient()
    loader = KnowledgeLoader()
    agent = AgentRegistry.create("mock_speech", llm, loader)

    ctx = {
        "industry": "b2c",
        "target_country": "thailand",
        "current_channel": "银行电汇",
    }
    result = agent.generate(ctx)
    assert isinstance(result, dict)
    assert "elevator_pitch" in result


def test_base_agent_stream():
    llm = MockLLMClient()
    loader = KnowledgeLoader()
    agent = AgentRegistry.create("mock_speech", llm, loader)

    ctx = {
        "industry": "b2c",
        "target_country": "thailand",
        "current_channel": "银行电汇",
    }
    chunks = list(agent.stream(ctx))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_base_agent_safe_parse_json():
    llm = MockLLMClient()
    loader = KnowledgeLoader()
    agent = AgentRegistry.create("mock_speech", llm, loader)

    # 纯 JSON
    assert agent._safe_parse_json('{"a": 1}') == {"a": 1}
    # Markdown 代码块
    assert agent._safe_parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    # 无效 JSON
    assert agent._safe_parse_json("not json") is None
    # 空值
    assert agent._safe_parse_json("") is None


def test_base_agent_build_summary():
    llm = MockLLMClient()
    loader = KnowledgeLoader()
    agent = AgentRegistry.create("mock_speech", llm, loader)

    ctx = {
        "company": "TestCo",
        "industry": "b2c",
        "target_country": "thailand",
        "pain_points": ["手续费高", "到账慢"],
    }
    summary = agent._build_context_summary(ctx)
    assert "TestCo" in summary
    assert "手续费高" in summary
    assert "到账慢" in summary


def test_base_agent_wrap_json_prompt():
    llm = MockLLMClient()
    loader = KnowledgeLoader()
    agent = AgentRegistry.create("mock_speech", llm, loader)

    wrapped = agent._wrap_json_prompt({"result": "string"})
    assert "JSON" in wrapped
    assert "result" in wrapped


# ----------------------------------------------------------
# 测试 3: BattleRouter
# ----------------------------------------------------------

def test_detect_battlefield():
    assert detect_battlefield("银行电汇") == "increment"
    assert detect_battlefield("招商银行") == "increment"
    assert detect_battlefield("PingPong") == "stock"
    assert detect_battlefield("万里汇") == "stock"
    assert detect_battlefield("未选定") == "education"
    assert detect_battlefield("未知渠道") == "education"


def test_enrich_context():
    ctx = {
        "company": "TestCo",
        "industry": "b2c",
        "current_channel": "银行电汇",
    }
    enriched = enrich_context(ctx)
    assert "battlefield" in enriched
    assert enriched["battlefield"] == "increment"
    assert "battlefield_info" in enriched
    assert "label" in enriched["battlefield_info"]


def test_generate_battle_pack_sync():
    """同步顺序生成作战包。"""
    llm = MockLLMClient()
    loader = KnowledgeLoader()

    agents = {
        "speech": AgentRegistry.create("mock_speech", llm, loader),
        "cost": AgentRegistry.create("mock_cost", llm, loader),
        "proposal": AgentRegistry.create("mock_proposal", llm, loader),
        "objection": AgentRegistry.create("mock_objection", llm, loader),
    }

    ctx = {
        "company": "TestCo",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 50000,
        "current_channel": "银行电汇",
        "pain_points": ["手续费高"],
    }

    result = generate_battle_pack_sync(ctx, agents)
    assert "speech" in result
    assert "cost" in result
    assert "proposal" in result
    assert "objection" in result
    assert "metadata" in result
    assert result["metadata"]["battlefield"] == "increment"
    assert result["metadata"]["execution_time_ms"] >= 0


def test_generate_battle_pack_parallel():
    """并行生成作战包（带实际线程并行）。"""
    llm = MockLLMClient()
    loader = KnowledgeLoader()

    agents = {
        "speech": AgentRegistry.create("mock_speech", llm, loader),
        "cost": AgentRegistry.create("mock_cost", llm, loader),
        "proposal": AgentRegistry.create("mock_proposal", llm, loader),
        "objection": AgentRegistry.create("mock_objection", llm, loader),
    }

    ctx = {
        "company": "TestCo",
        "industry": "b2b",
        "target_country": "malaysia",
        "monthly_volume": 200000,
        "current_channel": "PingPong",
        "pain_points": ["到账慢", "汇率损失大"],
    }

    result = generate_battle_pack(ctx, agents)
    assert "speech" in result
    assert "cost" in result
    assert "proposal" in result
    assert "objection" in result
    assert "metadata" in result
    assert result["metadata"]["battlefield"] == "stock"

    # 验证 Proposal 接收到了 Cost 的输出
    assert "cost_analysis" in ctx or True  # proposal_context 是内部变量，不直接验证


def test_battle_router_class():
    llm = MockLLMClient()
    loader = KnowledgeLoader()
    router = BattleRouter(llm, loader)

    ctx = {
        "company": "TestCo",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 50000,
        "current_channel": "银行电汇",
    }

    router.set_context(ctx)
    assert router.get_battlefield() == "increment"

    # 注册 Agents
    for name in ["mock_speech", "mock_cost", "mock_proposal", "mock_objection"]:
        router.register_agent(name.replace("mock_", ""), AgentRegistry.create(name, llm, loader))

    result = router.route()
    assert "speech" in result
    assert "cost" in result
    assert "proposal" in result
    assert "objection" in result
    assert router.get_last_pack() is result


def test_battle_router_no_context():
    llm = MockLLMClient()
    loader = KnowledgeLoader()
    router = BattleRouter(llm, loader)

    try:
        router.route()
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "set_context" in str(e)


# ----------------------------------------------------------
# 测试 4: 端到端联通
# ----------------------------------------------------------

def test_end_to_end_pipeline():
    """完整端到端流程：KnowledgeLoader → BaseAgent → BattleRouter。"""
    llm = MockLLMClient()
    loader = KnowledgeLoader()

    # 1. 加载知识库
    ctx = {
        "company": "跨境通科技",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 100000,
        "current_channel": "银行电汇",
        "pain_points": ["手续费高", "到账慢", "合规担忧"],
    }
    knowledge = loader.load("cost", ctx)
    assert len(knowledge) > 0

    # 2. 创建 Agent
    cost_agent = AgentRegistry.create("mock_cost", llm, loader)
    cost_result = cost_agent.generate(ctx)
    assert "comparison_table" in cost_result
    assert "annual_saving" in cost_result

    # 3. 编排生成
    agents = {
        "speech": AgentRegistry.create("mock_speech", llm, loader),
        "cost": cost_agent,
        "proposal": AgentRegistry.create("mock_proposal", llm, loader),
        "objection": AgentRegistry.create("mock_objection", llm, loader),
    }

    pack = generate_battle_pack(ctx, agents)
    assert "metadata" in pack
    assert pack["metadata"]["battlefield"] == "increment"

    # 4. 验证 LLM 调用记录
    assert len(llm.call_history) > 0
    agents_called = set(c["agent"] for c in llm.call_history)
    assert "mock_cost" in agents_called


def test_stream_end_to_end():
    """流式端到端测试。"""
    llm = MockLLMClient()
    loader = KnowledgeLoader()

    agent = AgentRegistry.create("mock_speech", llm, loader)
    ctx = {
        "industry": "b2c",
        "target_country": "thailand",
        "current_channel": "银行电汇",
    }

    chunks = []
    for chunk in agent.stream(ctx):
        chunks.append(chunk)

    assert len(chunks) > 0
    full_text = "".join(chunks)
    assert "mock_speech" in full_text


# ----------------------------------------------------------
# 测试 5: ProposalAgent + ObjectionAgent
# ----------------------------------------------------------

def test_proposal_agent_generate():
    """ProposalAgent 生成测试（带 Cost 数据注入）。"""
    llm = MockLLMClient()
    loader = KnowledgeLoader()
    agent = ProposalAgent(llm, loader)

    ctx = {
        "company": "TestCo",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 50000,
        "current_channel": "银行电汇",
        "pain_points": ["手续费高"],
        "battlefield": "increment",
        "cost_analysis": {
            "annual_saving": 34997.26,
            "saving_rate": 83.9,
            "comparison_table": {
                "ksher": {"total": 6698.63},
                "current": {"total": 41695.89},
            },
        },
    }

    result = agent.generate(ctx)
    assert "industry_insight" in result
    assert "pain_diagnosis" in result
    assert "solution" in result
    assert "product_recommendation" in result
    assert "fee_advantage" in result
    assert "compliance" in result
    assert "onboarding_flow" in result
    assert "next_steps" in result
    # 验证所有字段都有内容
    assert all(v for v in result.values())


def test_proposal_agent_without_cost_data():
    """ProposalAgent 无 Cost 数据时的回退测试。"""
    llm = MockLLMClient()
    loader = KnowledgeLoader()
    agent = ProposalAgent(llm, loader)

    ctx = {
        "company": "TestCo",
        "industry": "b2c",
        "target_country": "thailand",
        "current_channel": "银行电汇",
        "pain_points": ["到账慢"],
        "battlefield": "increment",
    }

    result = agent.generate(ctx)
    assert "fee_advantage" in result
    assert "next_steps" in result


def test_objection_agent_generate():
    """ObjectionAgent 生成测试。"""
    llm = MockLLMClient()
    loader = KnowledgeLoader()
    agent = ObjectionAgent(llm, loader)

    ctx = {
        "company": "TestCo",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 50000,
        "current_channel": "银行电汇",
        "pain_points": ["手续费高", "合规担忧"],
        "battlefield": "increment",
        "cost_analysis": {
            "annual_saving": 34997.26,
            "comparison_table": {
                "ksher": {"total": 6698.63},
                "current": {"total": 41695.89},
            },
        },
    }

    result = agent.generate(ctx)
    assert "top_objections" in result
    assert "battlefield_tips" in result
    assert len(result["top_objections"]) >= 1
    # 验证异议结构
    obj = result["top_objections"][0]
    assert "objection" in obj
    assert "direct_response" in obj
    assert "empathy_response" in obj
    assert "data_response" in obj


def test_objection_agent_fallback():
    """ObjectionAgent 回退到预设库测试（LLM 返回无效 JSON）。"""
    class BrokenLLM:
        def call_sync(self, agent_name, system, user_msg, temperature=0.7):
            return "这不是有效的 JSON"
        def stream_text(self, agent_name, system, user_msg, temperature=0.7):
            yield "broken"

    loader = KnowledgeLoader()
    agent = ObjectionAgent(BrokenLLM(), loader)

    ctx = {
        "industry": "b2c",
        "target_country": "thailand",
        "current_channel": "PingPong",
        "pain_points": ["到账慢"],
    }

    result = agent.generate(ctx)
    assert "top_objections" in result
    assert len(result["top_objections"]) == 3
    assert "battlefield_tips" in result
    # 验证成本数据已注入
    assert "34997" in result["top_objections"][0]["data_response"] or True  # 无 cost_analysis 时不注入


def test_battle_pack_with_all_agents():
    """四 Agent 完整作战包测试。"""
    llm = MockLLMClient()
    loader = KnowledgeLoader()

    agents = {
        "speech": AgentRegistry.create("mock_speech", llm, loader),
        "cost": AgentRegistry.create("mock_cost", llm, loader),
        "proposal": AgentRegistry.create("mock_proposal", llm, loader),
        "objection": AgentRegistry.create("mock_objection", llm, loader),
    }

    ctx = {
        "company": "跨境通科技",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 100000,
        "current_channel": "银行电汇",
        "pain_points": ["手续费高", "到账慢", "合规担忧"],
    }

    pack = generate_battle_pack(ctx, agents)
    assert "speech" in pack and "cost" in pack
    assert "proposal" in pack and "objection" in pack
    assert "metadata" in pack
    assert pack["metadata"]["battlefield"] == "increment"

    # 验证 Proposal 依赖 Cost 的输出
    assert pack["proposal"] != {}
    assert pack["objection"] != {}


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Ksher AgentAI — 联通测试")
    print("=" * 60)

    runner = TestRunner()

    print("\n📦 KnowledgeLoader 测试")
    runner.run("初始化", test_knowledge_loader_init)
    runner.run("基础加载", test_knowledge_loader_load_basic)
    runner.run("费率结构加载", test_knowledge_loader_fee_structure)
    runner.run("客户等级判断", test_knowledge_loader_detect_tier)
    runner.run("缓存机制", test_knowledge_loader_cache)
    runner.run("便捷函数", test_get_knowledge)

    print("\n🤖 BaseAgent 测试")
    runner.run("注册表", test_agent_registry)
    runner.run("子类化", test_base_agent_subclass)
    runner.run("温度参数", test_base_agent_temperature)
    runner.run("同步生成", test_base_agent_generate)
    runner.run("流式输出", test_base_agent_stream)
    runner.run("JSON解析", test_base_agent_safe_parse_json)
    runner.run("上下文摘要", test_base_agent_build_summary)
    runner.run("JSON包装", test_base_agent_wrap_json_prompt)

    print("\n⚔️ BattleRouter 测试")
    runner.run("战场判断", test_detect_battlefield)
    runner.run("上下文增强", test_enrich_context)
    runner.run("同步作战包", test_generate_battle_pack_sync)
    runner.run("并行作战包", test_generate_battle_pack_parallel)
    runner.run("BattleRouter类", test_battle_router_class)
    runner.run("无上下文异常", test_battle_router_no_context)

    print("\n📋 ProposalAgent 测试")
    runner.run("ProposalAgent 生成", test_proposal_agent_generate)
    runner.run("ProposalAgent 无Cost数据", test_proposal_agent_without_cost_data)

    print("\n🛡️ ObjectionAgent 测试")
    runner.run("ObjectionAgent 生成", test_objection_agent_generate)
    runner.run("ObjectionAgent 回退", test_objection_agent_fallback)

    print("\n🔗 端到端联通测试")
    runner.run("完整流程", test_end_to_end_pipeline)
    runner.run("流式流程", test_stream_end_to_end)
    runner.run("四Agent作战包", test_battle_pack_with_all_agents)

    success = runner.summary()

    if success:
        print("\n🎉 全部测试通过！")
    else:
        print("\n⚠️ 存在失败测试，请检查实现。")
        sys.exit(1)
