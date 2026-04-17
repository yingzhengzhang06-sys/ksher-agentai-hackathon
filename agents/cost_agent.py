"""
CostAgent — 成本分析 Agent

继承 BaseAgent，调用 CostCalculator 获取精确计算数据，
再用 LLM 生成有说服力的 AI 解读话术。

输出格式（INTERFACES.md）：
{
    "comparison_table": {
        "ksher": {"fee": float, "fx_loss": float, "time_cost": float,
                  "mgmt_cost": float, "compliance_cost": float, "total": float},
        "current": {"fee": float, "fx_loss": float, "time_cost": float,
                    "mgmt_cost": float, "compliance_cost": float, "total": float}
    },
    "annual_saving": float,
    "chart_data": dict,
    "summary": str
}
"""
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, agent_register
from services.cost_calculator import calculate_comparison, format_cost_summary
from prompts.system_prompts import COST_AGENT_PROMPT
from prompts.knowledge_fusion_rules import KNOWLEDGE_FUSION_RULES
from config import AGENT_TEMPERATURE


@agent_register("cost")
class CostAgent(BaseAgent):
    """
    成本分析 Agent。

    1. 调用 CostCalculator 进行精确的成本计算（纯 Python，不调用 AI）
    2. 将计算结果注入 Prompt，调用 LLM 生成 AI 解读话术
    3. 输出结构化数据（对比表 + 图表数据 + 话术摘要）
    """

    temperature = AGENT_TEMPERATURE["cost"]

    def generate(self, context: dict) -> dict:
        """
        同步生成成本分析结果。

        Args:
            context: {
                "industry": str,
                "target_country": str,
                "monthly_volume": float,
                "current_channel": str,
                "pain_points": [str],
                "battlefield": str,     # 可选
            }

        Returns:
            dict: {"comparison_table", "annual_saving", "chart_data", "summary"}
        """
        industry = context.get("industry", "")
        target_country = context.get("target_country", "")
        monthly_volume = context.get("monthly_volume", 0)
        current_channel = context.get("current_channel", "")

        # ── 步骤1：精确计算（纯 Python，不调用 AI）──
        calc_result = calculate_comparison(
            industry=industry,
            target_country=target_country,
            monthly_volume=monthly_volume,
            current_channel=current_channel,
        )

        # ── 步骤2：用 LLM 生成 AI 解读话术 ──
        # 将计算结果格式化为文本，注入 Prompt
        cost_summary = format_cost_summary(calc_result)

        # 构建增强上下文（包含计算结果）
        enriched_context = dict(context)
        enriched_context["_cost_summary"] = cost_summary
        enriched_context["_annual_saving"] = calc_result["annual_saving"]
        enriched_context["_monthly_saving"] = calc_result["monthly_saving"]
        enriched_context["_saving_rate"] = calc_result["saving_rate"]

        # 调用 LLM 生成解读
        llm_response = self._call_llm_sync(enriched_context)

        # 尝试从 LLM 响应中提取 summary
        summary = self._extract_summary(llm_response, calc_result)

        # ── 步骤3：组装最终输出 ──
        return {
            "comparison_table": calc_result["comparison_table"],
            "annual_saving": calc_result["annual_saving"],
            "chart_data": calc_result["chart_data"],
            "summary": summary,
            "monthly_saving": calc_result["monthly_saving"],
            "saving_rate": calc_result["saving_rate"],
        }

    def build_system_prompt(self, knowledge: str) -> str:
        """构建 System Prompt（注入知识库和计算规则）"""
        # 使用 replace() 仅替换 KNOWLEDGE_FUSION_RULES，保留模板中的其他占位符
        # 动态字段（战场类型、客户画像、计算结果等）由 build_user_message() 注入
        prompt = COST_AGENT_PROMPT.replace(
            "{KNOWLEDGE_FUSION_RULES}", KNOWLEDGE_FUSION_RULES
        )
        prompt += f"\n\n## 知识库\n\n{knowledge[:1500]}"
        return prompt

    def build_user_message(self, context: dict) -> str:
        """构建 User Message（客户上下文 + 成本计算结果）"""
        cost_summary = context.get("_cost_summary", "")
        annual_saving = context.get("_annual_saving", 0)
        monthly_saving = context.get("_monthly_saving", 0)
        saving_rate = context.get("_saving_rate", 0)

        lines = [
            f"## 客户画像\n",
            self._build_context_summary(context),
            f"\n## 成本计算结果（已由系统精确计算）\n",
            cost_summary,
            f"\n## 你的任务",
            f"基于以上精确计算数据，生成一段有说服力的 AI 解读话术。",
            f"要求：",
            f"1. 用一句话概括核心结论（'切换到 Ksher，年省 ¥{annual_saving:,.0f}，相当于每月多赚 ¥{monthly_saving:,.0f}'）",
            f"2. 用通俗易懂的语言解释 5 项成本差异",
            f"3. 结合客户的痛点（{', '.join(context.get('pain_points', []))}）强化说服力",
            f"4. 最后给出一个有力的行动号召",
            f"",
            f"请只输出 summary 文本（200-400字），不需要表格。",
        ]
        return "\n".join(lines)

    def _extract_summary(self, llm_response: str, calc_result: dict) -> str:
        """
        从 LLM 响应中提取 summary，失败时返回默认话术。
        """
        if not llm_response or not llm_response.strip():
            return self._default_summary(calc_result)

        # 清理响应文本（移除 JSON 标记等）
        text = llm_response.strip()
        if text.startswith("```"):
            # 尝试提取代码块内容
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                text = match.group(1).strip()

        # 如果响应看起来是 JSON，尝试解析
        parsed = self._safe_parse_json(text)
        if parsed and isinstance(parsed, dict):
            if "summary" in parsed:
                return parsed["summary"]

        # 直接使用文本作为 summary（LLM 返回的是纯文本）
        if len(text) > 20:
            return text

        return self._default_summary(calc_result)

    def _default_summary(self, calc_result: dict) -> str:
        """默认成本解读话术（回退用）"""
        annual_saving = calc_result["annual_saving"]
        monthly_saving = calc_result["monthly_saving"]
        saving_rate = calc_result["saving_rate"]
        current_channel = calc_result["details"]["current_channel"]
        monthly_volume = calc_result["details"]["monthly_volume"]

        return (
            f"根据您的月流水 ${monthly_volume:,.0f} USD，我们为您算了笔账："
            f"使用 {current_channel} 收款，一年下来的总成本包括手续费、汇率损失、"
            f"资金占用成本、管理成本和合规风险，合计远超您的预期。"
            f"切换到 Ksher，年省 ¥{annual_saving:,.0f}（节省 {saving_rate}%），"
            f"相当于每月多赚 ¥{monthly_saving:,.0f}。这笔钱本来可以是您的利润。"
        )


if __name__ == "__main__":
    print("=" * 60)
    print("CostAgent 模块测试")
    print("=" * 60)

    # 模拟测试（无需 LLM）
    from services.knowledge_loader import KnowledgeLoader

    class MockLLM:
        def call_sync(self, agent_name, system, user_msg, temperature=0.3):
            return (
                f"根据您的月流水情况，我们为您算了笔账：使用当前渠道收款，"
                f"一年下来的隐性成本远超您的预期。切换到 Ksher，"
                f"年省一大笔钱，相当于每月多赚一笔可观的利润。"
            )

    loader = KnowledgeLoader()
    agent = CostAgent(MockLLM(), loader)

    ctx = {
        "company": "测试公司",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 50000,
        "current_channel": "银行电汇",
        "pain_points": ["手续费高", "到账慢"],
    }

    result = agent.generate(ctx)
    print(f"\n生成结果：")
    print(f"  comparison_table: Ksher ¥{result['comparison_table']['ksher']['total']:,.2f} vs 当前 ¥{result['comparison_table']['current']['total']:,.2f}")
    print(f"  annual_saving: ¥{result['annual_saving']:,.2f}")
    print(f"  summary: {result['summary'][:100]}...")
    print(f"  chart_data keys: {list(result['chart_data'].keys())}")
