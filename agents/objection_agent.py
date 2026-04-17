"""
ObjectionAgent — 异议处理教练 Agent

继承 BaseAgent，预判客户最可能提出的异议，
为每个异议提供 3 种回复策略（直接型/共情型/数据型）。

输出格式（INTERFACES.md）：
{
    "top_objections": [
        {
            "objection": str,
            "direct_response": str,
            "empathy_response": str,
            "data_response": str
        }
    ],
    "battlefield_tips": str
}
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, agent_register
from prompts.system_prompts import OBJECTION_AGENT_PROMPT
from prompts.knowledge_fusion_rules import KNOWLEDGE_FUSION_RULES
from config import BATTLEFIELD_TYPES, AGENT_TEMPERATURE
from orchestrator.battle_router import detect_battlefield


@agent_register("objection")
class ObjectionAgent(BaseAgent):
    """
    异议处理教练 Agent。

    根据战场类型和客户画像预判 Top 3 异议，
    每种异议提供直接型、共情型、数据型三种回复策略。
    """

    temperature = AGENT_TEMPERATURE["objection"]

    # 战场类型 → 常见异议映射
    BATTLEFIELD_OBJECTIONS = {
        "increment": [
            {
                "objection": "没听过 Ksher，安全吗？",
                "direct_response": "Ksher 持有泰国、马来西亚、印尼等多国央行支付牌照，资金安全由当地监管直接保障，和银行同一级别的合规标准。",
                "empathy_response": "您的谨慎非常专业，选择收款渠道确实需要审慎。Ksher 在东南亚运营多年，服务超过万家商户，资金安全零事故。",
                "data_response": "Ksher 持有泰国央行（Bank of Thailand）颁发的支付牌照，资金本地清算不经过第三方中转，每一笔交易都可追溯。",
            },
            {
                "objection": "换渠道太麻烦，现在用的银行也挺好的",
                "direct_response": "切换确实需要一些时间，但 Ksher 提供专人对接服务，从开户到上线通常只需要 3-5 个工作日，不影响正常收款。",
                "empathy_response": "完全理解，稳定的收款渠道对业务很重要。不过很多客户反馈，切换后第一个月就感受到了明显的成本下降和效率提升。",
                "data_response": "按您的月流水计算，继续使用银行每年多花 ¥{annual_saving:,.0f}。Ksher 的切换成本几乎为零，而收益从第一个月开始体现。",
            },
            {
                "objection": "费率看起来差不多，为什么要换？",
                "direct_response": "表面费率相近，但隐性成本差异很大：银行 T+3 到账产生资金占用成本，汇率差通常比 Ksher 高 0.5% 以上。",
                "empathy_response": "很多客户一开始也有同样的感受。但如果把汇率损失、资金占用、管理成本都算上，总成本差距会很明显。",
                "data_response": "综合计算：银行手续费 1.5% + 汇差 0.8% + T+3 资金占用成本，实际年化成本约 {current_total:,.0f} 元。Ksher 总成本仅 {ksher_total:,.0f} 元。",
            },
        ],
        "stock": [
            {
                "objection": "已经在用 PingPong/万里汇了，懒得换",
                "direct_response": "理解，但东南亚是 Ksher 的主场。我们在泰国有本地牌照，资金本地清算不用中转，到账快 1-2 天。",
                "empathy_response": "换渠道确实需要投入一些精力。不过如果现有渠道在东南亚的到账速度和汇率不是最优，每年可能多损失不少利润。",
                "data_response": "PingPong 东南亚无本地牌照，资金需中转。Ksher 本地清算 T+1 到账，汇率优 0.3%。按您的流水，年省 ¥{annual_saving:,.0f}。",
            },
            {
                "objection": "你们的费率和现在用的差不多",
                "direct_response": "表面费率可能接近，但汇率和到账速度的差异会直接影响实际收益。Ksher 的汇率对标中行零售牌价，通常更优。",
                "empathy_response": "费率确实是一个重要考量。建议您同时跑一段时间对比，看看实际到账金额和到账速度的差异。",
                "data_response": "除手续费外，汇差和到账时间也是关键成本。Ksher T+1 到账 vs 竞品 T+2，资金早一天到账就少一天占用成本。",
            },
            {
                "objection": "迁移账户会不会影响正在进行的收款？",
                "direct_response": "完全不会影响。Ksher 支持并行运行，您可以在不影响现有收款的情况下先开通测试，确认无误后再逐步切换。",
                "empathy_response": "这是每位客户都会关心的问题。我们设计了无缝迁移方案，新老渠道可以并行一段时间，确保业务零中断。",
                "data_response": "迁移过程采用双轨并行：原有渠道继续收款，Ksher 账户同步开通测试。确认稳定后再做 DNS/账户切换，零风险。",
            },
        ],
        "education": [
            {
                "objection": "不着急，先了解一下",
                "direct_response": "了解是第一步。不过跨境收款渠道的选择会影响您的定价策略和资金周转，越早优化利润空间越大。",
                "empathy_response": "先做功课是对的。选择收款渠道确实是跨境业务的重要基础设施，选对了后面省心很多。",
                "data_response": "很多新客户反馈，上线 Ksher 后第一个月就看到明显的到账速度提升。您可以先开个测试账户体验一下。",
            },
            {
                "objection": "我再对比看看其他渠道",
                "direct_response": "应该的。建议您从三个维度对比：费率透明度、到账速度、本地合规资质。这三项是 Ksher 的核心优势。",
                "empathy_response": "货比三家是明智的做法。我可以给您一份详细的对比资料，帮您从费率、速度、合规三个维度做客观评估。",
                "data_response": "这是各渠道在东南亚的对比：Ksher 本地牌照 + T+1 到账 + 透明费率。建议您重点考察对方是否有目标国的本地牌照。",
            },
            {
                "objection": "现在量还不大，觉得不需要",
                "direct_response": "量小的时候更要控制成本，因为每一笔的利润都很珍贵。而且提前布局好收款渠道，量起来后直接受益。",
                "empathy_response": "从小做起很聪明。不过提前了解收款成本结构，能帮助您在定价时留出更合理的利润空间。",
                "data_response": "即使月流水 1 万美元，银行 T+3 的资金占用成本每年也超过 2000 元。量小的时候成本占比反而更高。",
            },
        ],
    }

    def generate(self, context: dict) -> dict:
        """
        同步生成异议处理方案。

        Args:
            context: {
                "company": str,
                "industry": str,
                "target_country": str,
                "monthly_volume": float,
                "current_channel": str,
                "pain_points": [str],
                "battlefield": str,
                "cost_analysis": dict,      # 可选
            }

        Returns:
            dict: {"top_objections": [...], "battlefield_tips": str}
        """
        battlefield = context.get("battlefield")
        if not battlefield:
            battlefield = detect_battlefield(context.get("current_channel", ""))

        text = self._call_llm_sync(context)

        parsed = self._safe_parse_json(text)
        if parsed and self._validate_output(parsed):
            # 替换模板变量
            return self._inject_cost_data(parsed, context)

        # 回退到预设异议库
        return self._get_default_objections(battlefield, context)

    def build_system_prompt(self, knowledge: str) -> str:
        """构建 System Prompt"""
        prompt = OBJECTION_AGENT_PROMPT.replace(
            "{KNOWLEDGE_FUSION_RULES}", KNOWLEDGE_FUSION_RULES
        )
        prompt += f"\n\n## 知识库\n\n{knowledge[:2000]}"
        return prompt

    def build_user_message(self, context: dict) -> str:
        """构建 User Message"""
        battlefield = context.get("battlefield")
        if not battlefield:
            battlefield = detect_battlefield(context.get("current_channel", ""))

        bf_info = BATTLEFIELD_TYPES.get(battlefield, {})
        pain_points = context.get("pain_points", [])
        cost_analysis = context.get("cost_analysis", {})
        annual_saving = cost_analysis.get("annual_saving", 0)

        lines = [
            f"## 客户画像\n",
            self._build_context_summary(context),
            f"\n## 战场类型：{battlefield}",
            f"战场标签：{bf_info.get('label', '')}",
            f"异议重点：{bf_info.get('objection_focus', '')}",
        ]

        if annual_saving > 0:
            lines.append(f"\n## 成本数据参考")
            lines.append(f"切换到 Ksher 年省 ¥{annual_saving:,.0f}")

        lines.extend([
            f"\n## 输出要求",
            f"请预判客户最可能提出的 Top 3 异议，严格按 JSON 格式输出：",
            f"",
            f"```json",
            f"{{",
            f'  "top_objections": [',
            f'    {{',
            f'      "objection": "异议内容（30字以内）",',
            f'      "direct_response": "直接型回复：用数据和事实正面回应（50字以内）",',
            f'      "empathy_response": "共情型回复：先认同感受再引导，不用"但是"（50字以内）",',
            f'      "data_response": "数据型回复：引用具体费率/到账时间/牌照数据（50字以内）"',
            f'    }}',
            f'  ],',
            f'  "battlefield_tips": "针对 {battlefield} 战场的总体拜访策略（100字以内）"',
            f"}}",
            f"```",
            f"",
            f"回复原则：",
            f"- 每种回复 30-60 字，代理商能直接说出口",
            f"- 引用具体数据，不空谈",
            f"- 共情型回复不能有'但是'，用'同时''而且'替代",
        ])

        if pain_points:
            lines.append(f"- 结合客户痛点预判异议：{', '.join(pain_points)}")

        return "\n".join(lines)

    def _validate_output(self, parsed: dict) -> bool:
        """验证输出结构"""
        if "top_objections" not in parsed or not isinstance(parsed["top_objections"], list):
            return False
        if len(parsed["top_objections"]) < 1:
            return False
        required_keys = ["objection", "direct_response", "empathy_response", "data_response"]
        for obj in parsed["top_objections"]:
            if not all(k in obj for k in required_keys):
                return False
        return "battlefield_tips" in parsed

    def _inject_cost_data(self, parsed: dict, context: dict) -> dict:
        """将成本数据注入回复模板"""
        cost_analysis = context.get("cost_analysis", {})
        annual_saving = cost_analysis.get("annual_saving", 0)
        comparison_table = cost_analysis.get("comparison_table", {})
        ksher_total = comparison_table.get("ksher", {}).get("total", 0)
        current_total = comparison_table.get("current", {}).get("total", 0)

        for obj in parsed.get("top_objections", []):
            for key in ["direct_response", "empathy_response", "data_response"]:
                if key in obj and isinstance(obj[key], str):
                    obj[key] = obj[key].format(
                        annual_saving=annual_saving,
                        ksher_total=ksher_total,
                        current_total=current_total,
                    )

        return parsed

    def _get_default_objections(self, battlefield: str, context: dict) -> dict:
        """从预设库获取默认异议处理方案"""
        objections = self.BATTLEFIELD_OBJECTIONS.get(battlefield, self.BATTLEFIELD_OBJECTIONS["education"])

        # 深拷贝并注入成本数据
        cost_analysis = context.get("cost_analysis", {})
        annual_saving = cost_analysis.get("annual_saving", 0)
        comparison_table = cost_analysis.get("comparison_table", {})
        ksher_total = comparison_table.get("ksher", {}).get("total", 0)
        current_total = comparison_table.get("current", {}).get("total", 0)

        result_objections = []
        for obj in objections:
            result_objections.append({
                "objection": obj["objection"],
                "direct_response": obj["direct_response"].format(
                    annual_saving=annual_saving,
                    ksher_total=ksher_total,
                    current_total=current_total,
                ),
                "empathy_response": obj["empathy_response"].format(
                    annual_saving=annual_saving,
                    ksher_total=ksher_total,
                    current_total=current_total,
                ),
                "data_response": obj["data_response"].format(
                    annual_saving=annual_saving,
                    ksher_total=ksher_total,
                    current_total=current_total,
                ),
            })

        bf_info = BATTLEFIELD_TYPES.get(battlefield, {})
        tips = {
            "increment": "本次拜访核心策略：先算隐性成本账，让客户意识到'便宜'的银行其实不便宜，再给出 Ksher 的降维打击方案。",
            "stock": "本次拜访核心策略：不攻击竞品，强调 Ksher 在东南亚的'主场优势'——本地牌照带来的到账速度和汇率优势。",
            "education": "本次拜访核心策略：建立信任为主，不要急着推销。帮客户建立选择标准（牌照/速度/费率），让客户自己发现 Ksher 是最优解。",
        }

        return {
            "top_objections": result_objections,
            "battlefield_tips": tips.get(battlefield, tips["education"]),
        }


if __name__ == "__main__":
    print("=" * 60)
    print("ObjectionAgent 模块测试")
    print("=" * 60)

    from services.knowledge_loader import KnowledgeLoader

    class MockLLM:
        def call_sync(self, agent_name, system, user_msg, temperature=0.7):
            return json.dumps({
                "top_objections": [
                    {
                        "objection": "【测试】安全吗？",
                        "direct_response": "【测试】直接回复",
                        "empathy_response": "【测试】共情回复",
                        "data_response": "【测试】数据回复",
                    }
                ],
                "battlefield_tips": "【测试】战场策略",
            })

    loader = KnowledgeLoader()
    agent = ObjectionAgent(MockLLM(), loader)

    # 测试增量战场
    print("\n【增量战场】银行电汇客户")
    ctx1 = {
        "company": "测试公司",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 50000,
        "current_channel": "银行电汇",
        "pain_points": ["手续费高"],
        "cost_analysis": {
            "annual_saving": 34997.26,
            "comparison_table": {
                "ksher": {"total": 6698.63},
                "current": {"total": 41695.89},
            },
        },
    }
    result1 = agent.generate(ctx1)
    print(f"  异议数: {len(result1['top_objections'])}")
    print(f"  第一条异议: {result1['top_objections'][0]['objection']}")
    print(f"  战场策略: {result1['battlefield_tips'][:50]}...")

    # 测试存量战场（回退）
    print("\n【存量战场】PingPong 客户（回退测试）")
    ctx2 = {
        "industry": "b2b",
        "target_country": "malaysia",
        "monthly_volume": 200000,
        "current_channel": "PingPong",
        "pain_points": ["到账慢"],
    }
    result2 = agent.generate(ctx2)
    print(f"  异议数: {len(result2['top_objections'])}")
    print(f"  第一条异议: {result2['top_objections'][0]['objection']}")
    print(f"  战场策略: {result2['battlefield_tips'][:50]}...")

    # 测试教育战场（回退）
    print("\n【教育战场】未选定渠道客户（回退测试）")
    ctx3 = {
        "industry": "b2c",
        "target_country": "indonesia",
        "monthly_volume": 30000,
        "current_channel": "未选定",
        "pain_points": [],
    }
    result3 = agent.generate(ctx3)
    print(f"  异议数: {len(result3['top_objections'])}")
    print(f"  第一条异议: {result3['top_objections'][0]['objection']}")
