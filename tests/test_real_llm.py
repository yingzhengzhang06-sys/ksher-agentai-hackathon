"""
真实 LLM 端到端测试 — 调用 Kimi + Claude 双模型

⚠️ 此测试消耗真实 API token。运行前确保 .env 文件已配置。

运行：python3 tests/test_real_llm.py
"""
import os
import sys
import json
import time

# 加载 .env 文件中的 API key（覆盖 shell 环境变量）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(override=True)

from services.llm_client import LLMClient
from services.knowledge_loader import KnowledgeLoader
from services.cost_calculator import calculate_comparison
from agents.speech_agent import SpeechAgent
from agents.cost_agent import CostAgent
from agents.proposal_agent import ProposalAgent
from agents.objection_agent import ObjectionAgent


def print_banner(title, width=70):
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def print_dict(data, indent=2):
    for k, v in data.items():
        prefix = " " * indent
        if isinstance(v, dict):
            print(f"{prefix}{k}:")
            print_dict(v, indent + 2)
        elif isinstance(v, list):
            print(f"{prefix}{k}: [list x{len(v)}]")
        else:
            preview = str(v)[:120]
            if len(str(v)) > 120:
                preview += "..."
            print(f"{prefix}{k}: {preview}")


def test_single_agent(agent, context, name):
    """测试单个 Agent，捕获异常"""
    print_banner(f"🧪 Testing {name}")
    start = time.time()
    try:
        result = agent.generate(context)
        elapsed = time.time() - start
        print(f"  ✅ 成功（{elapsed:.1f}s）")
        print_dict(result)
        return result
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ❌ 失败（{elapsed:.1f}s）: {type(e).__name__}: {e}")
        return None


def main():
    print_banner("Ksher AgentAI — 真实 LLM 端到端测试")

    # 验证 API key
    kimi_key = os.getenv("KIMI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    print(f"\n📡 API 配置:")
    print(f"  Kimi API Key:     {'✅ 已配置' if kimi_key else '❌ 未配置'}")
    print(f"  Anthropic API Key: {'✅ 已配置' if anthropic_key else '❌ 未配置'}")

    if not kimi_key or not anthropic_key:
        print("\n⚠️ API Key 未配置，无法运行真实 LLM 测试。")
        print("   请检查 .env 文件中的 KIMI_API_KEY 和 ANTHROPIC_API_KEY。")
        return 1

    # 初始化
    llm = LLMClient()
    loader = KnowledgeLoader()
    print(f"\n🤖 LLMClient 初始化成功")
    print(f"   speech/objection → Kimi（创意型）")
    print(f"   cost/proposal    → Claude/Sonnet（精准型）")

    # 客户画像
    customer = {
        "company": "跨境通科技",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 50000,
        "current_channel": "银行电汇",
        "pain_points": ["手续费高", "到账慢", "合规担忧"],
        "battlefield": "increment",
    }

    print(f"\n📋 客户画像:")
    print_dict(customer)

    # ── Step 1: CostCalculator（纯 Python，无 LLM）──
    print_banner("💰 Step 1: CostCalculator（纯 Python）")
    calc = calculate_comparison(
        customer["industry"],
        customer["target_country"],
        customer["monthly_volume"],
        customer["current_channel"],
    )
    print(f"  Ksher:  ¥{calc['ksher'].total:,.2f}")
    print(f"  当前:   ¥{calc['current'].total:,.2f}")
    print(f"  节省:   ¥{calc['annual_saving']:,.2f} ({calc['saving_rate']}%)")

    # ── Step 2: 并行测试 Speech + Cost + Objection ──
    print_banner("🎤 Step 2: SpeechAgent（Kimi，创意型）")
    speech_agent = SpeechAgent(llm, loader)
    speech = test_single_agent(speech_agent, customer, "SpeechAgent")

    print_banner("💰 Step 3: CostAgent（Claude，精准型）")
    cost_agent = CostAgent(llm, loader)
    cost = test_single_agent(cost_agent, customer, "CostAgent")

    print_banner("🛡️ Step 4: ObjectionAgent（Kimi，创意型）")
    objection_agent = ObjectionAgent(llm, loader)
    objection = test_single_agent(objection_agent, customer, "ObjectionAgent")

    # ── Step 3: 串行测试 Proposal（依赖 Cost 输出）──
    print_banner("📋 Step 5: ProposalAgent（Claude，精准型）")
    proposal_context = dict(customer)
    if cost:
        proposal_context["cost_analysis"] = {
            "annual_saving": cost.get("annual_saving", 0),
            "saving_rate": cost.get("saving_rate", 0),
            "comparison_table": cost.get("comparison_table", {}),
        }
    proposal_agent = ProposalAgent(llm, loader)
    proposal = test_single_agent(proposal_agent, proposal_context, "ProposalAgent")

    # ── 总结 ──
    print_banner("📊 测试总结")
    results = {
        "SpeechAgent": speech is not None,
        "CostAgent": cost is not None,
        "ObjectionAgent": objection is not None,
        "ProposalAgent": proposal is not None,
    }
    for name, ok in results.items():
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"  {status} | {name}")

    passed = sum(results.values())
    total = len(results)
    print(f"\n  总计: {passed}/{total} 通过")

    # 保存原始输出供审查
    output_file = "/Users/macbookm4/Desktop/黑客松参赛项目/tests/llm_output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "customer": customer,
            "cost_calculator": {
                "annual_saving": calc["annual_saving"],
                "saving_rate": calc["saving_rate"],
            },
            "speech": speech,
            "cost": cost,
            "proposal": proposal,
            "objection": objection,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  📝 原始输出已保存: {output_file}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
