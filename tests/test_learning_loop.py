"""
学习闭环测试 — Week 5 验证

验证项：
1. 学习循环初始化
2. 模式加载和保存
3. 学习模式格式化
4. 洞察格式化
5. 学习摘要获取
6. 全局单例
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.learning_loop import LearningLoop, LearningRecord, get_learning_loop


class TestLearningRecord:
    def test_create_record(self):
        """测试创建学习记录"""
        record = LearningRecord(
            cycle_id="test_cycle",
            start_date="2026-04-15T00:00:00",
            end_date="2026-04-21T23:59:59",
            total_contents_analyzed=10,
            insights_count=3,
            patterns_learned=[{"type": "platform", "value": "wechat"}],
            prompt_updates=["注入学习模式"],
        )

        assert record.cycle_id == "test_cycle"
        assert record.total_contents_analyzed == 10
        assert len(record.patterns_learned) == 1


class TestLearningLoop:
    @pytest.fixture
    def temp_patterns_file(self, tmp_path):
        """临时模式文件 fixture"""
        patterns_file = tmp_path / "learned_patterns.json"
        return patterns_file

    def test_initialization(self):
        """测试初始化"""
        loop = LearningLoop()
        assert loop.config is not None
        assert loop.analyzer is not None

    def test_format_patterns_for_prompt_empty(self):
        """测试空模式格式化"""
        loop = LearningLoop()
        result = loop._format_patterns_for_prompt([])

        assert "暂无学习到的高绩效模式" in result

    def test_format_patterns_for_prompt_with_data(self):
        """测试有数据模式格式化"""
        loop = LearningLoop()
        patterns = [
            {
                "type": "platform",
                "value": "wechat_moments",
                "description": "高绩效内容多发布在微信朋友圈",
                "frequency": 0.8,
            },
            {
                "type": "theme",
                "value": "行业趋势",
                "description": "主题「行业趋势」表现较好",
                "frequency": 0.6,
            },
        ]

        result = loop._format_patterns_for_prompt(patterns)

        assert "基于历史数据学习到的高绩效内容模式" in result
        assert "微信朋友圈" in result
        assert "行业趋势" in result

    def test_format_insights_for_prompt_empty(self):
        """测试空洞察格式化"""
        loop = LearningLoop()
        result = loop._format_insights_for_prompt([])

        assert result == ""

    def test_format_insights_for_prompt_with_data(self):
        """测试有数据洞察格式化"""
        loop = LearningLoop()

        class MockInsight:
            description = "内容性能呈上升趋势"

        insights = [MockInsight()]

        result = loop._format_insights_for_prompt(insights)

        assert "内容性能洞察" in result
        assert "内容性能呈上升趋势" in result

    def test_generate_cycle_id(self):
        """测试生成循环 ID"""
        loop = LearningLoop()
        cycle_id = loop._generate_cycle_id()

        assert cycle_id.startswith("learning_cycle_")

    def test_get_current_patterns_empty(self):
        """测试获取当前模式（无历史）"""
        loop = LearningLoop()
        patterns = loop.get_current_patterns()

        assert "暂无学习到的高绩效模式" in patterns

    def test_get_learning_summary_empty(self):
        """测试获取学习摘要（无历史）"""
        loop = LearningLoop()
        summary = loop.get_learning_summary()

        assert summary["total_cycles"] == 0
        assert summary["total_contents_analyzed"] == 0

    def test_get_patterns_for_agent(self):
        """测试获取 Agent 的学习模式"""
        loop = LearningLoop()

        # content agent 应该返回当前模式
        content_patterns = loop.get_patterns_for_agent("content")
        assert isinstance(content_patterns, str)

        # 其他 agent 应该返回空
        other_patterns = loop.get_patterns_for_agent("speech")
        assert other_patterns == ""


class TestGlobalLearningLoop:
    def test_get_learning_loop_singleton(self):
        """测试全局学习闭环单例"""
        loop1 = get_learning_loop()
        loop2 = get_learning_loop()

        assert loop1 is loop2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
