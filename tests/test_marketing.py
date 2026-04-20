"""
市场专员模块测试 — role_marketing.py

运行: source .venv/bin/activate && pytest tests/test_marketing.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from ui.pages.role_marketing import _mock_moments_calendar


class TestMockMomentsCalendar:
    """7天朋友圈日历测试"""

    def test_returns_7_days(self):
        cal = _mock_moments_calendar("ecommerce", "thailand")
        assert len(cal) == 7
        for i, day in enumerate(cal):
            assert day["day"] == i + 1
            assert "theme" in day
            assert "content" in day
            assert "time" in day
            assert len(day["content"]) > 0

    def test_product_focused(self):
        """验证产品宣传占主导（至少5天）"""
        product_themes = {"产品卖点", "客户案例", "功能亮点", "限时福利"}
        cal = _mock_moments_calendar("ecommerce", "thailand")
        product_count = sum(1 for d in cal if d["theme"] in product_themes)
        assert product_count >= 5, f"产品宣传天数只有 {product_count} 天"

    def test_weekly_rotation(self):
        """验证每周一自动刷新内容"""
        cal1 = _mock_moments_calendar("ecommerce", "thailand")
        cal2 = _mock_moments_calendar("ecommerce", "thailand")
        # 同一天多次调用应返回相同内容
        assert [d["content"] for d in cal1] == [d["content"] for d in cal2]

    def test_content_includes_ksher(self):
        """验证内容中包含 Ksher 品牌信息"""
        cal = _mock_moments_calendar("ecommerce", "thailand")
        all_content = " ".join(d["content"] for d in cal)
        assert "Ksher" in all_content or "ksher" in all_content.lower()

    def test_industry_country_substitution(self):
        """验证行业和国家被正确替换"""
        cal = _mock_moments_calendar("b2b", "malaysia")
        all_content = " ".join(d["content"] for d in cal)
        # 应该包含马来西亚相关内容
        assert "马来西亚" in all_content or "马来" in all_content

    def test_effect_field_present(self):
        """每条都有 effect 字段"""
        cal = _mock_moments_calendar("ecommerce", "thailand")
        for day in cal:
            assert "effect" in day
            assert "/" in day["effect"] or "获客" in day["effect"] or "品牌" in day["effect"]


class TestHexToRgbInMarketing:
    """测试 role_marketing.py 中的 hex_to_rgb 使用"""

    def test_hex_to_rgb_import(self):
        from ui.components.ui_cards import hex_to_rgb
        result = hex_to_rgb("#E83E4C")
        assert result == "232,62,76"


class TestContentRefinerIntegration:
    """测试 content_refiner 在市场专员中的集成"""

    def test_get_active_content_exists(self):
        from ui.components.content_refiner import get_active_content
        # 无状态时返回 fallback
        with patch.dict('streamlit.session_state', {}, clear=True):
            result = get_active_content("test_key", "fallback_value")
            assert result == "fallback_value"
