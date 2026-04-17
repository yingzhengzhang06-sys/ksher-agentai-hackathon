"""
SpeechAgent — 销售话术生成 Agent

继承 BaseAgent，根据客户画像和战场类型生成定制化销售话术。
输出格式（INTERFACES.md）：
{
    "elevator_pitch": str,      # 30秒电梯话术
    "full_talk": str,           # 3分钟完整讲解（分3段）
    "wechat_followup": str,     # 微信跟进话术（首次添加+后续）
    "battlefield": str          # 战场类型（increment/stock/education）
}
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, agent_register
from prompts.system_prompts import SPEECH_AGENT_PROMPT
from prompts.knowledge_fusion_rules import KNOWLEDGE_FUSION_RULES
from config import BATTLEFIELD_TYPES, AGENT_TEMPERATURE
from orchestrator.battle_router import detect_battlefield
import re


@agent_register("speech")
class SpeechAgent(BaseAgent):
    """
    销售话术生成 Agent。

    根据客户画像（行业/国家/渠道/痛点）和战场类型，
    生成 30 秒电梯话术、3 分钟完整讲解、微信跟进话术。
    """

    temperature = AGENT_TEMPERATURE["speech"]

    def generate(self, context: dict) -> dict:
        """
        同步生成销售话术。

        Args:
            context: {
                "company": str,
                "industry": str,        # "b2c" | "b2b" | "service"
                "target_country": str,
                "monthly_volume": float,
                "current_channel": str,
                "pain_points": [str],
                "battlefield": str,     # "increment" | "stock" | "education"
            }

        Returns:
            dict: {"elevator_pitch", "full_talk", "wechat_followup", "battlefield"}
        """
        # 获取战场类型（如果上下文未提供则自动检测）
        battlefield = context.get("battlefield")
        if not battlefield:
            battlefield = detect_battlefield(context.get("current_channel", ""))

        # 调用 LLM 生成话术
        text = self._call_llm_sync(context)

        # 尝试解析 JSON 输出
        parsed = self._safe_parse_json(text)
        if parsed and all(k in parsed for k in ("elevator_pitch", "full_talk", "wechat_followup")):
            parsed["battlefield"] = battlefield
            return parsed

        # 解析失败：回退到文本分块解析
        return self._parse_text_response(text, battlefield)

    def build_system_prompt(self, knowledge: str) -> str:
        """构建 System Prompt（注入知识库和战场策略）"""
        # 使用 replace() 仅替换 KNOWLEDGE_FUSION_RULES，保留模板中的其他占位符
        # 由 build_user_message() 注入动态字段（战场类型、客户画像等）
        prompt = SPEECH_AGENT_PROMPT.replace(
            "{KNOWLEDGE_FUSION_RULES}", KNOWLEDGE_FUSION_RULES
        )
        # 追加知识库内容
        prompt += f"\n\n## 知识库\n\n{knowledge[:2000]}"
        return prompt

    def build_user_message(self, context: dict) -> str:
        """构建 User Message（客户上下文 + 战场类型）"""
        battlefield = context.get("battlefield")
        if not battlefield:
            battlefield = detect_battlefield(context.get("current_channel", ""))

        bf_info = BATTLEFIELD_TYPES.get(battlefield, {})

        lines = [
            f"## 客户画像\n",
            self._build_context_summary(context),
            f"\n## 战场类型：{battlefield}",
            f"战场标签：{bf_info.get('label', '')}",
            f"话术重点：{bf_info.get('speech_focus', '')}",
            f"\n## 输出要求",
            f"请生成以下话术内容，严格按 JSON 格式输出：",
            f"",
            f"```json",
            f"{{",
            f'  "elevator_pitch": "30秒电梯话术，用于破冰",',
            f'  "full_talk": "3分钟完整讲解，分3段：切痛点→给方案→促行动",',
            f'  "wechat_followup": "微信跟进话术：首次添加+后续跟进",',
            f'  "battlefield": "{battlefield}"',
            f"}}",
            f"```",
            f"",
            f"注意：",
            f"- 话术要贴合客户的具体痛点（{', '.join(context.get('pain_points', []))}）",
            f"- 用客户能听懂的语言，避免过多专业术语",
            f"- 每段话术后要有明确的下一步行动建议",
        ]
        return "\n".join(lines)

    def _parse_text_response(self, text: str, battlefield: str) -> dict:
        """
        当 LLM 没有返回标准 JSON 时的回退解析。
        按标题分块提取内容。
        """
        result = {
            "elevator_pitch": "",
            "full_talk": "",
            "wechat_followup": "",
            "battlefield": battlefield,
        }

        # 尝试匹配各个部分
        patterns = {
            "elevator_pitch": r"(?:30秒电梯话术|电梯话术| Elevator Pitch).*?[\n:：](.+?)(?=\n##|\n### |\Z)",
            "full_talk": r"(?:3分钟完整讲解|完整讲解|Full Talk).*?[\n:：](.+?)(?=\n##|\n### |\Z)",
            "wechat_followup": r"(?:微信跟进话术|跟进话术|WeChat).*?[\n:：](.+?)(?=\n##|\n### |\Z)",
        }

        for key, pattern in patterns.items():
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                result[key] = matches[0].strip()

        # 如果某部分为空，填入默认内容
        if not result["elevator_pitch"]:
            result["elevator_pitch"] = self._default_elevator_pitch(battlefield)
        if not result["full_talk"]:
            result["full_talk"] = self._default_full_talk(battlefield)
        if not result["wechat_followup"]:
            result["wechat_followup"] = self._default_wechat_followup(battlefield)

        return result

    def _default_elevator_pitch(self, battlefield: str) -> str:
        """默认电梯话术（回退用）"""
        defaults = {
            "increment": "很多做跨境的同行都以为银行是最安全的选择，但其实银行在跨境收款上的隐性成本很高——汇率差、到账慢、还有每笔固定手续费。Ksher 是专注东南亚的本地收款平台，费率比银行低，到账快，而且我们有当地央行的支付牌照。",
            "stock": "您现在用的渠道在东南亚可能不是最优解。Ksher 和它们的区别很简单——我们在泰国有本地牌照，资金不用中转，到账更快、汇率更优。同样的流水，一年能省不少。",
            "education": "如果您正在选跨境收款渠道，有3个关键点需要注意：手续费高、到账慢、合规风险。Ksher 专注东南亚本地收款，帮您把这三项成本都降下来。",
        }
        return defaults.get(battlefield, defaults["education"])

    def _default_full_talk(self, battlefield: str) -> str:
        """默认完整讲解（回退用）"""
        defaults = {
            "increment": "【第1分钟·切痛点】您现在用银行电汇收款，每个月除了明面上的手续费，还有汇率损失和资金占用成本。银行 T+3 到账，意味着您的资金有3天是被锁住的。\n\n【第2分钟·给方案】Ksher 是 T+1 到账，费率比银行低将近一半。我们有泰国央行的支付牌照，资金安全有保障。\n\n【第3分钟·促行动】我可以帮您算一笔具体的账，看看一年能省多少。您方便的话，我们约个 15 分钟线上会议？",
            "stock": "【第1分钟·切痛点】您在用的渠道虽然也能收款，但东南亚这块不是他们的强项。资金要中转，到账慢，汇率也不够优。\n\n【第2分钟·给方案】Ksher 在泰国有本地牌照，资金本地清算，不用中转。同样一笔款，我们能快 1-2 天到账，汇率也更优。\n\n【第3分钟·促行动】切换很简单，我们有专人对接。您可以先开一个测试账户，体验下到账速度。",
            "education": "【第1分钟·切痛点】很多刚开始做跨境的商家，选收款渠道时只看手续费率，忽略了汇率损失和到账时间。这三项加起来，才是真正的成本。\n\n【第2分钟·给方案】Ksher 专注东南亚市场，泰国、马来、印尼都有本地牌照。我们的费率透明，汇率优，T+1 到账。\n\n【第3分钟·促行动】我可以给您发一份详细的费率对比表，您参考一下。需要的话我们可以安排一次线上沟通。",
        }
        return defaults.get(battlefield, defaults["education"])

    def _default_wechat_followup(self, battlefield: str) -> str:
        """默认微信跟进话术（回退用）"""
        defaults = {
            "increment": "【首次添加】XX 总您好，我是 Ksher 的代理商小王。刚才聊到的跨境收款成本问题，我整理了一份对比表，您有空可以看看。\n\n【后续跟进】XX 总，上次提到的银行隐性成本，我帮您算了一下——按您现在的月流水，一年大概能多花 XX 万。用 Ksher 可以省下来。",
            "stock": "【首次添加】XX 总您好，我是 Ksher 的代理商小李。东南亚收款这块，我们有本地牌照的优势，到账速度和汇率都比中转渠道更优。\n\n【后续跟进】XX 总，切换渠道其实比想象中简单。我们可以先开一个测试账户，您体验下到账速度再决定。",
            "education": "【首次添加】XX 总您好，我是 Ksher 的代理商小张。如果您正在了解跨境收款方案，我可以帮您对比各渠道的费率、到账时间和合规情况。\n\n【后续跟进】XX 总，我整理了一份东南亚跨境收款指南，发给您参考。有任何问题随时问我。",
        }
        return defaults.get(battlefield, defaults["education"])


if __name__ == "__main__":
    print("=" * 60)
    print("SpeechAgent 模块测试")
    print("=" * 60)

    # 模拟测试（无需 LLM）
    from services.knowledge_loader import KnowledgeLoader

    class MockLLM:
        def call_sync(self, agent_name, system, user_msg, temperature=0.7):
            return json.dumps({
                "elevator_pitch": "【测试】30秒电梯话术",
                "full_talk": "【测试】3分钟完整讲解",
                "wechat_followup": "【测试】微信跟进话术",
                "battlefield": "increment",
            })

    loader = KnowledgeLoader()
    agent = SpeechAgent(MockLLM(), loader)

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
    for k, v in result.items():
        print(f"  {k}: {v[:60]}...")
