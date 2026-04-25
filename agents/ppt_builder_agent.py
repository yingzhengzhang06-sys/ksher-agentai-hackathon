"""
PPT Builder Agent — 从客户上下文生成完整PPT

1. 调用K2.6生成详细幻灯片大纲
2. 调用PPTGenerator渲染为.pptx文件
3. 返回文件路径和预览信息
"""
import json
import time
from io import BytesIO

from agents.base_agent import BaseAgent, agent_register
from config import AGENT_TEMPERATURE, BRAND_COLORS
from services.ppt_generator import PPTGenerator


@agent_register("ppt_builder")
class PPTBuilderAgent(BaseAgent):
    """PPT生成Agent：大纲→文件"""

    agent_name = "ppt_builder"
    temperature = AGENT_TEMPERATURE.get("ppt_builder", 0.5)

    def build_system_prompt(self, knowledge: str = "") -> str:
        return """你是Ksher的专业PPT设计顾问。你的职责是根据客户画像和方案内容，生成结构清晰、数据驱动的PPT大纲。

## 输出格式（严格JSON）
```json
{
  "title": "方案标题（含客户名）",
  "subtitle": "副标题/一句话价值主张",
  "slides": [
    {
      "slide_num": 1,
      "title": "页面标题",
      "content": "要点内容，\\n分隔",
      "speaker_notes": "演讲者备注",
      "layout": "content"
    }
  ]
}
```

## PPT结构规范（6-8页）
1. **封面**：客户名 + 方案主题 + Ksher品牌
2. **客户画像**：行业/国家/痛点摘要
3. **当前痛点**：数据驱动的痛点分析
4. **Ksher方案**：核心优势 + 差异化
5. **成本对比**：费率/时效/隐性成本
6. **实施路径**：开户→上线→优化
7. **结尾页**：CTA + 联系方式

## 设计原则
- 每页内容精炼，不超过5个要点
- 数据驱动：用具体数字说话
- 品牌一致性：使用Ksher红(#E83E4C)和活力绿(#00C9A7)
- 演讲者备注要详细，帮助演讲者讲好每一页

## 约束
- 只输出JSON，不要任何markdown包裹或解释文字
- 确保JSON可被标准json.loads解析
"""

    def build_user_message(self, context: dict) -> str:
        company = context.get("company", "客户")
        industry = context.get("industry", "")
        country = context.get("target_country", "")
        volume = context.get("monthly_volume", 0)
        channel = context.get("current_channel", "")
        pain_points = context.get("pain_points", [])
        battlefield = context.get("battlefield", "education")

        # 注入依赖结果（如果有）
        cost_result = context.get("_cost_analysis_result", {})
        speech_result = context.get("_speech_generation_result", {})

        cost_summary = ""
        if cost_result:
            summary = cost_result.get("summary", "")
            annual_saving = cost_result.get("annual_saving", 0)
            if summary:
                cost_summary = f"\n成本分析摘要：{summary}"
            if annual_saving:
                cost_summary += f"\n预计年省：{annual_saving}万元"

        pain_text = "、".join(pain_points) if pain_points else "未明确"

        return f"""请为以下客户生成PPT大纲：

## 客户信息
- 公司名：{company}
- 行业：{industry}
- 目标国家：{country}
- 月流水：{volume}万元
- 当前渠道：{channel}
- 战场类型：{battlefield}
- 痛点：{pain_text}
{cost_summary}

## 要求
生成6-8页的PPT大纲，包含封面、客户画像、痛点分析、Ksher方案、成本对比、实施路径、结尾页。
每页提供详细的演讲者备注。"""

    def generate(self, context: dict) -> dict:
        """生成PPT：先K2.6生成大纲，再python-pptx渲染"""
        if not getattr(self, "llm_client", None):
            # LLM未初始化，返回默认大纲生成的PPT
            outline = self._default_outline(context)
            generator = PPTGenerator()
            ppt_bytes = generator.generate(outline)
            return {
                "title": outline.get("title", "方案演示"),
                "subtitle": outline.get("subtitle", ""),
                "slide_count": len(outline.get("slides", [])),
                "outline": outline,
                "ppt_bytes": ppt_bytes,
                "file_name": f"{context.get('company', '客户')}_Ksher方案_{time.strftime('%Y%m%d')}.pptx",
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }

        # Step 1: 生成大纲
        system = self.build_system_prompt()
        user_msg = self.build_user_message(context)
        raw_outline = self.llm_client.call_sync(
            agent_name=self.agent_name,
            system=system,
            user_msg=user_msg,
            temperature=self.temperature,
        )

        outline = self._safe_parse_json(raw_outline)
        if not outline:
            outline = self._default_outline(context)

        # Step 2: 渲染PPT文件
        generator = PPTGenerator()
        ppt_bytes = generator.generate(outline)

        # Step 3: 返回结果
        return {
            "title": outline.get("title", "方案演示"),
            "subtitle": outline.get("subtitle", ""),
            "slide_count": len(outline.get("slides", [])),
            "outline": outline,
            "ppt_bytes": ppt_bytes,
            "file_name": f"{context.get('company', '客户')}_Ksher方案_{time.strftime('%Y%m%d')}.pptx",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

    def _default_outline(self, context: dict) -> dict:
        """默认PPT大纲（K2.6失败时兜底）"""
        company = context.get("company", "客户")
        industry = context.get("industry", "")
        country = context.get("target_country", "")
        volume = context.get("monthly_volume", 0)

        return {
            "title": f"{company} × Ksher 跨境收款解决方案",
            "subtitle": "东南亚本地牌照 · 更低费率 · 更快到账",
            "slides": [
                {
                    "slide_num": 1,
                    "title": "客户画像",
                    "content": f"## 客户概况\n- 行业：{industry}\n- 目标市场：{country}\n- 月流水：{volume}万元\n- 当前痛点：手续费高、到账慢、汇率损失",
                    "speaker_notes": "简要介绍客户背景，建立共鸣。",
                    "layout": "content",
                },
                {
                    "slide_num": 2,
                    "title": "当前痛点分析",
                    "content": "## 三大核心痛点\n1. 手续费蚕食利润：传统渠道综合费率高达1.0%+\n2. 到账慢影响现金流：3-5个工作日才能到账\n3. 汇率损失不可控：银行结汇汇率比市场中间价高0.8-1.5%",
                    "speaker_notes": "用数据说话，让客户意识到隐性成本。",
                    "layout": "content",
                },
                {
                    "slide_num": 3,
                    "title": "Ksher差异化方案",
                    "content": "## Ksher核心优势\n1. 东南亚本地牌照：泰国/马来/菲律宾/印尼直接清算\n2. 综合费率低至0.6%：手续费+汇率点差全面优化\n3. T+0到账：本地清算，资金当日可提\n4. 全程合规：持牌经营，资金安全保障",
                    "speaker_notes": "突出Ksher的牌照优势和费率优势。",
                    "layout": "content",
                },
                {
                    "slide_num": 4,
                    "title": "成本对比",
                    "content": "## 费率对比（以月流水100万为例）\n- 银行电汇：约1.0%综合成本 = 1万元/月\n- 第三方平台：约0.7%综合成本 = 7,000元/月\n- Ksher：约0.6%综合成本 = 6,000元/月\n\n## 年省金额\n相比银行电汇：年省约4.8万元\n相比第三方平台：年省约1.2万元",
                    "speaker_notes": "用具体数字展示节省金额，强化ROI。",
                    "layout": "two_column",
                },
                {
                    "slide_num": 5,
                    "title": "实施路径",
                    "content": "## 三步快速上线\n1. 开户审核（1-2工作日）：提交资料→资质审核→账户开通\n2. 技术对接（3-5工作日）：API对接→测试验证→生产上线\n3. 运营优化（持续）：数据监控→费率优化→增值服务",
                    "speaker_notes": "消除客户对切换成本的担忧，强调快速上线。",
                    "layout": "content",
                },
            ],
        }
