"""
端到端真实 LLM 测试 — 完整作战包生成

测试流程：
1. 客户信息输入 → 2. 战场判断 → 3. 四 Agent 生成 → 4. 作战包输出

使用真实 API 调用（Kimi + Claude），非 Mock。
为了控制成本，使用 sync_sequential 模式（串行执行）。

运行: python3 tests/test_e2e_real_llm.py
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

from services.llm_client import LLMClient
from services.knowledge_loader import KnowledgeLoader
from agents.speech_agent import SpeechAgent
from agents.cost_agent import CostAgent
from agents.proposal_agent import ProposalAgent
from agents.objection_agent import ObjectionAgent
from orchestrator.battle_router import BattleRouter, enrich_context


def main():
    print("=" * 80)
    print("端到端真实 LLM 测试 — 完整作战包生成")
    print("=" * 80)

    # 客户信息
    customer = {
        "company": "深圳外贸工厂",
        "industry": "b2b",
        "target_country": "thailand",
        "monthly_volume": 800000,  # 80万
        "current_channel": "招商银行电汇",
        "pain_points": ["手续费高", "到账慢", "汇率损失大"],
    }

    print(f"\n📋 客户信息:")
    print(f"   公司: {customer['company']}")
    print(f"   行业: {customer['industry']}")
    print(f"   目标国家: {customer['target_country']}")
    print(f"   月流水: ¥{customer['monthly_volume']:,.0f}")
    print(f"   当前渠道: {customer['current_channel']}")
    print(f"   痛点: {', '.join(customer['pain_points'])}")

    # 增强上下文（战场判断）
    enriched = enrich_context(customer)
    print(f"\n⚔️ 战场判断: {enriched['battlefield']}")
    print(f"   标签: {enriched['battlefield_info'].get('label', '')}")

    # 初始化基础设施
    print("\n🔧 初始化基础设施...")
    llm_client = LLMClient()
    knowledge_loader = KnowledgeLoader()
    print("   ✅ LLMClient")
    print("   ✅ KnowledgeLoader")

    # 初始化 Agents
    print("\n🤖 初始化 Agents...")
    speech = SpeechAgent(llm_client, knowledge_loader)
    cost = CostAgent(llm_client, knowledge_loader)
    proposal = ProposalAgent(llm_client, knowledge_loader)
    objection = ObjectionAgent(llm_client, knowledge_loader)
    print("   ✅ SpeechAgent")
    print("   ✅ CostAgent")
    print("   ✅ ProposalAgent")
    print("   ✅ ObjectionAgent")

    # 注册到 BattleRouter
    print("\n🔗 注册到 BattleRouter...")
    router = BattleRouter(llm_client, knowledge_loader)
    router.register_agent("speech", speech)
    router.register_agent("cost", cost)
    router.register_agent("proposal", proposal)
    router.register_agent("objection", objection)
    router.set_context(customer)
    print("   ✅ 全部注册完成")

    # 生成作战包（串行模式，更稳定）
    print("\n" + "=" * 80)
    print("🚀 开始生成作战包（真实 LLM 调用）")
    print("=" * 80)
    print("   阶段1: Speech + Cost + Objection 串行执行")
    print("   阶段2: Proposal（依赖 Cost 输出）")
    print()

    pack = router.route_sync()

    # 输出结果
    print("\n" + "=" * 80)
    print("📦 作战包生成完成")
    print("=" * 80)
    print(f"   执行时间: {pack['metadata']['execution_time_ms']}ms")
    print(f"   战场类型: {pack['metadata']['battlefield']}")
    print(f"   生成时间: {pack['metadata']['generated_at']}")

    # 验证每个 Agent 的输出
    print("\n" + "-" * 80)
    print("📊 输出质量验证")
    print("-" * 80)

    checks = {}

    # --- Speech ---
    speech_out = pack.get("speech", {})
    if "error" in speech_out:
        print(f"\n🎤 SpeechAgent: ❌ 错误 - {speech_out['error']}")
        checks["speech"] = False
    else:
        has_elevator = bool(speech_out.get("elevator_pitch", ""))
        has_full = bool(speech_out.get("full_talk", ""))
        has_wechat = bool(speech_out.get("wechat_followup", ""))
        print(f"\n🎤 SpeechAgent:")
        print(f"   电梯话术: {'✅' if has_elevator else '❌'} ({len(speech_out.get('elevator_pitch', ''))} 字符)")
        print(f"   完整讲解: {'✅' if has_full else '❌'} ({len(speech_out.get('full_talk', ''))} 字符)")
        print(f"   微信跟进: {'✅' if has_wechat else '❌'} ({len(speech_out.get('wechat_followup', ''))} 字符)")
        checks["speech"] = has_elevator and has_full and has_wechat

    # --- Cost ---
    cost_out = pack.get("cost", {})
    if "error" in cost_out:
        print(f"\n💰 CostAgent: ❌ 错误 - {cost_out['error']}")
        checks["cost"] = False
    else:
        has_table = "comparison_table" in cost_out
        has_saving = cost_out.get("annual_saving", 0) > 0
        print(f"\n💰 CostAgent:")
        print(f"   对比表格: {'✅' if has_table else '❌'}")
        print(f"   年节省额: {'✅' if has_saving else '❌'} (¥{cost_out.get('annual_saving', 0):,.0f})")
        if has_table:
            ct = cost_out["comparison_table"]
            curr = ct.get("current", {}).get("total", 0)
            ksh = ct.get("ksher", {}).get("total", 0)
            print(f"   当前渠道成本: ¥{curr:,.0f}")
            print(f"   Ksher 成本: ¥{ksh:,.0f}")
        checks["cost"] = has_table and has_saving

    # --- Proposal ---
    proposal_out = pack.get("proposal", {})
    if "error" in proposal_out:
        print(f"\n📋 ProposalAgent: ❌ 错误 - {proposal_out['error']}")
        checks["proposal"] = False
    else:
        required = ["industry_insight", "pain_diagnosis", "solution",
                   "product_recommendation", "fee_advantage", "compliance",
                   "onboarding_flow", "next_steps"]
        filled = sum(1 for k in required if proposal_out.get(k, ""))
        print(f"\n📋 ProposalAgent:")
        print(f"   章节完整度: {filled}/{len(required)}")
        for k in required:
            v = proposal_out.get(k, "")
            print(f"   - {k}: {'✅' if v else '❌'} ({len(str(v))} 字符)")
        checks["proposal"] = filled == len(required)

    # --- Objection ---
    objection_out = pack.get("objection", {})
    if "error" in objection_out:
        print(f"\n🛡️ ObjectionAgent: ❌ 错误 - {objection_out['error']}")
        checks["objection"] = False
    else:
        top = objection_out.get("top_objections", [])
        has_tips = bool(objection_out.get("battlefield_tips", ""))
        print(f"\n🛡️ ObjectionAgent:")
        print(f"   异议数量: {len(top)}")
        print(f"   战场建议: {'✅' if has_tips else '❌'}")
        for i, obj in enumerate(top[:3], 1):
            print(f"   异议{i}: {obj.get('objection', '')[:40]}...")
        checks["objection"] = len(top) >= 1 and has_tips

    # 总结
    print("\n" + "=" * 80)
    passed = sum(checks.values())
    total = len(checks)
    print(f"验证结果: {passed}/{total} 通过 ({passed*100//total}%)")
    for name, ok in checks.items():
        print(f"   {'✅' if ok else '❌'} {name}")
    print("=" * 80)

    # 保存结果
    result_path = PROJECT_ROOT / "tests" / "e2e_battle_pack_result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)
    print(f"\n💾 作战包已保存: {result_path}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
