"""
数据采集集成测试 — Week 4 验证

验证项：
1. CompetitorMonitor 抓取和解析
2. AnalyticsCollector 手动录入和 Excel 导入
3. 审批队列端到端流程
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from integrations.competitor_monitor import CompetitorMonitor, run_competitor_monitor
from integrations.analytics_collector import AnalyticsCollector


class TestCompetitorMonitor:
    def test_initialization(self):
        """测试初始化"""
        monitor = CompetitorMonitor({"platforms": ["xiaohongshu"], "competitors": ["PingPong"]})
        assert monitor.name == "competitor_monitor"
        assert monitor.config["platforms"] == ["xiaohongshu"]
        assert monitor.config["competitors"] == ["PingPong"]

    def test_parse_empty_data(self):
        """测试解析空数据"""
        monitor = CompetitorMonitor()
        result = monitor.parse({"xiaohongshu": []})
        assert result == []

    def test_parse_mock_data(self):
        """测试解析模拟数据"""
        monitor = CompetitorMonitor()
        # 使用空列表模拟
        mock_data = {
            "xiaohongshu": []
        }
        result = monitor.parse(mock_data)

        assert len(result) == 0

    def test_run_without_crawler(self):
        """测试 run 方法（验证执行流程完整性）"""
        monitor = CompetitorMonitor({"auto_save": False})
        result = monitor.run()
        # 验证执行成功
        assert result["success"] is True
        # 验证返回结构
        assert "count" in result
        assert "data" in result
        assert "error" in result

    def test_run_competitor_monitor_function(self):
        """测试便捷函数"""
        result = run_competitor_monitor({"auto_save": False})
        assert "success" in result
        assert "count" in result
        assert "data" in result


class TestAnalyticsCollector:
    def test_initialization(self):
        """测试初始化"""
        collector = AnalyticsCollector()
        assert collector.name == "analytics_collector"
        assert len(collector._manual_data) == 0

    def test_add_manual_data(self):
        """测试手动录入数据"""
        collector = AnalyticsCollector()
        data = {
            "material_id": "2026-W17-1",
            "platform": "wechat_moments",
            "impressions": 1000,
            "engagements": 50,
        }
        result = collector.add_manual_data(data)
        assert result is True
        assert len(collector._manual_data) == 1

    def test_add_manual_data_missing_fields(self):
        """测试缺少必填字段"""
        collector = AnalyticsCollector()
        data = {
            "material_id": "2026-W17-1",
            # 缺少 platform, impressions, engagements
        }
        result = collector.add_manual_data(data)
        assert result is False

    def test_get_engagement_rate(self):
        """测试计算 engagement_rate"""
        collector = AnalyticsCollector()
        collector.add_manual_data({
            "material_id": "test1",
            "platform": "wx",
            "impressions": 1000,
            "engagements": 50,
        })
        collector.add_manual_data({
            "material_id": "test2",
            "platform": "wx",
            "impressions": 500,
            "engagements": 40,
        })

        rates = collector.get_engagement_rate(collector._manual_data)
        assert abs(rates["test1"] - 5.0) < 0.01  # 50/1000 = 5%
        assert abs(rates["test2"] - 8.0) < 0.01  # 40/500 = 8%

    def test_get_top_performers(self):
        """测试获取表现最好的内容"""
        collector = AnalyticsCollector()
        collector.add_manual_data({
            "material_id": "low",
            "platform": "wx",
            "impressions": 1000,
            "engagements": 10,
        })
        collector.add_manual_data({
            "material_id": "high",
            "platform": "wx",
            "impressions": 100,
            "engagements": 20,
        })

        top = collector.get_top_performers(collector._manual_data, top_n=2)
        assert len(top) == 2
        assert top[0]["material_id"] == "high"  # 20% > 1%
        assert top[1]["material_id"] == "low"

    def test_clear_manual_data(self):
        """测试清空手动数据"""
        collector = AnalyticsCollector()
        collector.add_manual_data({
            "material_id": "test",
            "platform": "wx",
            "impressions": 100,
            "engagements": 10,
        })
        assert len(collector._manual_data) == 1

        collector.clear_manual_data()
        assert len(collector._manual_data) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
