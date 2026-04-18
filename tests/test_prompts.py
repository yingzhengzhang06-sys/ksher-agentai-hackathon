"""
test_prompts.py
Prompt 质量验证测试

测试内容：
1. Prompt 模板可正确加载
2. 变量占位符完整
3. 三层知识融合规则注入正常
4. 战场策略适配正确
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from prompts.knowledge_fusion_rules import KNOWLEDGE_FUSION_RULES, AGENT_FUSION_FOCUS
from prompts.speech_prompt import SPEECH_AGENT_PROMPT, BATTLEFIELD_SPEECH_CONFIG
from prompts.cost_prompt import COST_AGENT_PROMPT, CHANNEL_FEE_REFERENCE


def test_knowledge_fusion_rules():
    """测试知识融合规则"""
    print("=" * 60)
    print("测试 1: knowledge_fusion_rules.py")
    print("=" * 60)

    # 检查三层结构
    assert "第一层" in KNOWLEDGE_FUSION_RULES, "缺失第一层"
    assert "第二层" in KNOWLEDGE_FUSION_RULES, "缺失第二层"
    assert "第三层" in KNOWLEDGE_FUSION_RULES, "缺失第三层"
    print("✅ 三层知识优先级体系完整")

    # 检查标注规范
    assert "根据 Ksher 产品资料" in KNOWLEDGE_FUSION_RULES, "缺失 Ksher 标注规范"
    assert "根据行业公开信息" in KNOWLEDGE_FUSION_RULES, "缺失行业标注规范"
    assert "需确认" in KNOWLEDGE_FUSION_RULES, "缺失需确认标注"
    print("✅ 标注规范完整")

    # 检查冲突规则
    assert "以第一层知识库为准" in KNOWLEDGE_FUSION_RULES, "缺失冲突规则"
    print("✅ 冲突规则正确（知识库 > 模型知识）")

    # 检查禁止行为
    assert "❌" in KNOWLEDGE_FUSION_RULES, "缺失禁止行为标记"
    print("✅ 禁止行为列表完整")

    # 检查 AGENT_FUSION_FOCUS
    assert "SpeechAgent" in AGENT_FUSION_FOCUS, "缺失 SpeechAgent"
    assert "CostAgent" in AGENT_FUSION_FOCUS, "缺失 CostAgent"
    print("✅ Agent 融合重点速查表完整")

    print()


def test_speech_prompt():
    """测试 SpeechAgent Prompt"""
    print("=" * 60)
    print("测试 2: speech_prompt.py")
    print("=" * 60)

    # 检查关键占位符
    required_vars = [
        "{KNOWLEDGE_FUSION_RULES}",
        "{battlefield_type}",
        "{industry}",
        "{current_channel}",
        "{target_country}",
        "{pain_points}",
        "{monthly_volume}",
    ]
    for var in required_vars:
        assert var in SPEECH_AGENT_PROMPT, f"缺失变量: {var}"
    print(f"✅ 全部 {len(required_vars)} 个变量占位符完整")

    # 检查战场适配
    assert "增量战场" in SPEECH_AGENT_PROMPT, "缺失增量战场策略"
    assert "存量战场" in SPEECH_AGENT_PROMPT, "缺失存量战场策略"
    assert "教育战场" in SPEECH_AGENT_PROMPT, "缺失教育战场策略"
    print("✅ 三种战场策略适配完整")

    # 检查战场钩子
    assert "帮您全面了解收款的真实成本构成" in SPEECH_AGENT_PROMPT, "缺失增量钩子"
    assert "东南亚市场，Ksher 具备差异化竞争优势" in SPEECH_AGENT_PROMPT, "缺失存量钩子"
    assert "跨境收款有 3 个关键点需要注意" in SPEECH_AGENT_PROMPT, "缺失教育钩子"
    print("✅ 三种战场核心钩子正确")

    # 检查输出格式
    assert "30 秒电梯话术" in SPEECH_AGENT_PROMPT, "缺失电梯话术"
    assert "3 分钟完整讲解" in SPEECH_AGENT_PROMPT, "缺失完整讲解"
    assert "微信跟进话术" in SPEECH_AGENT_PROMPT, "缺失微信话术"
    print("✅ 输出格式完整（电梯/3分钟/微信）")

    # 检查质量检查清单
    assert "质量检查清单" in SPEECH_AGENT_PROMPT, "缺失自检清单"
    print("✅ 质量检查清单存在")

    # 检查战场配置
    assert "increment" in BATTLEFIELD_SPEECH_CONFIG, "缺失 increment 配置"
    assert "stock" in BATTLEFIELD_SPEECH_CONFIG, "缺失 stock 配置"
    assert "education" in BATTLEFIELD_SPEECH_CONFIG, "缺失 education 配置"
    print("✅ 战场配置字典完整")

    # 模拟注入测试
    mock_knowledge = "Ksher 泰国 B2C 费率 0.80%，本地 SCB 账户，T+1 到账"
    filled_prompt = SPEECH_AGENT_PROMPT.format(
        KNOWLEDGE_FUSION_RULES=KNOWLEDGE_FUSION_RULES.format(knowledge_text=mock_knowledge),
        battlefield_type="increment",
        industry="跨境电商（B2C）",
        current_channel="银行电汇",
        target_country="泰国",
        pain_points="手续费高、到账慢",
        monthly_volume="50",
    )
    assert "帮您全面了解收款的真实成本构成" in filled_prompt, "注入后钩子丢失"
    assert "0.80%" in filled_prompt, "注入后知识丢失"
    print("✅ 模拟注入测试通过")
    print(f"   注入后 Prompt 长度: {len(filled_prompt)} 字符")

    print()


def test_cost_prompt():
    """测试 CostAgent Prompt"""
    print("=" * 60)
    print("测试 3: cost_prompt.py")
    print("=" * 60)

    # 检查关键占位符
    required_vars = [
        "{KNOWLEDGE_FUSION_RULES}",
        "{battlefield_type}",
        "{monthly_volume}",
        "{current_channel}",
        "{target_country}",
        "{industry}",
        "{transaction_count}",
        "{fee_data_json}",
        "{annual_saving}",
        "{monthly_saving}",
    ]
    for var in required_vars:
        assert var in COST_AGENT_PROMPT, f"缺失变量: {var}"
    print(f"✅ 全部 {len(required_vars)} 个变量占位符完整")

    # 检查 5 项成本
    assert "显性手续费" in COST_AGENT_PROMPT, "缺失显性手续费"
    assert "汇率损失" in COST_AGENT_PROMPT, "缺失汇率损失"
    assert "资金时间成本" in COST_AGENT_PROMPT, "缺失资金时间成本"
    assert "多平台管理" in COST_AGENT_PROMPT, "缺失多平台管理"
    assert "合规风险" in COST_AGENT_PROMPT, "缺失合规风险"
    print("✅ 5 项成本计算规则完整")

    # 检查计算公式
    assert "月流水 × 手续费率 × 12" in COST_AGENT_PROMPT, "缺失显性手续费公式"
    assert "月流水 × 汇率差" in COST_AGENT_PROMPT, "缺失汇率损失公式"
    assert "结算天数/365" in COST_AGENT_PROMPT, "缺失资金时间成本公式"
    print("✅ 3 项核心计算公式完整")

    # 检查战场适配
    assert "增量战场" in COST_AGENT_PROMPT, "缺失增量战场策略"
    assert "存量战场" in COST_AGENT_PROMPT, "缺失存量战场策略"
    assert "教育战场" in COST_AGENT_PROMPT, "缺失教育战场策略"
    print("✅ 三种战场策略适配完整")

    # 检查输出格式
    assert "成本对比总表" in COST_AGENT_PROMPT, "缺失成本对比表"
    assert "核心结论" in COST_AGENT_PROMPT, "缺失核心结论"
    assert "对客户说的话" in COST_AGENT_PROMPT, "缺失话术"
    assert "隐性成本洞察" in COST_AGENT_PROMPT, "缺失隐性成本洞察"
    print("✅ 输出格式完整（表格/结论/话术/洞察）")

    # 检查解读话术
    assert "解读话术" in COST_AGENT_PROMPT, "缺失解读话术"
    print("✅ 包含 LLM 生成解读话术的要求")

    # 检查质量检查清单
    assert "质量检查清单" in COST_AGENT_PROMPT, "缺失自检清单"
    print("✅ 质量检查清单存在")

    # 检查渠道费率速查
    assert "银行电汇" in CHANNEL_FEE_REFERENCE, "缺失银行费率"
    assert "PingPong" in CHANNEL_FEE_REFERENCE, "缺失 PingPong 费率"
    print("✅ 渠道费率速查表完整")

    # 模拟注入测试
    mock_knowledge = "泰国 B2C 标准费率 0.80%，到账 T+1"
    mock_fee_data = json.dumps({
        "thailand": {"b2c_fee_rate": 0.008, "settlement_days": 1},
        "bank": {"fee_rate": 0.015, "fee_fixed": 150, "fx_spread": 0.008, "settlement_days": 4},
    }, ensure_ascii=False)

    filled_prompt = COST_AGENT_PROMPT.format(
        KNOWLEDGE_FUSION_RULES=KNOWLEDGE_FUSION_RULES.format(knowledge_text=mock_knowledge),
        battlefield_type="increment",
        monthly_volume="100",
        current_channel="银行电汇",
        target_country="泰国",
        industry="跨境电商（B2C）",
        transaction_count="100",
        fee_data_json=mock_fee_data,
        annual_saving="XX",
        monthly_saving="XX",
    )
    assert "0.80%" in filled_prompt, "注入后知识丢失"
    assert "隐性成本" in filled_prompt, "注入后战场策略丢失"
    print("✅ 模拟注入测试通过")
    print(f"   注入后 Prompt 长度: {len(filled_prompt)} 字符")

    print()


def test_integration():
    """集成测试：验证 Prompt 与 system_prompts.py 的兼容性"""
    print("=" * 60)
    print("测试 4: 集成兼容性")
    print("=" * 60)

    from prompts.system_prompts import AGENT_PROMPTS

    # 检查 system_prompts 中的注册
    assert "speech" in AGENT_PROMPTS, "system_prompts 未注册 speech"
    assert "cost" in AGENT_PROMPTS, "system_prompts 未注册 cost"
    print("✅ system_prompts.py 已注册 speech/cost")

    # 检查独立文件与 system_prompts 的一致性
    from prompts.system_prompts import SPEECH_AGENT_PROMPT as SYS_SPEECH
    from prompts.system_prompts import COST_AGENT_PROMPT as SYS_COST

    # 核心结构一致性检查（不要求完全相同，独立文件是增强版）
    assert "战场类型" in SYS_SPEECH, "system_prompts speech 缺失战场类型"
    assert "战场类型" in SPEECH_AGENT_PROMPT, "speech_prompt 缺失战场类型"
    assert "5 项总成本" in SYS_COST, "system_prompts cost 缺失5项成本"
    assert "5 项总成本" in COST_AGENT_PROMPT, "cost_prompt 缺失5项成本"
    print("✅ 独立文件与 system_prompts 核心结构一致")

    # 独立文件应包含更多细节
    assert len(SPEECH_AGENT_PROMPT) > len(SYS_SPEECH), "speech_prompt 应比 system_prompts 更详细"
    assert len(COST_AGENT_PROMPT) > len(SYS_COST), "cost_prompt 应比 system_prompts 更详细"
    print(f"✅ speech_prompt 更详细: {len(SPEECH_AGENT_PROMPT)} vs {len(SYS_SPEECH)} 字符")
    print(f"✅ cost_prompt 更详细: {len(COST_AGENT_PROMPT)} vs {len(SYS_COST)} 字符")

    print()


def main():
    """运行全部测试"""
    print("\n" + "=" * 60)
    print("Ksher AgentAI — Prompt 质量验证测试")
    print("=" * 60 + "\n")

    try:
        test_knowledge_fusion_rules()
        test_speech_prompt()
        test_cost_prompt()
        test_integration()

        print("=" * 60)
        print("🎉 全部测试通过！Prompt 质量合格。")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n💥 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
