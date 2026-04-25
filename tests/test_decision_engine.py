"""
决策引擎测试 — Week 5 验证

验证项：
1. 规则定义和添加
2. 规则评估和触发
3. LLM 辅助决策
4. 上下文收集
5. 决策历史记录
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.decision_engine import DecisionRule, DecisionResult, MarketingDecisionEngine, get_decision_engine


class TestDecisionRule:
    def test_create_rule(self):
        """测试创建决策规则"""
        rule = DecisionRule(
            rule_id="test_rule",
            name="测试规则",
            description="测试规则描述",
            condition=lambda ctx: ctx.get("test_value", 0) > 5,
            action="test_action",
            priority=10,
        )
        assert rule.rule_id == "test_rule"
        assert rule.name == "测试规则"
        assert rule.enabled is True
        assert rule.priority == 10


class TestMarketingDecisionEngine:
    def test_initialization(self):
        """测试初始化"""
        engine = MarketingDecisionEngine()
        assert len(engine.rules) > 0  # 应该有默认规则
        assert engine.llm_client is not None

    def test_add_rule(self):
        """测试添加规则"""
        engine = MarketingDecisionEngine()
        initial_count = len(engine.rules)

        new_rule = DecisionRule(
            rule_id="custom_rule",
            name="自定义规则",
            description="自定义规则描述",
            condition=lambda ctx: ctx.get("custom_key") is True,
            action="custom_action",
            priority=15,
        )
        engine.add_rule(new_rule)

        assert len(engine.rules) == initial_count + 1

    def test_evaluate_rules_empty_context(self):
        """测试空上下文评估"""
        engine = MarketingDecisionEngine()
        results = engine.evaluate_rules({})

        assert isinstance(results, list)
        assert len(engine.decision_history) == len(results)

    def test_evaluate_rules_approval_backlog(self):
        """测试审批队列积压规则"""
        engine = MarketingDecisionEngine()
        context = {
            "pending_approvals": [{"material_id": "1"}, {"material_id": "2"}, {"material_id": "3"}, {"material_id": "4"}],
        }

        results = engine.evaluate_rules(context)

        # 应该触发 approval_backlog 规则
        triggered = [r for r in results if r.rule_id == "approval_backlog"]
        assert len(triggered) > 0
        assert triggered[0].triggered is True
        assert triggered[0].suggested_action == "notify_approval_backlog"

    def test_evaluate_rules_content_gap(self):
        """测试内容空缺规则"""
        engine = MarketingDecisionEngine()
        context = {
            "content_gap_count": 3,
        }

        results = engine.evaluate_rules(context)

        triggered = [r for r in results if r.rule_id == "content_gap"]
        assert len(triggered) > 0
        assert triggered[0].suggested_action == "generate_urgent_content"

    def test_evaluate_rules_competitor_high_activity(self):
        """测试竞品高活跃规则"""
        engine = MarketingDecisionEngine()
        context = {
            "competitor_today_posts": 5,
        }

        results = engine.evaluate_rules(context)

        triggered = [r for r in results if r.rule_id == "competitor_high_activity"]
        assert len(triggered) > 0
        assert triggered[0].suggested_action == "generate_counter_content"

    def test_evaluate_rules_low_engagement(self):
        """测试低互动率规则"""
        engine = MarketingDecisionEngine()
        context = {
            "platform_performance": [
                {"platform": "wechat_moments", "engagement_rate": 1.5},
            ],
        }

        results = engine.evaluate_rules(context)

        triggered = [r for r in results if r.rule_id == "low_engagement"]
        assert len(triggered) > 0

    def test_collect_context(self):
        """测试收集上下文"""
        engine = MarketingDecisionEngine()
        context = engine.collect_context()

        assert "pending_approvals" in context
        assert "content_gap_count" in context
        assert "current_week" in context
        assert "collected_at" in context

    def test_get_decision_history(self):
        """测试获取决策历史"""
        engine = MarketingDecisionEngine()
        # 先执行一次评估
        engine.evaluate_rules({"content_gap_count": 2})

        history = engine.get_decision_history()

        assert isinstance(history, list)
        assert len(history) > 0
        assert "rule_id" in history[0]
        assert "suggested_action" in history[0]


class TestDecisionResult:
    def test_create_result(self):
        """测试创建决策结果"""
        result = DecisionResult(
            rule_id="test_rule",
            rule_name="测试规则",
            triggered=True,
            reason="测试原因",
            suggested_action="test_action",
            confidence=0.9,
        )

        assert result.rule_id == "test_rule"
        assert result.triggered is True
        assert result.confidence == 0.9
        assert "created_at" in result.__dict__


class TestGlobalDecisionEngine:
    def test_get_decision_engine_singleton(self):
        """测试全局决策引擎单例"""
        engine1 = get_decision_engine()
        engine2 = get_decision_engine()

        assert engine1 is engine2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
