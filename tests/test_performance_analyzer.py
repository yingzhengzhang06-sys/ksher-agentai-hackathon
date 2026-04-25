"""
性能分析器测试 — Week 5 验证

验证项：
1. 性能数据加载和计算
2. Top-performer 识别
3. Underperformer 识别
4. 趋势分析
5. 模式提取
6. 洞察生成
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.performance_analyzer import (
    ContentPerformance,
    PerformanceInsight,
    PerformanceAnalyzer,
    get_performance_analyzer,
)


class TestContentPerformance:
    def test_create_performance(self):
        """测试创建性能数据"""
        perf = ContentPerformance(
            material_id="2026-W17-1",
            platform="wechat_moments",
            impressions=1000,
            engagements=50,
            clicks=20,
            conversions=2,
        )

        assert perf.material_id == "2026-W17-1"
        assert perf.impressions == 1000
        assert perf.engagements == 50


class TestPerformanceAnalyzer:
    def test_initialization(self):
        """测试初始化"""
        analyzer = PerformanceAnalyzer()
        assert analyzer.config is not None
        assert analyzer._performance_cache == {}

    def test_calculate_rates(self):
        """测试计算比率"""
        analyzer = PerformanceAnalyzer()
        perf = ContentPerformance(
            material_id="test",
            platform="wechat",
            impressions=1000,
            engagements=50,
            clicks=20,
            conversions=2,
        )

        result = analyzer.calculate_rates(perf)

        assert result.engagement_rate == 5.0  # 50/1000 * 100
        assert result.click_rate == 2.0  # 20/1000 * 100
        assert result.conversion_rate == 10.0  # 2/20 * 100

    def test_calculate_rates_zero_impressions(self):
        """测试零曝光情况"""
        analyzer = PerformanceAnalyzer()
        perf = ContentPerformance(
            material_id="test",
            platform="wechat",
            impressions=0,
            engagements=0,
        )

        result = analyzer.calculate_rates(perf)

        assert result.engagement_rate == 0.0
        assert result.click_rate == 0.0

    def test_identify_top_performers(self):
        """测试识别 Top Performer"""
        analyzer = PerformanceAnalyzer()

        performances = [
            ContentPerformance(
                material_id=f"test-{i}",
                platform="wechat",
                impressions=1000,
                engagements=i * 10,
            )
            for i in range(1, 11)
        ]

        # 计算 engagement_rate
        for perf in performances:
            analyzer.calculate_rates(perf)

        top = analyzer.identify_top_performers(performances, top_n=3)

        assert len(top) == 3
        assert top[0].material_id == "test-10"  # 最高的应该在前面
        assert top[1].material_id == "test-9"

    def test_identify_underperformers(self):
        """测试识别 Underperformer"""
        analyzer = PerformanceAnalyzer()

        performances = [
            ContentPerformance(
                material_id=f"test-{i}",
                platform="wechat",
                impressions=1000,
                engagements=i * 10,
            )
            for i in range(1, 11)
        ]

        for perf in performances:
            analyzer.calculate_rates(perf)

        # 阈值设为 5%，只有前 4 个 (40-100 engagements) 满足
        under = analyzer.identify_underperformers(
            performances, bottom_n=5, threshold=5.0
        )

        # 只有 engagement_rate < 5% 的会被返回
        assert len(under) <= 5

    def test_analyze_trends_empty(self):
        """测试空数据趋势分析"""
        analyzer = PerformanceAnalyzer()
        result = analyzer.analyze_trends([])

        assert result["trend"] == "stable"
        assert result["change_rate"] == 0.0

    def test_analyze_trends_improving(self):
        """测试上升趋势分析"""
        analyzer = PerformanceAnalyzer()

        # 创建上升趋势的数据
        performances = [
            ContentPerformance(
                material_id=f"test-{i}",
                platform="wechat",
                impressions=1000,
                engagements=30 + i * 10,  # 30, 40, 50, 60, 70, 80, 90, 100
                recorded_at=f"2026-04-{20+i:02d}T10:00:00",
            )
            for i in range(10)
        ]

        for perf in performances:
            analyzer.calculate_rates(perf)

        result = analyzer.analyze_trends(performances)

        assert result["trend"] == "improving"

    def test_analyze_trends_declining(self):
        """测试下降趋势分析"""
        analyzer = PerformanceAnalyzer()

        # 创建下降趋势的数据
        performances = [
            ContentPerformance(
                material_id=f"test-{i}",
                platform="wechat",
                impressions=1000,
                engagements=100 - i * 10,  # 100, 90, 80, 70, 60, 50, 40, 30
                recorded_at=f"2026-04-{20+i:02d}T10:00:00",
            )
            for i in range(10)
        ]

        for perf in performances:
            analyzer.calculate_rates(perf)

        result = analyzer.analyze_trends(performances)

        assert result["trend"] == "declining"

    def test_extract_patterns_empty(self):
        """测试空数据模式提取"""
        analyzer = PerformanceAnalyzer()
        result = analyzer.extract_patterns([])

        assert result["patterns"] == []
        assert result["confidence"] == 0.0

    def test_extract_patterns_with_data(self):
        """测试有数据的模式提取"""
        analyzer = PerformanceAnalyzer()

        performances = [
            ContentPerformance(
                material_id=f"test-{i}",
                platform="wechat_moments" if i % 2 == 0 else "xiaohongshu",
                impressions=1000,
                engagements=50,
                metadata={"theme": "行业趋势" if i % 3 == 0 else "产品价值", "day_of_week": (i % 5) + 1},
            )
            for i in range(10)
        ]

        result = analyzer.extract_patterns(performances)

        assert "patterns" in result
        assert "confidence" in result

    def test_generate_insights_empty(self):
        """测试空数据洞察生成"""
        analyzer = PerformanceAnalyzer()
        insights = analyzer.generate_insights([])

        assert isinstance(insights, list)

    def test_generate_insights_with_data(self):
        """测试有数据的洞察生成"""
        analyzer = PerformanceAnalyzer()

        performances = [
            ContentPerformance(
                material_id=f"test-{i}",
                platform="wechat_moments",
                impressions=1000,
                engagements=30 + i * 10,
                metadata={"theme": "行业趋势", "day_of_week": (i % 5) + 1},
            )
            for i in range(10)
        ]

        for perf in performances:
            analyzer.calculate_rates(perf)

        insights = analyzer.generate_insights(performances)

        assert len(insights) > 0
        assert all(isinstance(insight, PerformanceInsight) for insight in insights)

    def test_get_summary_empty(self):
        """测试空数据摘要"""
        analyzer = PerformanceAnalyzer()
        summary = analyzer.get_summary([])

        assert summary["total"] == 0
        assert summary["avg_engagement_rate"] == 0

    def test_get_summary_with_data(self):
        """测试有数据摘要"""
        analyzer = PerformanceAnalyzer()

        performances = [
            ContentPerformance(
                material_id=f"test-{i}",
                platform="wechat_moments" if i % 2 == 0 else "xiaohongshu",
                impressions=1000,
                engagements=30 + i * 10,
            )
            for i in range(10)
        ]

        for perf in performances:
            analyzer.calculate_rates(perf)

        summary = analyzer.get_summary(performances)

        assert summary["total"] == 10
        assert summary["avg_engagement_rate"] > 0
        assert "wechat_moments" in summary["platforms"]


class TestPerformanceInsight:
    def test_create_insight(self):
        """测试创建洞察"""
        insight = PerformanceInsight(
            insight_type="pattern",
            material_ids=["test-1", "test-2"],
            description="测试洞察",
            metrics={"confidence": 0.8},
            confidence=0.8,
        )

        assert insight.insight_type == "pattern"
        assert len(insight.material_ids) == 2


class TestGlobalAnalyzer:
    def test_get_performance_analyzer_singleton(self):
        """测试全局分析器单例"""
        analyzer1 = get_performance_analyzer()
        analyzer2 = get_performance_analyzer()

        assert analyzer1 is analyzer2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
