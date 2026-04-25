"""
决策引擎 — 基于规则和 LLM 辅助的自主决策

核心功能：
1. 规则决策：基于预定义规则触发行动（如竞品今日发帖>3条→触发反制内容生成）
2. LLM 辅助决策：分析趋势 → 生成行动建议
3. 决策记录：记录决策历史用于学习循环
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from services.llm_client import LLMClient
from services.material_service import (
    get_materials_by_lifecycle_state,
    get_materials_by_week,
    get_pending_approvals,
)

logger = logging.getLogger(__name__)


@dataclass
class DecisionRule:
    """决策规则定义"""
    rule_id: str
    name: str
    description: str
    condition: Callable[[Dict[str, Any]], bool]  # 判断条件
    action: str  # 触发动作
    priority: int = 0  # 优先级，数字越大越优先
    enabled: bool = True


@dataclass
class DecisionResult:
    """决策结果"""
    rule_id: str
    rule_name: str
    triggered: bool
    reason: str
    suggested_action: str
    confidence: float  # 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class MarketingDecisionEngine:
    """
    市场专员决策引擎。

    支持两种决策模式：
    1. 规则决策：基于预定义规则的自动触发
    2. LLM 辅助决策：基于上下文分析生成建议
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.rules: List[DecisionRule] = []
        self.decision_history: List[DecisionResult] = []
        self.llm_client = LLMClient()

        # 初始化默认规则
        self._init_default_rules()

    def _init_default_rules(self):
        """初始化默认决策规则"""
        self.rules = [
            # 规则1：审批队列积压超过3条 → 提醒加速审批
            DecisionRule(
                rule_id="approval_backlog",
                name="审批队列积压提醒",
                description="当待审批内容超过3条时，提醒加速审批",
                condition=lambda ctx: len(ctx.get("pending_approvals", [])) > 3,
                action="notify_approval_backlog",
                priority=10,
            ),
            # 规则2：本周内容空缺 → 触发紧急生成
            DecisionRule(
                rule_id="content_gap",
                name="内容空缺紧急生成",
                description="本周应发布但未生成的内容超过1条时，触发紧急生成",
                condition=lambda ctx: ctx.get("content_gap_count", 0) > 1,
                action="generate_urgent_content",
                priority=20,
            ),
            # 规则3：竞品今日发帖超过3条 → 触发反制内容生成
            DecisionRule(
                rule_id="competitor_high_activity",
                name="竞品高活跃反制",
                description="竞品今日发帖超过3条时，生成反制内容",
                condition=lambda ctx: ctx.get("competitor_today_posts", 0) > 3,
                action="generate_counter_content",
                priority=15,
            ),
            # 规则4：某平台 engagement_rate 低于阈值 → 建议调整策略
            DecisionRule(
                rule_id="low_engagement",
                name="低互动率提醒",
                description="某平台 engagement_rate 低于 2% 时，建议调整策略",
                condition=lambda ctx: any(
                    p.get("engagement_rate", 100) < 2.0
                    for p in ctx.get("platform_performance", [])
                ),
                action="suggest_strategy_adjustment",
                priority=8,
            ),
            # 规则5：周五前未完成下周计划 → 触发规划提醒
            DecisionRule(
                rule_id="weekly_plan_missing",
                name="周计划缺失提醒",
                description="周五前未完成下周内容规划时触发",
                condition=lambda ctx: ctx.get("is_before_friday", False) and not ctx.get(
                    "next_week_planned", False
                ),
                action="remind_weekly_planning",
                priority=12,
            ),
        ]

    def add_rule(self, rule: DecisionRule):
        """添加新规则"""
        self.rules.append(rule)
        # 按优先级排序
        self.rules.sort(key=lambda r: -r.priority)

    def evaluate_rules(
        self, context: Dict[str, Any]
    ) -> List[DecisionResult]:
        """
        评估所有规则，返回触发的决策。

        Args:
            context: 决策上下文，包含 pending_approvals, content_gap_count 等

        Returns:
            触发的决策列表
        """
        results = []
        for rule in self.rules:
            if not rule.enabled:
                continue

            try:
                triggered = rule.condition(context)
                if triggered:
                    result = DecisionResult(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        triggered=True,
                        reason=f"规则「{rule.name}」条件满足",
                        suggested_action=rule.action,
                        confidence=0.9,  # 规则决策置信度固定为0.9
                        metadata={"rule_description": rule.description},
                    )
                    results.append(result)
                    logger.info(
                        f"[DecisionEngine] 规则触发: {rule.name} → {rule.action}"
                    )
            except Exception as e:
                logger.warning(
                    f"[DecisionEngine] 规则 {rule.rule_id} 执行失败: {e}"
                )

        self.decision_history.extend(results)
        return results

    async def llm_assisted_decision(
        self, scenario: str, context: Dict[str, Any]
    ) -> DecisionResult:
        """
        LLM 辅助决策：分析场景 → 生成行动建议。

        Args:
            scenario: 决策场景描述
            context: 相关上下文

        Returns:
            决策结果
        """
        prompt = f"""
你是一位资深市场运营专家。请分析以下场景，给出决策建议。

## 场景描述
{scenario}

## 上下文数据
{json.dumps(context, ensure_ascii=False, indent=2)}

## 请按以下格式输出：
```json
{{
  "analysis": "对场景的分析",
  "suggested_action": "建议采取的行动（简洁）",
  "reason": "行动理由",
  "confidence": 0.0-1.0,
  "risk_level": "low|medium|high"
}}
```
"""

        try:
            response = await self.llm_client.achat(
                messages=[{"role": "user", "content": prompt}],
                model="kimi",
                temperature=0.3,
            )

            # 解析 LLM 返回的 JSON
            content = response.get("choices", [{}])[0].get("message", {}).get(
                "content", ""
            )
            # 提取 JSON 部分
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                llm_result = json.loads(content[start:end])
            else:
                raise ValueError("未找到有效 JSON")

            result = DecisionResult(
                rule_id="llm_assisted",
                rule_name="LLM 辅助决策",
                triggered=True,
                reason=llm_result.get("analysis", ""),
                suggested_action=llm_result.get("suggested_action", ""),
                confidence=llm_result.get("confidence", 0.7),
                metadata={
                    "scenario": scenario,
                    "risk_level": llm_result.get("risk_level", "medium"),
                    "llm_raw": content,
                },
            )

            self.decision_history.append(result)
            logger.info(
                f"[DecisionEngine] LLM 决策: {result.suggested_action} (confidence={result.confidence})"
            )
            return result

        except Exception as e:
            logger.error(f"[DecisionEngine] LLM 辅助决策失败: {e}")
            # 返回失败结果
            return DecisionResult(
                rule_id="llm_failed",
                rule_name="LLM 决策失败",
                triggered=False,
                reason=f"LLM 决策失败: {e}",
                suggested_action="manual_review",
                confidence=0.0,
            )

    def collect_context(self) -> Dict[str, Any]:
        """
        收集当前决策上下文。

        Returns:
            包含 pending_approvals, content_gap_count 等的上下文字典
        """
        # 获取待审批内容
        pending_approvals = get_pending_approvals(limit=50)

        # 获取当前周的内容
        year, week = self._get_current_week()
        week_materials = get_materials_by_week(year, week)
        content_gap_count = 5 - len(week_materials)  # 假设每周5天内容

        # 判断是否是周五前
        from datetime import date

        today = date.today()
        is_before_friday = today.weekday() < 4  # 0-4 是周一到周五

        # 获取下一周是否已规划
        next_year, next_week = self._get_next_week()
        next_week_materials = get_materials_by_week(next_year, next_week)
        next_week_planned = len(next_week_materials) > 0

        return {
            "pending_approvals": pending_approvals,
            "content_gap_count": max(0, content_gap_count),
            "is_before_friday": is_before_friday,
            "next_week_planned": next_week_planned,
            "current_week": f"{year}-W{week:02d}",
            "collected_at": datetime.now().isoformat(),
        }

    async def daily_decision_cycle(self) -> Dict[str, Any]:
        """
        执行日度决策周期。

        Returns:
            决策结果汇总
        """
        context = self.collect_context()
        rule_decisions = self.evaluate_rules(context)

        # 如果没有规则触发，可以尝试 LLM 辅助决策
        llm_decision = None
        if not rule_decisions and context.get("content_gap_count", 0) > 0:
            scenario = f"本周内容空缺 {context['content_gap_count']} 条，需要补充内容"
            llm_decision = await self.llm_assisted_decision(scenario, context)

        return {
            "context": context,
            "rule_decisions": [
                {
                    "rule_id": d.rule_id,
                    "rule_name": d.rule_name,
                    "suggested_action": d.suggested_action,
                    "confidence": d.confidence,
                }
                for d in rule_decisions
            ],
            "llm_decision": (
                {
                    "suggested_action": llm_decision.suggested_action,
                    "confidence": llm_decision.confidence,
                    "reason": llm_decision.reason,
                }
                if llm_decision
                else None
            ),
            "total_decisions": len(rule_decisions) + (1 if llm_decision else 0),
        }

    def _get_current_week(self) -> tuple[int, int]:
        """获取当前年份和周数"""
        from datetime import datetime

        now = datetime.now()
        iso = now.isocalendar()
        return iso.year, iso.week

    def _get_next_week(self) -> tuple[int, int]:
        """获取下一周的年份和周数"""
        year, week = self._get_current_week()
        if week == 52 or (week == 53 and year % 4 != 0):  # 处理跨年
            return year + 1, 1
        return year, week + 1

    def get_decision_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取决策历史"""
        return [
            {
                "rule_id": d.rule_id,
                "rule_name": d.rule_name,
                "triggered": d.triggered,
                "suggested_action": d.suggested_action,
                "confidence": d.confidence,
                "created_at": d.created_at,
            }
            for d in self.decision_history[-limit:]
        ]


# 全局决策引擎实例
_global_decision_engine: Optional[MarketingDecisionEngine] = None


def get_decision_engine() -> MarketingDecisionEngine:
    """获取全局决策引擎实例（单例）"""
    global _global_decision_engine
    if _global_decision_engine is None:
        _global_decision_engine = MarketingDecisionEngine()
    return _global_decision_engine
