"""
KnowledgeAgent — 知识问答专家 Agent

继承 BaseAgent，帮助城市代理商回答跨境支付相关问题。
融合知识库 + 模型知识，确保"永远不会被客户问住"。

输出格式（INTERFACES.md）：
{
    "answer": str,
    "ksher_advantages": [str],
    "speech_tip": str,
    "sources": [str],
    "confidence": str
}
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, agent_register
from prompts.system_prompts import KNOWLEDGE_QA_PROMPT
from prompts.knowledge_fusion_rules import KNOWLEDGE_FUSION_RULES
from config import AGENT_TEMPERATURE


@agent_register("knowledge")
class KnowledgeAgent(BaseAgent):
    """
    知识问答专家 Agent。

    回答跨境支付相关问题，融合知识库数据和模型知识。
    输出包含：完整回答、Ksher 优势点、话术建议、信息来源、置信度。
    """

    temperature = AGENT_TEMPERATURE["knowledge"]

    # 置信度等级
    CONFIDENCE_LEVELS = {
        "high": "高（知识库有明确数据支持）",
        "medium": "中（基于行业常识推断）",
        "low": "低（建议联系 Ksher 内部确认）",
    }

    def generate(self, context: dict) -> dict:
        """
        同步生成知识问答。

        Args:
            context: {
                "question": str,            # 用户问题
                "industry": str,            # 行业（可选）
                "target_country": str,      # 目标国家（可选）
            }

        Returns:
            dict: {"answer", "ksher_advantages", "speech_tip", "sources", "confidence"}
        """
        text = self._call_llm_sync(context)

        parsed = self._safe_parse_json(text)
        if parsed and self._validate_output(parsed):
            return parsed

        return self._parse_text_response(text, context)

    def build_system_prompt(self, knowledge: str) -> str:
        """构建 System Prompt"""
        prompt = KNOWLEDGE_QA_PROMPT.replace(
            "{KNOWLEDGE_FUSION_RULES}", KNOWLEDGE_FUSION_RULES
        )
        prompt += f"\n\n## 知识库\n\n{knowledge[:2500]}"
        return prompt

    def build_user_message(self, context: dict) -> str:
        """构建 User Message"""
        question = context.get("question", "")
        industry = context.get("industry", "")
        target_country = context.get("target_country", "")

        lines = [
            f"## 客户问题",
            f"{question}",
        ]

        if industry or target_country:
            lines.append(f"\n## 客户背景")
            if industry:
                lines.append(f"行业：{industry}")
            if target_country:
                lines.append(f"目标国家：{target_country}")

        lines.extend([
            f"\n## 输出要求",
            f"请回答以上问题，严格按 JSON 格式输出：",
            f"",
            f"```json",
            f"{{",
            f'  "answer": "完整、连贯、专业的回答，自然融合知识库和模型知识",',
            f'  "ksher_advantages": ["可用于对客户说的优势点1", "优势点2", "优势点3"],',
            f'  "speech_tip": "代理商可以直接对客户说的一句话",',
            f'  "sources": ["知识库文档1", "行业数据2"],',
            f'  "confidence": "high|medium|low"',
            f"}}",
            f"```",
            f"",
            f"回答策略：",
            f"- 如果问题在知识库范围内：精准引用数据，补充行业背景",
            f"- 如果问题超出知识库：用行业知识专业回答，引导回 Ksher 优势",
            f"- 如果涉及具体 Ksher 数据但知识库中没有：回答'建议联系 Ksher 内部确认，但从行业角度来看...'",
            f"- confidence 标注：知识库有数据 → high，行业常识 → medium，需确认 → low",
        ])

        return "\n".join(lines)

    def _validate_output(self, parsed: dict) -> bool:
        """验证输出结构"""
        required = ["answer", "ksher_advantages", "speech_tip", "sources", "confidence"]
        return all(k in parsed for k in required)

    def _parse_text_response(self, text: str, context: dict) -> dict:
        """回退解析"""
        import re

        question = context.get("question", "")

        # 尝试提取各个部分
        answer = text.strip()

        # 尝试匹配回答
        answer_match = re.search(r'(?:回答|Answer).*?[\n:：](.+?)(?=\n##|\n### |相关|话术|来源|置信|\Z)', text, re.DOTALL | re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).strip()

        # 尝试匹配优势
        advantages = []
        adv_match = re.findall(r'(?:Ksher优势|优势).*?[\n•\-]\s*(.+?)(?=\n##|\n### |\Z)', text, re.DOTALL | re.IGNORECASE)
        if adv_match:
            advantages = [a.strip() for a in adv_match[:3]]

        # 尝试匹配话术建议
        speech_tip = ""
        tip_match = re.search(r'(?:话术建议|Speech Tip).*?[\n:：](.+?)(?=\n##|\n### |\Z)', text, re.DOTALL | re.IGNORECASE)
        if tip_match:
            speech_tip = tip_match.group(1).strip()

        # 尝试匹配来源
        sources = []
        src_match = re.findall(r'(?:来源|Sources).*?[\n•\-]\s*(.+?)(?=\n##|\n### |\Z)', text, re.DOTALL | re.IGNORECASE)
        if src_match:
            sources = [s.strip() for s in src_match[:3]]

        return {
            "answer": answer[:800] if answer else self._default_answer(question),
            "ksher_advantages": advantages if advantages else [
                "Ksher 持有东南亚多国本地支付牌照",
                "T+1 快速到账，资金效率高",
                "费率透明，综合成本低",
            ],
            "speech_tip": speech_tip if speech_tip else self._default_speech_tip(question),
            "sources": sources if sources else ["Ksher 产品资料", "行业公开数据"],
            "confidence": "medium",
        }

    def _default_answer(self, question: str) -> str:
        """默认回答"""
        return (
            f"关于「{question}」，从行业角度来看：\n\n"
            f"跨境收款涉及多个维度——费率结构、到账速度、合规资质、多平台管理能力。"
            f"Ksher 作为专注东南亚市场的本地收款平台，在这几个维度上都有明显优势。"
            f"具体细节建议您安排一次线上沟通，我可以根据您的业务模式做更精准的分析。"
        )

    def _default_speech_tip(self, question: str) -> str:
        """默认话术建议"""
        return f"您问的这个问题非常好，很多客户都有同样的关注。简单来说，Ksher 在东南亚本地收款这块，牌照、速度、费率三个维度都更有优势。"


if __name__ == "__main__":
    print("=" * 60)
    print("KnowledgeAgent 模块测试")
    print("=" * 60)

    from services.knowledge_loader import KnowledgeLoader

    class MockLLM:
        def call_sync(self, agent_name, system, user_msg, temperature=0.3):
            return json.dumps({
                "answer": "Ksher 在泰国持有央行颁发的支付牌照（Payment Service Provider License），资金安全由泰国银行直接监管。",
                "ksher_advantages": [
                    "持有泰国央行支付牌照，合规级别与银行同级",
                    "资金本地清算，不经过第三方中转",
                    "每笔交易可追溯，监管透明",
                ],
                "speech_tip": "您完全有理由关注资金安全，这是选择收款渠道的第一要素。Ksher 持有泰国央行颁发的支付牌照，和银行同一级别的合规标准。",
                "sources": ["Ksher 泰国牌照资质文件", "泰国央行官网公开信息"],
                "confidence": "high",
            })

    loader = KnowledgeLoader()
    agent = KnowledgeAgent(MockLLM(), loader)

    ctx = {
        "question": "Ksher 在泰国有没有支付牌照？资金安全怎么保障？",
        "industry": "b2c",
        "target_country": "thailand",
    }

    result = agent.generate(ctx)
    print(f"\n生成结果：")
    for k, v in result.items():
        if isinstance(v, list):
            print(f"  {k}:")
            for item in v:
                print(f"    - {item}")
        else:
            preview = str(v)[:80]
            print(f"  {k}: {preview}...")
