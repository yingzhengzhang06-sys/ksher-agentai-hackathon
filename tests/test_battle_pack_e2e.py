"""
完整作战包端到端测试 — 使用真实 Agent 运行全流程

此测试验证：
1. 所有 4 个 Agent 能正确实例化
2. BattleRouter 能编排完整流程
3. 输出符合 INTERFACES.md 格式

注意：CostAgent 的 CostCalculator 部分不依赖 LLM，
但 Speech/Proposal/Objection Agent 需要 LLM 调用。
使用 MockLLM 模拟 LLM 响应，确保测试可独立运行。
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.knowledge_loader import KnowledgeLoader
from services.cost_calculator import calculate_comparison
from agents.speech_agent import SpeechAgent
from agents.cost_agent import CostAgent
from agents.proposal_agent import ProposalAgent
from agents.objection_agent import ObjectionAgent
from orchestrator.battle_router import BattleRouter, enrich_context


class MockLLMClient:
    """Mock LLM — 返回结构化 JSON，模拟真实 LLM 输出"""

    def __init__(self):
        self.call_history = []

    def stream_text(self, agent_name, system, user_msg, temperature=0.7):
        self.call_history.append({"agent": agent_name, "method": "stream"})
        yield f"[{agent_name}] 模拟流式输出..."

    def call_sync(self, agent_name, system, user_msg, temperature=0.7):
        self.call_history.append({"agent": agent_name, "method": "sync", "temp": temperature})

        # 模拟各 Agent 的 JSON 输出
        responses = {
            "speech": {
                "elevator_pitch": "很多跨境商家以为银行最安全，但银行隐性成本高——汇率差、到账慢、每笔固定手续费。Ksher 是专注东南亚的本地收款平台，费率更低、到账更快，而且持有当地央行支付牌照。",
                "full_talk": "【第1分钟·切痛点】您现在用银行电汇收款，每个月除了明面上的手续费，还有汇率损失和资金占用成本。银行 T+3 到账，意味着资金有3天被锁住。\n\n【第2分钟·给方案】Ksher 是 T+1 到账，费率比银行低将近一半。我们有泰国央行支付牌照，资金安全有保障。\n\n【第3分钟·促行动】我可以帮您算一笔具体的账，看看一年能省多少。您方便的话，我们约个 15 分钟线上会议？",
                "wechat_followup": "【首次添加】XX总您好，我是 Ksher 代理商小王。刚才聊到的跨境收款成本问题，我整理了一份对比表，您有空可以看看。\n\n【后续跟进】XX总，上次提到的银行隐性成本，我帮您算了一下——按您现在的月流水，一年大概能多花不少。用 Ksher 可以省下来。",
                "battlefield": "increment",
            },
            "cost": {
                "comparison_table": {
                    "ksher": {"fee": 4800, "fx_loss": 1200, "time_cost": 98.63, "mgmt_cost": 0, "compliance_cost": 600, "total": 6698.63},
                    "current": {"fee": 34200, "fx_loss": 4800, "time_cost": 295.89, "mgmt_cost": 600, "compliance_cost": 1800, "total": 41695.89},
                },
                "annual_saving": 34997.26,
                "chart_data": {"type": "bar", "data": []},
                "summary": "根据您的月流水 $50,000 USD，我们为您算了笔账：使用银行电汇收款，一年下来的隐性成本远超预期。切换到 Ksher，年省 ¥34,997（节省 83.9%），相当于每月多赚 ¥2,916。这笔钱本来可以是您的利润。",
            },
            "proposal": {
                "industry_insight": "B2C 跨境电商正处于东南亚爆发期。泰国电商市场年增长率超过 15%，但跨境收款环节存在成本高、到账慢、合规风险等核心挑战。",
                "pain_diagnosis": "使用银行电汇收款，客户面临三大痛点：1）手续费 1.5% + 每笔固定费，显性成本高；2）T+3 到账，资金周转效率低；3）汇率差 0.8%，汇兑损失大。",
                "solution": "Ksher 提供东南亚本地收款解决方案：T+1 快速到账释放资金占用；透明费率 0.8% 降低综合成本；本地牌照保障合规安全；一站式管理多平台资金。",
                "product_recommendation": "针对泰国市场，推荐开通 Ksher 泰国本地收款账户（THB）。直接收取泰铢，避免美元中转的双重汇兑损失。支持 Shopee/Lazada/独立站等多平台收款。",
                "fee_advantage": "切换到 Ksher，年省 ¥34,997（节省 83.9%）。Ksher 年度总成本仅 ¥6,699，而银行电汇高达 ¥41,696。费率透明无隐藏成本，汇率优于银行零售牌价。",
                "compliance": "Ksher 持有泰国央行（Bank of Thailand）颁发的支付牌照，资金本地清算不经过第三方中转。合规链路完整，监管透明，为客户提供银行级别的资金安全保障。",
                "onboarding_flow": "1. 线上提交开户申请（10分钟）→ 2. 资料审核（1-2个工作日）→ 3. 账户开通 → 4. 平台绑定/技术对接 → 5. 开始收款。全程客户经理一对一服务。",
                "next_steps": "建议安排 30 分钟线上沟通，详细了解您的业务需求后，为您定制最优收款方案。我可以先帮您算一笔精确的账。",
            },
            "objection": {
                "top_objections": [
                    {
                        "objection": "没听过 Ksher，安全吗？",
                        "direct_response": "Ksher 持有泰国、马来西亚、印尼等多国央行支付牌照，资金安全由当地监管直接保障，和银行同一级别的合规标准。",
                        "empathy_response": "您的谨慎非常专业，选择收款渠道确实需要审慎。Ksher 在东南亚运营多年，服务超过万家商户，资金安全零事故。",
                        "data_response": "Ksher 持有泰国央行颁发的支付牌照，资金本地清算不经过第三方中转，每一笔交易都可追溯。",
                    },
                    {
                        "objection": "换渠道太麻烦，现在用的银行也挺好的",
                        "direct_response": "切换确实需要时间，但 Ksher 提供专人对接服务，从开户到上线通常只需 3-5 个工作日，不影响正常收款。",
                        "empathy_response": "完全理解，稳定的收款渠道对业务很重要。不过很多客户反馈，切换后第一个月就感受到了明显的成本下降。",
                        "data_response": "按您的月流水计算，继续使用银行每年多花 ¥34,997。Ksher 切换成本几乎为零，收益从第一个月开始体现。",
                    },
                    {
                        "objection": "费率看起来差不多，为什么要换？",
                        "direct_response": "表面费率相近，但隐性成本差异很大：银行 T+3 到账产生资金占用成本，汇率差通常比 Ksher 高 0.5% 以上。",
                        "empathy_response": "很多客户一开始也有同样感受。但如果把汇率损失、资金占用、管理成本都算上，总成本差距会很明显。",
                        "data_response": "综合计算：银行手续费 1.5% + 汇差 0.8% + T+3 资金占用，实际年化成本 ¥41,696。Ksher 仅 ¥6,699。",
                    },
                ],
                "battlefield_tips": "本次拜访核心策略：先算隐性成本账，让客户意识到'便宜'的银行其实不便宜，再给出 Ksher 的降维打击方案。重点击破'安全质疑'和'嫌麻烦'两大异议。",
            },
        }

        resp = responses.get(agent_name, {"result": "mock"})
        return json.dumps(resp, ensure_ascii=False, indent=2)


def print_section(title, content, width=70):
    """美化打印章节"""
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")
    if isinstance(content, dict):
        for k, v in content.items():
            if isinstance(v, list):
                print(f"\n📌 {k}:")
                for i, item in enumerate(v, 1):
                    if isinstance(item, dict):
                        print(f"  [{i}]")
                        for kk, vv in item.items():
                            print(f"    {kk}: {vv}")
                    else:
                        print(f"  [{i}] {item}")
            elif isinstance(v, dict):
                print(f"\n📌 {k}:")
                for kk, vv in v.items():
                    if isinstance(vv, dict):
                        print(f"  {kk}:")
                        for kkk, vvv in vv.items():
                            print(f"    {kkk}: {vvv}")
                    else:
                        print(f"  {kk}: {vv}")
            else:
                print(f"\n📌 {k}:")
                print(f"  {v}")
    else:
        print(content)


def run_full_battle_pack_test():
    """运行完整作战包端到端测试"""
    print("=" * 70)
    print("  Ksher AgentAI — 完整作战包端到端测试")
    print("=" * 70)

    # ── 客户画像 ──
    customer = {
        "company": "跨境通科技",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 50000,
        "current_channel": "银行电汇",
        "pain_points": ["手续费高", "到账慢", "合规担忧"],
    }

    print(f"\n📋 客户画像:")
    for k, v in customer.items():
        print(f"  {k}: {v}")

    # ── 初始化 ──
    llm = MockLLMClient()
    loader = KnowledgeLoader()

    # ── 成本计算（纯 Python，不依赖 LLM）──
    print(f"\n{'─' * 70}")
    print("  Step 0: CostCalculator 精确计算（纯 Python）")
    print(f"{'─' * 70}")
    calc_result = calculate_comparison(
        industry=customer["industry"],
        target_country=customer["target_country"],
        monthly_volume=customer["monthly_volume"],
        current_channel=customer["current_channel"],
    )
    print(f"  Ksher 年度成本:    ¥{calc_result['ksher'].total:>12,.2f}")
    print(f"  当前渠道年度成本:  ¥{calc_result['current'].total:>12,.2f}")
    print(f"  💰 年度节省:       ¥{calc_result['annual_saving']:>12,.2f} ({calc_result['saving_rate']}%)")

    # ── 创建 Router ──
    router = BattleRouter(llm, loader)
    router.set_context(customer)

    # 注册 4 个真实 Agent
    router.register_agent("speech", SpeechAgent(llm, loader))
    router.register_agent("cost", CostAgent(llm, loader))
    router.register_agent("proposal", ProposalAgent(llm, loader))
    router.register_agent("objection", ObjectionAgent(llm, loader))

    print(f"\n  已注册 Agent: speech, cost, proposal, objection")
    print(f"  战场类型: {router.get_battlefield()}")

    # ── 执行作战包生成 ──
    print(f"\n{'─' * 70}")
    print("  Step 1-4: BattleRouter 执行两阶段编排")
    print(f"{'─' * 70}")
    print("  阶段1（并行）: SpeechAgent + CostAgent + ObjectionAgent")
    print("  阶段2（串行）: ProposalAgent（依赖 CostAgent 输出）")

    pack = router.route()

    print(f"\n  ✅ 执行完成！耗时: {pack['metadata']['execution_time_ms']}ms")

    # ── 验证输出格式 ──
    print(f"\n{'─' * 70}")
    print("  输出格式验证")
    print(f"{'─' * 70}")

    validations = []

    # Speech
    speech = pack.get("speech", {})
    speech_ok = all(k in speech for k in ["elevator_pitch", "full_talk", "wechat_followup", "battlefield"])
    validations.append(("SpeechAgent", speech_ok, "elevator_pitch/full_talk/wechat_followup/battlefield"))

    # Cost
    cost = pack.get("cost", {})
    cost_ok = all(k in cost for k in ["comparison_table", "annual_saving", "chart_data", "summary"])
    validations.append(("CostAgent", cost_ok, "comparison_table/annual_saving/chart_data/summary"))

    # Proposal
    proposal = pack.get("proposal", {})
    proposal_ok = all(k in proposal for k in ["industry_insight", "pain_diagnosis", "solution",
                                                "product_recommendation", "fee_advantage",
                                                "compliance", "onboarding_flow", "next_steps"])
    validations.append(("ProposalAgent", proposal_ok, "8 chapters"))

    # Objection
    objection = pack.get("objection", {})
    obj_ok = "top_objections" in objection and "battlefield_tips" in objection
    if obj_ok and objection["top_objections"]:
        first = objection["top_objections"][0]
        obj_ok = all(k in first for k in ["objection", "direct_response", "empathy_response", "data_response"])
    validations.append(("ObjectionAgent", obj_ok, "top_objections[3]/battlefield_tips"))

    for name, ok, fields in validations:
        status = "✅" if ok else "❌"
        print(f"  {status} {name:15} | {fields}")

    all_ok = all(ok for _, ok, _ in validations)

    # ── 打印详细输出 ──
    print(f"\n{'─' * 70}")
    print("  详细输出")
    print(f"{'─' * 70}")

    print_section("🎤 SpeechAgent — 销售话术", speech)
    print_section("💰 CostAgent — 成本分析", {
        "annual_saving": f"¥{cost.get('annual_saving', 0):,.2f}",
        "monthly_saving": f"¥{cost.get('monthly_saving', 0):,.2f}",
        "saving_rate": f"{cost.get('saving_rate', 0)}%",
        "summary": cost.get("summary", ""),
        "comparison_table": cost.get("comparison_table", {}),
    })
    print_section("📋 ProposalAgent — 解决方案", proposal)
    print_section("🛡️ ObjectionAgent — 异议处理", objection)

    # ── 总结 ──
    print(f"\n{'=' * 70}")
    if all_ok:
        print("  ✅ 全部通过！作战包生成成功。")
    else:
        print("  ❌ 部分验证失败，请检查输出格式。")
    print(f"{'=' * 70}")

    return all_ok, pack


if __name__ == "__main__":
    success, pack = run_full_battle_pack_test()
    sys.exit(0 if success else 1)
