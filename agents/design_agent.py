"""
DesignAgent — 品牌设计顾问 Agent

继承 BaseAgent，为 Ksher 代理商生成营销物料文案和 PPT 结构。
支持：海报文案、PPT 结构。

输出格式（INTERFACES.md）：
{
    "design_type": str,
    "headline": str,
    "subheadline": str,
    "selling_points": [str],
    "cta": str,
    "color_scheme": str,
    "layout_suggestion": str,
    "ppt_slides": [{"title": str, "content": str, "notes": str}]
}
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, agent_register
from prompts.system_prompts import DESIGN_AGENT_PROMPT
from prompts.knowledge_fusion_rules import KNOWLEDGE_FUSION_RULES
from config import AGENT_TEMPERATURE, BRAND_COLORS


@agent_register("design")
class DesignAgent(BaseAgent):
    """
    品牌设计顾问 Agent。

    生成专业营销物料：
    - 海报文案：主标题、副标题、卖点、CTA、配色、排版
    - PPT 结构：8页完整内容（封面→下一步）
    """

    temperature = AGENT_TEMPERATURE["design"]

    # 默认 PPT 结构
    DEFAULT_PPT_SLIDES = [
        {"title": "封面", "content": "客户公司名 + Ksher + 日期", "notes": "建立专业第一印象"},
        {"title": "关于 Ksher", "content": "公司介绍、牌照资质、服务规模", "notes": "建立信任：我们是持牌的正规平台"},
        {"title": "您的挑战", "content": "针对客户的痛点分析", "notes": "引起共鸣：说中客户的困扰"},
        {"title": "解决方案", "content": "Ksher 产品匹配客户场景", "notes": "核心价值：我们如何解决您的问题"},
        {"title": "费率优势", "content": "成本对比数据", "notes": "用数据说话：年省多少钱"},
        {"title": "合规保障", "content": "牌照 + 安全机制", "notes": "消除顾虑：资金安全有保障"},
        {"title": "接入流程", "content": "步骤 + 时间线", "notes": "降低门槛：其实很简单"},
        {"title": "下一步", "content": "CTA + 联系方式", "notes": "促成行动：明确下一步"},
    ]

    def generate(self, context: dict) -> dict:
        """
        同步生成设计物料。

        Args:
            context: {
                "design_type": str,         # "海报文案" | "PPT结构"
                "company": str,             # 客户公司名
                "industry": str,            # 行业
                "target_country": str,      # 目标国家
                "monthly_volume": float,    # 月流水（可选）
                "current_channel": str,     # 当前渠道（可选）
                "pain_points": [str],       # 痛点（可选）
                "cost_analysis": dict,      # 成本分析（可选）
            }

        Returns:
            dict: 海报文案或 PPT 结构
        """
        text = self._call_llm_sync(context)

        parsed = self._safe_parse_json(text)
        if parsed and self._validate_output(parsed, context):
            return parsed

        return self._parse_text_response(text, context)

    def build_system_prompt(self, knowledge: str) -> str:
        """构建 System Prompt"""
        prompt = DESIGN_AGENT_PROMPT.replace(
            "{KNOWLEDGE_FUSION_RULES}", KNOWLEDGE_FUSION_RULES
        )
        prompt += f"\n\n## 品牌色系\n"
        prompt += f"主色：{BRAND_COLORS['primary']}（Ksher红）\n"
        prompt += f"辅色：{BRAND_COLORS['secondary']}（深蓝）\n"
        prompt += f"强调色：{BRAND_COLORS['accent']}（青色）\n"
        prompt += f"\n## 知识库\n\n{knowledge[:1500]}"
        return prompt

    def build_user_message(self, context: dict) -> str:
        """构建 User Message"""
        design_type = context.get("design_type", "海报文案")
        company = context.get("company", "您的公司")
        industry = context.get("industry", "")
        target_country = context.get("target_country", "")
        current_channel = context.get("current_channel", "")
        pain_points = context.get("pain_points", [])
        cost_analysis = context.get("cost_analysis", {})

        lines = [
            f"## 设计需求",
            f"设计类型：{design_type}",
            f"客户公司：{company}",
        ]

        if industry:
            lines.append(f"行业：{industry}")
        if target_country:
            lines.append(f"目标国家：{target_country}")
        if current_channel:
            lines.append(f"当前渠道：{current_channel}")
        if pain_points:
            lines.append(f"痛点：{', '.join(pain_points)}")

        if cost_analysis:
            annual_saving = cost_analysis.get("annual_saving", 0)
            if annual_saving > 0:
                lines.append(f"年节省金额：¥{annual_saving:,.0f}")

        lines.extend([
            f"",
            f"## 输出要求",
            f"请生成设计内容，严格按 JSON 格式输出：",
            f"",
            f"```json",
            f"{{",
            f'  "design_type": "{design_type}",',
            f'  "headline": "主标题（8字以内，吸引眼球）",',
            f'  "subheadline": "副标题（15字以内，补充信息）",',
            f'  "selling_points": ["卖点1（10字以内）", "卖点2", "卖点3"],',
            f'  "cta": "行动号召",',
            f'  "color_scheme": "主色+辅色+背景色",',
            f'  "layout_suggestion": "排版建议",',
        ])

        if design_type == "PPT结构":
            lines.extend([
                f'  "ppt_slides": [',
                f'    {{"title": "封面", "content": "...", "notes": "..."}},',
                f'    ...',
                f'  ]',
            ])
        else:
            lines.append(f'  "ppt_slides": []')

        lines.extend([
            f"}}",
            f"```",
            f"",
            f"设计原则：",
            f"- 专业但不刻板，像知名咨询公司的输出",
            f"- 数据优先于描述，图表优先于文字",
            f"- 每页/每屏一个核心信息，不堆砌",
            f"- 配色建议基于 Ksher 品牌色系",
        ])

        return "\n".join(lines)

    def _validate_output(self, parsed: dict, context: dict) -> bool:
        """验证输出结构"""
        required = ["design_type", "headline", "subheadline", "selling_points", "cta", "color_scheme", "layout_suggestion"]
        if not all(k in parsed for k in required):
            return False

        design_type = context.get("design_type", "海报文案")
        if design_type == "PPT结构" and "ppt_slides" not in parsed:
            return False

        return True

    def _parse_text_response(self, text: str, context: dict) -> dict:
        """回退解析"""
        design_type = context.get("design_type", "海报文案")

        return {
            "design_type": design_type,
            "headline": "东南亚收款，选本地的",
            "subheadline": "Ksher 本地牌照，T+1到账",
            "selling_points": [
                "泰国央行牌照",
                "T+1极速到账",
                "费率透明",
            ],
            "cta": "扫码咨询，免费测算",
            "color_scheme": f"主色 {BRAND_COLORS['primary']} + 辅色 {BRAND_COLORS['secondary']} + 背景白",
            "layout_suggestion": "标题居中，卖点横向排列，CTA底部突出",
            "ppt_slides": self.DEFAULT_PPT_SLIDES if design_type == "PPT结构" else [],
        }


if __name__ == "__main__":
    print("=" * 60)
    print("DesignAgent 模块测试")
    print("=" * 60)

    from services.knowledge_loader import KnowledgeLoader

    class MockLLM:
        def call_sync(self, agent_name, system, user_msg, temperature=0.6):
            return json.dumps({
                "design_type": "海报文案",
                "headline": "东南亚收款快人一步",
                "subheadline": "Ksher 本地牌照，T+1到账",
                "selling_points": ["泰国央行牌照", "T+1极速到账", "费率低至0.8%"],
                "cta": "扫码咨询，免费测算",
                "color_scheme": "主色 #E83E4C + 辅色 #1A1A2E + 背景白",
                "layout_suggestion": "标题居中大字，卖点三列横排，CTA底部红色按钮",
                "ppt_slides": [],
            })

    loader = KnowledgeLoader()
    agent = DesignAgent(MockLLM(), loader)

    ctx = {
        "design_type": "海报文案",
        "company": "跨境通科技",
        "industry": "b2c",
        "target_country": "thailand",
        "current_channel": "银行电汇",
        "pain_points": ["手续费高", "到账慢"],
    }

    result = agent.generate(ctx)
    print(f"\n生成结果：")
    for k, v in result.items():
        if isinstance(v, list):
            print(f"  {k}: {v}")
        else:
            print(f"  {k}: {v}")
