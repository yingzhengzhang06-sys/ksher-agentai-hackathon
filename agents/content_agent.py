"""
ContentAgent — 内容营销专家 Agent

继承 BaseAgent，为 Ksher 城市代理商生成高质量社交媒体内容。
支持：朋友圈 7 天计划、获客海报文案、小红书/公众号、短视频口播稿。

输出格式（INTERFACES.md）：
{
    "content_type": str,
    "contents": [
        {
            "day": int,
            "title": str,
            "body": str,
            "image_suggestion": str,
            "publish_time": str,
            "category": str
        }
    ]
}
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, agent_register
from prompts.system_prompts import CONTENT_AGENT_PROMPT
from prompts.knowledge_fusion_rules import KNOWLEDGE_FUSION_RULES
from config import AGENT_TEMPERATURE


@agent_register("content")
class ContentAgent(BaseAgent):
    """
    内容营销专家 Agent。

    根据内容类型和目标受众，生成社交媒体内容：
    - 朋友圈 7 天计划
    - 获客海报文案
    - 小红书/公众号文章
    - 短视频口播稿
    """

    temperature = AGENT_TEMPERATURE["content"]

    # 内容类型配置
    CONTENT_TYPES = {
        "朋友圈7天计划": {
            "days": 7,
            "categories": ["行业趋势", "痛点共鸣", "产品价值", "客户案例", "个人分享", "互动问答", "软性推广"],
            "default_length": "80-150字",
        },
        "获客海报文案": {
            "days": 1,
            "categories": ["海报文案"],
            "default_length": "短文案",
        },
        "小红书/公众号": {
            "days": 1,
            "categories": ["长文"],
            "default_length": "500-800字",
        },
        "短视频口播稿": {
            "days": 1,
            "categories": ["口播稿"],
            "default_length": "30-60秒",
        },
    }

    def generate(self, context: dict) -> dict:
        """
        同步生成内容。

        Args:
            context: {
                "content_type": str,        # 内容类型
                "target_audience": str,     # 目标受众描述
                "industry": str,            # 行业（可选）
                "target_country": str,      # 目标国家（可选）
                "pain_points": [str],       # 痛点（可选）
                "company": str,             # 公司名（可选）
            }

        Returns:
            dict: {"content_type", "contents": [...]}
        """
        text = self._call_llm_sync(context)

        parsed = self._safe_parse_json(text)
        if parsed and self._validate_output(parsed):
            return parsed

        return self._parse_text_response(text, context)

    def build_system_prompt(self, knowledge: str) -> str:
        """构建 System Prompt"""
        prompt = CONTENT_AGENT_PROMPT.replace(
            "{KNOWLEDGE_FUSION_RULES}", KNOWLEDGE_FUSION_RULES
        )
        prompt += f"\n\n## 知识库\n\n{knowledge[:2000]}"
        return prompt

    def build_user_message(self, context: dict) -> str:
        """构建 User Message"""
        content_type = context.get("content_type", "朋友圈7天计划")
        target_audience = context.get("target_audience", "跨境电商卖家")
        industry = context.get("industry", "")
        target_country = context.get("target_country", "")
        pain_points = context.get("pain_points", [])
        company = context.get("company", "")

        config = self.CONTENT_TYPES.get(content_type, self.CONTENT_TYPES["朋友圈7天计划"])

        lines = [
            f"## 内容需求",
            f"内容类型：{content_type}",
            f"目标受众：{target_audience}",
        ]

        if industry:
            lines.append(f"行业：{industry}")
        if target_country:
            lines.append(f"目标国家：{target_country}")
        if company:
            lines.append(f"公司名：{company}")
        if pain_points:
            lines.append(f"客户痛点：{', '.join(pain_points)}")

        lines.extend([
            f"",
            f"## 输出要求",
            f"请生成以下内容，严格按 JSON 格式输出：",
            f"",
            f"```json",
            f"{{",
            f'  "content_type": "{content_type}",',
            f'  "contents": [',
        ])

        # 根据内容类型生成不同的输出模板
        if content_type == "朋友圈7天计划":
            for i, cat in enumerate(config["categories"], 1):
                lines.extend([
                    f'    {{',
                    f'      "day": {i},',
                    f'      "title": "Day {i} | {cat}",',
                    f'      "body": "{config["default_length"]}文案内容，带emoji但不过度",',
                    f'      "image_suggestion": "配图建议",',
                    f'      "publish_time": "建议发布时间",',
                    f'      "category": "{cat}"',
                    f'    }}{"," if i < len(config["categories"]) else ""}',
                ])
        else:
            lines.extend([
                f'    {{',
                f'      "day": 1,',
                f'      "title": "内容标题",',
                f'      "body": "正文内容",',
                f'      "image_suggestion": "配图建议",',
                f'      "publish_time": "建议发布时间",',
                f'      "category": "{content_type}"',
                f'    }}',
            ])

        lines.extend([
            f'  ]',
            f"}}",
            f"```",
            f"",
            f"写作原则：",
            f"- 像真人代理商发的，不像品牌官方号",
            f"- 有温度，有故事感，避免硬广",
            f"- 每条内容都有一个清晰的价值点",
            f"- 适当使用 emoji，但不要过度",
        ])

        return "\n".join(lines)

    def _validate_output(self, parsed: dict) -> bool:
        """验证输出结构"""
        if "content_type" not in parsed or "contents" not in parsed:
            return False
        if not isinstance(parsed["contents"], list):
            return False
        for item in parsed["contents"]:
            if not all(k in item for k in ["day", "title", "body", "category"]):
                return False
        return True

    def _parse_text_response(self, text: str, context: dict) -> dict:
        """回退解析"""
        content_type = context.get("content_type", "朋友圈7天计划")

        # 尝试按天分割提取内容
        import re
        contents = []

        # 匹配 Day X 或 第X天
        day_pattern = r'(?:Day|第)\s*(\d+).*?[\n:：](.+?)(?=(?:Day|第)\s*\d+|\Z)'
        matches = re.findall(day_pattern, text, re.DOTALL | re.IGNORECASE)

        if matches:
            for day_num, content in matches:
                contents.append({
                    "day": int(day_num),
                    "title": f"Day {day_num}",
                    "body": content.strip()[:500],
                    "image_suggestion": "建议配相关主题图片",
                    "publish_time": "19:00-21:00",
                    "category": "内容",
                })

        if not contents:
            # 整体作为一个内容
            contents.append({
                "day": 1,
                "title": content_type,
                "body": text.strip()[:800],
                "image_suggestion": "建议配品牌相关图片",
                "publish_time": "19:00-21:00",
                "category": content_type,
            })

        return {
            "content_type": content_type,
            "contents": contents,
        }

    def _default_content(self, content_type: str) -> dict:
        """默认回退内容"""
        if content_type == "朋友圈7天计划":
            return {
                "content_type": "朋友圈7天计划",
                "contents": [
                    {"day": 1, "title": "Day 1 | 行业趋势", "body": "📈 东南亚电商正在爆发！泰国、马来、印尼的市场增速都超过20%。但很多卖家还没意识到，收款渠道的优化直接影响利润。", "image_suggestion": "东南亚地图+增长数据", "publish_time": "12:00", "category": "行业趋势"},
                    {"day": 2, "title": "Day 2 | 痛点共鸣", "body": "💸 做跨境的朋友都懂：银行电汇手续费1.5%看起来不高，但加上汇率差、固定费、资金占用...实际成本远超想象。", "image_suggestion": "成本计算对比图", "publish_time": "19:00", "category": "痛点共鸣"},
                    {"day": 3, "title": "Day 3 | 产品价值", "body": "✨ Ksher 泰国本地收款：买家付泰铢，你收人民币。T+1到账，费率透明，还有泰国央行牌照保障。", "image_suggestion": "产品功能图", "publish_time": "19:00", "category": "产品价值"},
                    {"day": 4, "title": "Day 4 | 客户案例", "body": "👤 客户张总做泰国B2C，月流水5万美金。从银行电汇切换到 Ksher，一年省了3万多。最重要的是资金到账快了2天。", "image_suggestion": "客户案例截图", "publish_time": "19:00", "category": "客户案例"},
                    {"day": 5, "title": "Day 5 | 个人分享", "body": "💡 做了3年跨境支付顾问，最大的感受是：很多卖家只关注流量和选品，却忽略了收款这个利润黑洞。", "image_suggestion": "个人工作照", "publish_time": "20:00", "category": "个人分享"},
                    {"day": 6, "title": "Day 6 | 互动问答", "body": "❓ 问：跨境收款最重要的三个指标是什么？\n\n答：费率、到账速度、合规资质。你目前最看重哪个？评论区聊聊👇", "image_suggestion": "互动问答图", "publish_time": "19:00", "category": "互动问答"},
                    {"day": 7, "title": "Day 7 | 软性推广", "body": "🎁 这周分享了这么多东南亚收款干货，如果有朋友想具体了解自己能省多少，可以私聊我，免费帮你算笔账。", "image_suggestion": "联系方式图", "publish_time": "19:00", "category": "软性推广"},
                ],
            }
        else:
            return {
                "content_type": content_type,
                "contents": [{
                    "day": 1,
                    "title": f"{content_type}内容",
                    "body": "内容生成中，请稍后重试...",
                    "image_suggestion": "建议配品牌相关图片",
                    "publish_time": "19:00-21:00",
                    "category": content_type,
                }],
            }


if __name__ == "__main__":
    print("=" * 60)
    print("ContentAgent 模块测试")
    print("=" * 60)

    from services.knowledge_loader import KnowledgeLoader

    class MockLLM:
        def call_sync(self, agent_name, system, user_msg, temperature=0.8):
            return json.dumps({
                "content_type": "朋友圈7天计划",
                "contents": [
                    {"day": 1, "title": "Day 1 | 行业趋势", "body": "测试内容1", "image_suggestion": "图1", "publish_time": "12:00", "category": "行业趋势"},
                    {"day": 2, "title": "Day 2 | 痛点共鸣", "body": "测试内容2", "image_suggestion": "图2", "publish_time": "19:00", "category": "痛点共鸣"},
                ],
            })

    loader = KnowledgeLoader()
    agent = ContentAgent(MockLLM(), loader)

    ctx = {
        "content_type": "朋友圈7天计划",
        "target_audience": "泰国B2C跨境电商卖家",
        "industry": "b2c",
        "target_country": "thailand",
        "pain_points": ["手续费高", "到账慢"],
    }

    result = agent.generate(ctx)
    print(f"\n生成结果：")
    print(f"  content_type: {result['content_type']}")
    print(f"  contents: {len(result['contents'])} 条")
    for c in result["contents"]:
        print(f"    Day {c['day']}: {c['title']} ({c['category']})")
