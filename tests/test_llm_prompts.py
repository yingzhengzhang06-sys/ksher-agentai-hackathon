"""
LLM Prompt 真实数据测试

测试两个 Agent 的 Prompt 在真实场景下的输出效果：
1. SpeechAgent（Kimi K2.5）— 增量战场话术生成
2. CostAgent（Claude Sonnet 4.6）— 成本对比计算

测试场景：深圳外贸工厂，月流水80万，招商银行电汇，做泰国B2B
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 先加载环境变量（override=True 覆盖 shell 中可能存在的旧值）
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

from services.llm_client import LLMClient
from prompts.knowledge_fusion_rules import KNOWLEDGE_FUSION_RULES
from prompts.speech_prompt import SPEECH_AGENT_PROMPT, BATTLEFIELD_SPEECH_CONFIG
from prompts.cost_prompt import COST_AGENT_PROMPT, CHANNEL_FEE_REFERENCE


def load_knowledge_text() -> str:
    """从知识库加载真实数据，作为第一层知识注入"""
    # 读取费率数据
    with open(PROJECT_ROOT / "knowledge" / "fee_structure.json", "r", encoding="utf-8") as f:
        fee_data = json.load(f)

    # 读取泰国产品卡片
    with open(PROJECT_ROOT / "knowledge" / "b2c" / "b2c_thailand.md", "r", encoding="utf-8") as f:
        thailand_md = f.read()

    # 读取竞品对比
    with open(PROJECT_ROOT / "knowledge" / "competitors" / "bank_wire.md", "r", encoding="utf-8") as f:
        bank_md = f.read()

    # 组装知识文本
    knowledge_text = f"""
=== Ksher 费率数据（来自 fee_structure.json）===
B2C 泰国: 标准费率 {fee_data['ksher']['b2c']['countries']['thailand']['fee_rate']*100}%, 汇率基准: {fee_data['ksher']['b2c']['countries']['thailand']['fx_benchmark']}, 到账: T+{fee_data['ksher']['b2c']['countries']['thailand']['settlement_days']}
B2B 泰国: 标准费率 {fee_data['ksher']['b2b']['countries']['thailand']['fee_rate']*100}%, 到账: T+{fee_data['ksher']['b2b']['countries']['thailand']['settlement_days']}

银行电汇: 固定费 {fee_data['bank']['wire_transfer']['fee_fixed_per_transaction']}元/笔, 费率 {fee_data['bank']['wire_transfer']['fee_rate']*100}%, 汇率点差 {fee_data['bank']['wire_transfer']['fx_spread']*100}%, 到账 T+{fee_data['bank']['wire_transfer']['settlement_days']}

竞品对比:
- PingPong: B2C {fee_data['competitors']['pingpong']['b2c_fee_rate']*100}%, B2B {fee_data['competitors']['pingpong']['b2b_fee_rate']*100}%, 汇率点差 {fee_data['competitors']['pingpong']['fx_spread']*100}%, 到账 T+{fee_data['competitors']['pingpong']['settlement_days']}
- 万里汇: B2C {fee_data['competitors']['worldfirst']['b2c_fee_rate']*100}%, B2B {fee_data['competitors']['worldfirst']['b2b_fee_rate']*100}%, 汇率点差 {fee_data['competitors']['worldfirst']['fx_spread']*100}%, 到账 T+{fee_data['competitors']['worldfirst']['settlement_days']}
- XTransfer: B2C {fee_data['competitors']['xtransfer']['b2c_fee_rate']*100}%, B2B {fee_data['competitors']['xtransfer']['b2b_fee_rate']*100}%, 汇率点差 {fee_data['competitors']['xtransfer']['fx_spread']*100}%, 到账 T+{fee_data['competitors']['xtransfer']['settlement_days']}

=== 泰国产品卡片 ===
{thailand_md[:1000]}

=== 银行电汇竞品分析 ===
{bank_md[:1000]}
"""
    return knowledge_text.strip()


def test_speech_agent():
    """测试 SpeechAgent — 增量战场话术生成"""
    print("=" * 80)
    print("测试 SpeechAgent（Kimi K2.5 — 创意型）")
    print("场景：深圳外贸工厂，月流水80万，招商银行电汇，泰国B2B")
    print("战场：增量（从银行抢客户）")
    print("=" * 80)

    client = LLMClient()

    # 准备知识文本
    knowledge_text = load_knowledge_text()

    # 填充 Prompt
    system_prompt = SPEECH_AGENT_PROMPT.format(
        KNOWLEDGE_FUSION_RULES=KNOWLEDGE_FUSION_RULES.format(knowledge_text=knowledge_text),
        battlefield_type="increment",
        industry="跨境货贸（B2B）",
        current_channel="招商银行电汇",
        target_country="泰国",
        pain_points="手续费高、到账慢、汇率损失大",
        monthly_volume="80",
    )

    user_msg = "请为这位客户生成完整的销售话术包。"

    print(f"\n[Prompt 长度: {len(system_prompt)} 字符]")
    print("\n--- 开始调用 Kimi K2.5 ---\n")

    response = client.call_sync(
        agent_name="speech",
        system=system_prompt,
        user_msg=user_msg,
        temperature=1.0,
    )

    print(response)
    print(f"\n[输出长度: {len(response)} 字符]")
    return response


def test_cost_agent():
    """测试 CostAgent — 成本对比计算"""
    print("\n" + "=" * 80)
    print("测试 CostAgent（Claude Sonnet 4.6 — 精准型）")
    print("场景：深圳外贸工厂，月流水80万，招商银行电汇，泰国B2B")
    print("战场：增量（从银行抢客户）")
    print("=" * 80)

    client = LLMClient()

    # 准备费率数据 JSON
    with open(PROJECT_ROOT / "knowledge" / "fee_structure.json", "r", encoding="utf-8") as f:
        fee_data = json.load(f)

    fee_json = json.dumps({
        "current_channel": {
            "name": "银行电汇（招商银行）",
            "fee_rate": fee_data["bank"]["wire_transfer"]["fee_rate"],
            "fee_fixed_per_transaction": fee_data["bank"]["wire_transfer"]["fee_fixed_per_transaction"],
            "fx_spread": fee_data["bank"]["wire_transfer"]["fx_spread"],
            "settlement_days": fee_data["bank"]["wire_transfer"]["settlement_days"],
        },
        "ksher": {
            "name": "Ksher B2B 泰国",
            "fee_rate": fee_data["ksher"]["b2b"]["countries"]["thailand"]["fee_rate"],
            "fx_spread": 0.003,
            "settlement_days": fee_data["ksher"]["b2b"]["countries"]["thailand"]["settlement_days"],
        },
    }, ensure_ascii=False, indent=2)

    knowledge_text = load_knowledge_text()

    # 填充 Prompt
    system_prompt = COST_AGENT_PROMPT.format(
        KNOWLEDGE_FUSION_RULES=KNOWLEDGE_FUSION_RULES.format(knowledge_text=knowledge_text),
        battlefield_type="increment",
        monthly_volume="80",
        current_channel="招商银行电汇",
        target_country="泰国",
        industry="跨境货贸（B2B）",
        transaction_count="10",
        fee_data_json=fee_json,
        annual_saving="XX",
        monthly_saving="XX",
    )

    user_msg = "请计算这位客户切换到 Ksher 的年度成本节省，并生成代理商可以直接使用的解读话术。"

    print(f"\n[Prompt 长度: {len(system_prompt)} 字符]")
    print("\n--- 开始调用 Claude Sonnet 4.6 ---\n")

    response = client.call_sync(
        agent_name="cost",
        system=system_prompt,
        user_msg=user_msg,
        temperature=0.3,
    )

    print(response)
    print(f"\n[输出长度: {len(response)} 字符]")
    return response


def evaluate_output(speech_output: str, cost_output: str):
    """评估输出质量"""
    print("\n" + "=" * 80)
    print("输出质量评估")
    print("=" * 80)

    checks = {
        "SpeechAgent — 30秒电梯话术": "30 秒电梯话术" in speech_output or "电梯话术" in speech_output,
        "SpeechAgent — 3分钟完整讲解": "3 分钟" in speech_output or "完整讲解" in speech_output,
        "SpeechAgent — 微信跟进话术": "微信" in speech_output,
        "SpeechAgent — 含具体数据": "%" in speech_output or "万" in speech_output,
        "SpeechAgent — 有CTA/促行动": any(w in speech_output for w in ["下一步", "联系", "试试", "了解"]),
        "CostAgent — 成本对比表格": "|" in cost_output and "成本" in cost_output,
        "CostAgent — 核心结论": "年省" in cost_output or "节省" in cost_output,
        "CostAgent — 对客户说的话": "对客户" in cost_output or "一句话" in cost_output,
        "CostAgent — 含具体数字": any(w in cost_output for w in ["¥", "元", "万"]),
        "CostAgent — 隐性成本分析": "隐性" in cost_output,
    }

    passed = 0
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
        if result:
            passed += 1

    print(f"\n通过: {passed}/{len(checks)} ({passed*100//len(checks)}%)")


def main():
    print("\n" + "🧪 " * 20)
    print("LLM Prompt 真实数据测试")
    print("🧪 " * 20 + "\n")

    try:
        # 测试 1: SpeechAgent
        speech_output = test_speech_agent()

        # 测试 2: CostAgent
        cost_output = test_cost_agent()

        # 评估
        evaluate_output(speech_output, cost_output)

        # 保存结果
        result_path = PROJECT_ROOT / "tests" / "llm_test_results.md"
        with open(result_path, "w", encoding="utf-8") as f:
            f.write("# LLM Prompt 真实数据测试结果\n\n")
            f.write("## 测试配置\n\n")
            f.write("- SpeechAgent: Kimi K2.5, temperature=0.7\n")
            f.write("- CostAgent: Claude Sonnet 4.6, temperature=0.3\n")
            f.write("- 场景: 深圳外贸工厂，月流水80万，招商银行电汇，泰国B2B\n")
            f.write("- 战场: 增量（从银行抢客户）\n\n")
            f.write("---\n\n")
            f.write("## SpeechAgent 输出\n\n")
            f.write(speech_output)
            f.write("\n\n---\n\n")
            f.write("## CostAgent 输出\n\n")
            f.write(cost_output)

        print(f"\n结果已保存: {result_path}")
        return 0

    except Exception as e:
        print(f"\n💥 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
