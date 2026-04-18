"""
ProposalAgent — 解决方案顾问 Agent

继承 BaseAgent，为客户生成定制化跨境收款方案。
依赖 CostAgent 的输出（cost_analysis）注入费率优势章节。

输出格式（INTERFACES.md）：
{
    "industry_insight": str,
    "pain_diagnosis": str,
    "solution": str,
    "product_recommendation": str,
    "fee_advantage": str,
    "compliance": str,
    "onboarding_flow": str,
    "next_steps": str
}
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, agent_register
from prompts.system_prompts import PROPOSAL_AGENT_PROMPT
from prompts.knowledge_fusion_rules import KNOWLEDGE_FUSION_RULES
from config import BATTLEFIELD_TYPES, AGENT_TEMPERATURE, INDUSTRY_OPTIONS, COUNTRY_OPTIONS


@agent_register("proposal")
class ProposalAgent(BaseAgent):
    """
    解决方案顾问 Agent。

    生成 8 章节专业方案：行业洞察 → 痛点诊断 → 解决方案 → 产品推荐 →
    费率优势 → 合规保障 → 接入流程 → 下一步行动。

    依赖 CostAgent 输出：如果上下文中包含 cost_analysis，
    将费率数据注入方案中的「费率优势」章节。
    """

    temperature = AGENT_TEMPERATURE["proposal"]

    def generate(self, context: dict) -> dict:
        """
        同步生成解决方案。

        Args:
            context: {
                "company": str,
                "industry": str,
                "target_country": str,
                "monthly_volume": float,
                "current_channel": str,
                "pain_points": [str],
                "battlefield": str,
                "cost_analysis": dict,      # 来自 CostAgent（可选）
            }

        Returns:
            dict: 8 章节方案
        """
        text = self._call_llm_sync(context)

        parsed = self._safe_parse_json(text)
        if parsed and self._validate_output(parsed):
            return parsed

        return self._parse_text_response(text, context)

    def build_system_prompt(self, knowledge: str) -> str:
        """构建 System Prompt"""
        prompt = PROPOSAL_AGENT_PROMPT.replace(
            "{KNOWLEDGE_FUSION_RULES}", KNOWLEDGE_FUSION_RULES
        )
        prompt += f"\n\n## 知识库\n\n{knowledge[:2000]}"
        return prompt

    def build_user_message(self, context: dict) -> str:
        """构建 User Message（客户上下文 + Cost 数据）"""
        battlefield = context.get("battlefield", "education")
        bf_info = BATTLEFIELD_TYPES.get(battlefield, {})
        industry = context.get("industry", "")
        target_country = context.get("target_country", "")
        current_channel = context.get("current_channel", "")
        pain_points = context.get("pain_points", [])

        # 注入 CostAgent 数据（如果存在）
        cost_analysis = context.get("cost_analysis", {})
        annual_saving = cost_analysis.get("annual_saving", 0)
        comparison_table = cost_analysis.get("comparison_table", {})

        lines = [
            f"## 客户画像\n",
            self._build_context_summary(context),
            f"\n## 战场类型：{battlefield}",
            f"战场标签：{bf_info.get('label', '')}",
            f"方案重点：{bf_info.get('proposal_focus', '')}",
        ]

        # 注入成本数据
        if annual_saving > 0:
            lines.extend([
                f"\n## 成本分析数据（来自 CostAgent）",
                f"年节省金额：¥{annual_saving:,.0f}",
                f"节省比例：{cost_analysis.get('saving_rate', 0)}%",
            ])
            if comparison_table:
                ksher_total = comparison_table.get("ksher", {}).get("total", 0)
                current_total = comparison_table.get("current", {}).get("total", 0)
                lines.append(f"Ksher 年度总成本：¥{ksher_total:,.0f}")
                lines.append(f"当前渠道年度总成本：¥{current_total:,.0f}")

        # 输出格式要求
        lines.extend([
            f"\n## 输出要求",
            f"请生成以下 8 个章节的方案，每个章节至少 200 字，严格按 JSON 格式输出：",
            f"",
            f"```json",
            f"{{",
            f'  "industry_insight": "基于 {INDUSTRY_OPTIONS.get(industry, industry)} 的行业趋势和挑战",',
            f'  "pain_diagnosis": "针对客户使用 {current_channel} 的具体痛点诊断",',
            f'  "solution": "Ksher 如何解决每个痛点",',
            f'  "product_recommendation": "根据 {COUNTRY_OPTIONS.get(target_country, target_country)} 推荐最适合的产品组合",',
            f'  "fee_advantage": "引用成本数据：切换到 Ksher，年省 ¥{annual_saving:,.0f}",',
            f'  "compliance": "Ksher 在 {COUNTRY_OPTIONS.get(target_country, target_country)} 的合规保障",',
            f'  "onboarding_flow": "从签约到收款的完整流程",',
            f'  "next_steps": "明确的下一步行动 CTA"',
            f"}}",
            f"```",
            f"",
            f"写作要求：",
            f"- 像写给 CEO 的商业提案，不像产品手册",
            f"- 每个章节至少 200 字，内容详实有深度，总计 1600-3200 字",
            f"- 引用真实数据（费率/到账时间/牌照）",
            f"- 痛点要具体，不要泛泛而谈",
        ])

        if pain_points:
            lines.append(f"- 重点回应客户痛点：{', '.join(pain_points)}")

        return "\n".join(lines)

    def _validate_output(self, parsed: dict) -> bool:
        """验证输出是否包含所有必需字段"""
        required = [
            "industry_insight", "pain_diagnosis", "solution",
            "product_recommendation", "fee_advantage", "compliance",
            "onboarding_flow", "next_steps",
        ]
        return all(k in parsed and parsed[k] for k in required)

    def _parse_text_response(self, text: str, context: dict) -> dict:
        """回退解析：按章节标题提取内容"""
        import re

        result = {key: "" for key in [
            "industry_insight", "pain_diagnosis", "solution",
            "product_recommendation", "fee_advantage", "compliance",
            "onboarding_flow", "next_steps",
        ]}

        # 章节标题映射
        title_patterns = {
            "industry_insight": r"(?:一、|1\.?\s*)[\s\S]*?行业洞察|行业趋势|行业现状",
            "pain_diagnosis": r"(?:二、|2\.?\s*)[\s\S]*?痛点诊断|痛点分析|客户挑战",
            "solution": r"(?:三、|3\.?\s*)[\s\S]*?解决方案|解决|方案",
            "product_recommendation": r"(?:四、|4\.?\s*)[\s\S]*?产品推荐|产品|推荐",
            "fee_advantage": r"(?:五、|5\.?\s*)[\s\S]*?费率优势|成本|节省|费率",
            "compliance": r"(?:六、|6\.?\s*)[\s\S]*?合规保障|合规|牌照|安全",
            "onboarding_flow": r"(?:七、|7\.?\s*)[\s\S]*?接入流程|开户|上线|流程",
            "next_steps": r"(?:八、|8\.?\s*)[\s\S]*?下一步|行动|CTA|安排",
        }

        for key, pattern in title_patterns.items():
            matches = re.findall(
                rf"{pattern}.*?[\n:：](.+?)(?=\n##|\n### |\n(?:一、|二、|三、|四、|五、|六、|七、|八、)|\Z)",
                text, re.DOTALL | re.IGNORECASE
            )
            if matches:
                result[key] = matches[0].strip()

        # 填充默认值
        return self._fill_defaults(result, context)

    def _fill_defaults(self, result: dict, context: dict) -> dict:
        """为空字段填充默认内容"""
        industry = context.get("industry", "")
        target_country = context.get("target_country", "")
        current_channel = context.get("current_channel", "")
        cost_analysis = context.get("cost_analysis", {})
        annual_saving = cost_analysis.get("annual_saving", 0)

        defaults = {
            "industry_insight": f"{INDUSTRY_OPTIONS.get(industry, industry)}正处于快速增长期，东南亚市场成为主要增长点。跨境收款环节存在成本高、到账慢、合规风险等核心挑战。",
            "pain_diagnosis": f"使用 {current_channel} 收款，客户面临手续费高、汇率损失大、到账周期长等痛点，直接影响资金周转效率和利润率。",
            "solution": "Ksher 提供东南亚本地收款解决方案：本地牌照保障资金安全，T+1 快速到账，透明费率降低综合成本，一站式管理多平台资金。",
            "product_recommendation": f"针对 {COUNTRY_OPTIONS.get(target_country, target_country)} 市场，推荐 Ksher 本地收款账户，直接收取当地货币，避免多重汇兑损失。",
            "fee_advantage": f"切换到 Ksher，年省 ¥{annual_saving:,.0f}。费率透明无隐藏成本，汇率优于银行牌价，资金占用成本显著降低。",
            "compliance": "Ksher 持有东南亚多国央行颁发的支付牌照，资金本地清算，合规链路完整，为客户提供银行级别的资金安全保障。",
            "onboarding_flow": "1. 线上提交开户申请 → 2. 资料审核（1-2 个工作日）→ 3. 账户开通 → 4. 技术对接 → 5. 开始收款。全程专人一对一服务。",
            "next_steps": "建议安排 30 分钟线上沟通，详细了解您的业务需求后，为您定制最优收款方案。",
        }

        for key, default in defaults.items():
            if not result.get(key):
                result[key] = default

        return result


if __name__ == "__main__":
    print("=" * 60)
    print("ProposalAgent 模块测试")
    print("=" * 60)

    from services.knowledge_loader import KnowledgeLoader

    class MockLLM:
        def call_sync(self, agent_name, system, user_msg, temperature=0.5):
            return json.dumps({
                "industry_insight": "【测试】B2C 跨境电商正处于东南亚爆发期",
                "pain_diagnosis": "【测试】银行电汇隐性成本高",
                "solution": "【测试】Ksher 本地收款 T+1 到账",
                "product_recommendation": "【测试】推荐泰国本地收款账户",
                "fee_advantage": "【测试】年省 ¥35,000",
                "compliance": "【测试】持有泰国央行支付牌照",
                "onboarding_flow": "【测试】5步开户流程",
                "next_steps": "【测试】安排30分钟线上沟通",
            })

    loader = KnowledgeLoader()
    agent = ProposalAgent(MockLLM(), loader)

    ctx = {
        "company": "测试公司",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 50000,
        "current_channel": "银行电汇",
        "pain_points": ["手续费高", "到账慢"],
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
    print(f"\n生成结果（{len(result)} 个字段）：")
    for k, v in result.items():
        preview = v[:60] if isinstance(v, str) else str(v)[:60]
        print(f"  {k}: {preview}...")
