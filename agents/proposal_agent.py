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
        # ── 第一次调用 ──
        text = self._call_llm_sync(context)

        # 尝试 1：直接解析 JSON
        parsed = self._safe_parse_json(text)
        if parsed and self._validate_output(parsed):
            return parsed

        # 尝试 2：修复值内部未转义的 ASCII 双引号（LLM 常在中文文本中用 "引号" 导致 JSON 语法错误）
        repaired_text = self._repair_json_quotes(text)
        if repaired_text != text:
            parsed2 = self._safe_parse_json(repaired_text)
            if parsed2 and self._validate_output(parsed2):
                return parsed2

        # 尝试 3：回退解析第一次输出
        result = self._parse_text_response(text, context)
        if self._result_quality_ok(result):
            return result

        # ── 重试：追加更强提醒 ──
        knowledge = self.knowledge_loader.load(self.agent_name, context)
        system = self.build_system_prompt(knowledge)
        user_msg = self.build_user_message(context)
        user_msg += (
            "\n\n⚠️ 紧急提醒：上面的 JSON 中各字段的值只是写作指导说明，"
            "不是实际内容。你必须用自己的分析生成 200 字以上的中文段落，"
            "替换掉这些指导文字。不要重复\"此处应写...\"之类的示例文字。"
        )
        text2 = self.llm_client.call_sync(
            agent_name=self.agent_name,
            system=system,
            user_msg=user_msg,
            temperature=self.temperature,
        )

        # 第二次：直接解析
        parsed3 = self._safe_parse_json(text2)
        if parsed3 and self._validate_output(parsed3):
            return parsed3

        # 第二次引号修复
        repaired_text2 = self._repair_json_quotes(text2)
        if repaired_text2 != text2:
            parsed4 = self._safe_parse_json(repaired_text2)
            if parsed4 and self._validate_output(parsed4):
                return parsed4

        # 第二次回退解析
        result2 = self._parse_text_response(text2, context)
        if self._result_quality_ok(result2):
            return result2

        # 两次都失败，挑更好的
        return self._pick_better_result(result, result2)

    def _repair_json_quotes(self, text: str) -> str:
        """
        修复 JSON 值内部未转义的 ASCII 双引号。
        LLM 生成中文内容时常用 "引号" 标出词汇，导致 JSON 语法破裂。
        先用 _safe_parse_json 知道失败后调用此方法。
        """
        import re

        # 提取 markdown JSON 代码块
        match = re.search(
            r'```(?:json)?\s*\n?(.*?)\n?```',
            text, re.DOTALL
        )
        if not match:
            return text

        content = match.group(1)

        def _fix_line(line: str) -> str:
            # 匹配每行的 "key": "value" 或 "key": "value",
            m = re.match(r'^(\s*"[^"]+":\s*")(.*?)"(,?)$', line)
            if m:
                prefix, value, comma = m.groups()
                value = value.replace('"', r'\"')
                return prefix + value + '"' + (comma or '')
            return line

        lines = content.split('\n')
        repaired = '\n'.join(_fix_line(l) for l in lines)
        if repaired != content:
            return text.replace(content, repaired)
        return text

    def build_system_prompt(self, knowledge: str) -> str:
        """构建 System Prompt — 清理所有未解析占位符的版本。"""
        # 将知识库注入融合规则，避免 {knowledge_text} 留在 prompt 中
        rules = KNOWLEDGE_FUSION_RULES.replace("{knowledge_text}", knowledge[:2000])

        system = f"""你是 Ksher 跨境支付的高级解决方案顾问。任务：为客户生成专业的跨境收款定制方案。

{rules}

- 你有 10 年跨境支付行业经验
- 你熟悉东南亚各国的监管政策和市场环境
- 你擅长用商业语言打动 CEO 级别的决策者

## 写作标准
- 像写给 CEO 看的商业提案，不像产品手册
- 每个章节是一段完整的分析段落，至少 200 字（约 200 个中文字符）
- 引用真实数据（费率/到账时间/牌照），增加可信度
- 深度分析：每个章节要有分析、有洞察、有逻辑递进
- 不要只列 bullet point——要像写商业报告一样展开论述

## ⚠️ 输出强制要求（最高优先级，不可忽略）
- 你必须输出完整、合法的 JSON 对象，严格按 User Message 中指定的 8 个字段键名
- 输出中不要有任何 JSON 格式以外的说明文字
- 每个字段的值是一段中文长文本段落（至少 200 字）
- 如果内容短于 200 字，系统会判定为不合格，必须重写
- 不要使用示例中的指导文字作为实际输出内容（如"此处应写..."），必须替换为真实分析
"""
        return system

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
            f"注意：JSON 字符串值中不能包含英文双引号符号，否则会导致 JSON 语法错误。如果需要在文本中标出某个词，请使用中文引号或直接描述，不要使用 ASCII 双引号。",
            f"",
            f"```json",
            f"{{",
            f'  "industry_insight": "此处应写一段至少 200 字的行业洞察分析。包括：(1) 行业规模与增长趋势——引用权威数据说明市场有多大、增速如何；(2) 竞争格局变化——主要市场参与者、消费者行为变化、政策环境影响；(3) 跨境收款的核心挑战——为什么传统方案已无法满足该行业的发展需求；以及对客户意味着什么——这些趋势如何影响客户的利润空间和竞争力。不要只列数字，要有逻辑递进和深度洞察。",',
            f'  "pain_diagnosis": "此处应写一段至少 200 字的痛点诊断。不要只说手续费高，要具体到三个层次：第一，显性成本具体是多少——当前渠道的费率结构如何构成，每月固定费用和比例费用分别是多少；第二，隐性成本有哪些——汇率损失、资金占用时间、多平台管理的人工成本；第三，业务影响是什么——这些成本如何拖累客户的备货能力、定价竞争力和资金周转效率。每个痛点都要有数据和逻辑链条。",',
            f'  "solution": "此处应写一段至少 200 字的解决方案描述。不是简单地列出产品功能，而是针对上述每个痛点给出完整的解决方案逻辑：针对手续费高的痛点——Ksher 的费率结构和节省方式是什么，具体能降低多少百分比；针对汇率损失的痛点——Ksher 采用的汇率机制和与国际市价的对比优势；针对到账慢的问题——T+1 到账如何释放资金占用成本、提高资金周转率；针对多平台管理问题——一站式收款如何降低人力成本。每个解决方案都要有量化价值和业务逻辑支撑。",',
            f'  "product_recommendation": "此处应写一段至少 200 字的产品推荐。基于客户的目标国家和业务类型，推荐最适合的 Ksher 产品组合。包括：(1) 主推产品——为什么这个产品最匹配客户的业务场景，具体有哪些功能；(2) 辅助产品——还可以搭配哪些增值服务，如多币种账户、自动结算、API 对接等；(3) 与竞品对比——为什么 Ksher 的产品在该市场上具有差异化优势；(4) 客户收益预期——使用这些产品后预计能达到什么效果。",',
            f'  "fee_advantage": "此处应写一段至少 200 字的费率优势分析。引用 CostAgent 提供的具体成本数据：年度总成本对比、各项成本的明细拆解（手续费、汇率损失、资金时间成本、多平台管理成本、合规风险成本），以及切换到 Ksher 后的节省金额和节省比例。不要只罗列表格数字，要解释这些节省对客户业务的实际意义——省下的钱可以用来做什么，如何转为客户的核心竞争力。",',
            f'  "compliance": "此处应写一段至少 200 字的合规保障说明。详细介绍 Ksher 在目标国家的合规资质：持有哪些监管机构颁发的牌照、牌照类型和覆盖范围、监管框架下的资金安全保障机制、合规审计和风控体系。同时说明合规对客户的价值：降低交易冻结风险、满足跨境收付的法规要求、避免无资质服务商的潜在损失。用客户能理解的商业语言，不要变成法律条文罗列。",',
            f'  "onboarding_flow": "此处应写一段至少 200 字的接入流程说明。详细描述从签约到成功收款的完整流程：(1) 申请阶段——需要提交哪些资料、资料准备周期是多久；(2) 审核阶段——Ksher 合规团队的审核流程和时间承诺；(3) 技术对接——是否需要技术人员参与、集成方式有哪些选择；(4) 测试上线——测试环境验证、首笔收款确认；(5) 后续支持——专属客户经理的持续服务机制。让客户感到门槛低、流程清晰、有专人支持。",',
            f'  "next_steps": "此处应写一段至少 200 字的下一步行动方案。给出三个明确可执行的行动步骤，每个步骤都包含：(1) 具体做什么——安排 30 分钟线上沟通而不是我们开始吧；(2) 何时完成——给出明确的时间框架；(3) 谁来负责——说明 Ksher 会提供哪些支持资源；(4) 预期产出——这步完成后能达到什么效果。整体语气要积极但不催促，让客户感受到是在帮助他们做出更好的决策，而不是推销压力。"',
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
        """验证输出是否包含所有必需字段，且每个字段足够长"""
        required = [
            "industry_insight", "pain_diagnosis", "solution",
            "product_recommendation", "fee_advantage", "compliance",
            "onboarding_flow", "next_steps",
        ]
        if not all(k in parsed and parsed[k] for k in required):
            return False
        # 每个字段至少 150 字（留出 margin，低于 150 视为 LLM 未充分展开）
        MIN_LENGTH = 150
        for key in required:
            if len(str(parsed[key])) < MIN_LENGTH:
                return False
        return True

    def _parse_text_response(self, text: str, context: dict) -> dict:
        """回退解析：优先提取 markdown 代码块中的 JSON，其次按章节标题提取"""
        import re

        result = {key: "" for key in [
            "industry_insight", "pain_diagnosis", "solution",
            "product_recommendation", "fee_advantage", "compliance",
            "onboarding_flow", "next_steps",
        ]}

        # 1. 优先尝试提取 markdown 代码块中的 JSON
        json_block_match = re.search(
            r'```(?:json)?\s*\n?(.*?)\n?```',
            text, re.DOTALL
        )
        if json_block_match:
            try:
                parsed = json.loads(json_block_match.group(1).strip())
                for key in result:
                    if key in parsed and parsed[key]:
                        result[key] = str(parsed[key]).strip()
                # 若提取到 ≥5 个字段则认为成功
                if sum(1 for v in result.values() if v) >= 5:
                    return self._fill_defaults(result, context)
            except (json.JSONDecodeError, TypeError):
                pass  # 回退到章节标题提取

        # 2. 章节标题映射（JSON 解析失败时使用）
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

    def _result_quality_ok(self, result: dict) -> bool:
        """
        判断回退解析的结果质量是否可接受。
        要求至少 6/8 个字段非空且每个字段 ≥80 字。
        """
        required = [
            "industry_insight", "pain_diagnosis", "solution",
            "product_recommendation", "fee_advantage", "compliance",
            "onboarding_flow", "next_steps",
        ]
        ok_count = sum(
            1 for k in required
            if result.get(k) and len(str(result[k])) >= 80
        )
        return ok_count >= 6

    def _pick_better_result(self, result_a: dict, result_b: dict) -> dict:
        """
        比较两次回退解析结果，返回质量更好的那个。
        如果两个都不够好，依然返回其中更好的一个（减少全默认值概率）。
        """
        required = [
            "industry_insight", "pain_diagnosis", "solution",
            "product_recommendation", "fee_advantage", "compliance",
            "onboarding_flow", "next_steps",
        ]

        def score(r: dict) -> int:
            return sum(
                len(str(r.get(k, "")))
                for k in required
            )

        return result_b if score(result_b) > score(result_a) else result_a


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
