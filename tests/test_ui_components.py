"""
UI 组件测试 — ui_cards.py

运行: source .venv/bin/activate && pytest tests/test_ui_components.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock

from ui.components.ui_cards import hex_to_rgb, render_status_badge
from config import BRAND_COLORS, TYPE_SCALE, SPACING, RADIUS


class TestHexToRgb:
    """hex_to_rgb 工具函数测试"""

    def test_standard_hex(self):
        assert hex_to_rgb("#E83E4C") == "232,62,76"
        assert hex_to_rgb("#FFFFFF") == "255,255,255"
        assert hex_to_rgb("#000000") == "0,0,0"

    def test_no_hash_prefix(self):
        assert hex_to_rgb("E83E4C") == "232,62,76"

    def test_brand_colors(self):
        """验证所有品牌色都能正确转换"""
        for name, color in BRAND_COLORS.items():
            if color.startswith("#"):
                result = hex_to_rgb(color)
                parts = result.split(",")
                assert len(parts) == 3
                assert all(p.isdigit() for p in parts)
                assert all(0 <= int(p) <= 255 for p in parts)


class TestRenderStatusBadge:
    """状态徽章 HTML 生成测试"""

    def test_returns_span_html(self):
        html = render_status_badge("测试中", "#E83E4C")
        assert html.startswith("<span")
        assert "测试中" in html
        assert "#E83E4C" in html
        assert html.endswith("</span>")

    def test_size_variants(self):
        sm = render_status_badge("高", "#E83E4C", size="sm")
        md = render_status_badge("高", "#E83E4C", size="md")
        assert TYPE_SCALE["xs"] in sm
        assert TYPE_SCALE["base"] in md


class TestRenderKpiCard:
    """KPI 卡片渲染测试（需要 mock streamlit）"""

    @patch("ui.components.ui_cards.st")
    def test_sm_size(self, mock_st):
        from ui.components.ui_cards import render_kpi_card
        render_kpi_card("测试指标", "99.9%", "#E83E4C", size="sm")
        assert mock_st.markdown.called
        call_args = mock_st.markdown.call_args[0][0]
        assert "测试指标" in call_args
        assert "99.9%" in call_args
        assert "text-align:center" in call_args

    @patch("ui.components.ui_cards.st")
    def test_lg_size(self, mock_st):
        from ui.components.ui_cards import render_kpi_card
        render_kpi_card("GMV", "¥1.2M", "#00C9A7", size="lg")
        call_args = mock_st.markdown.call_args[0][0]
        assert TYPE_SCALE["display"] in call_args


class TestRenderScoreCard:
    """评分卡渲染测试"""

    @patch("ui.components.ui_cards.st")
    def test_with_max_score(self, mock_st):
        from ui.components.ui_cards import render_score_card
        render_score_card(8.5, "综合评分", "#E83E4C", max_score=10)
        call_args = mock_st.markdown.call_args[0][0]
        assert "8.5" in call_args
        assert "/10" in call_args
        assert "综合评分" in call_args

    @patch("ui.components.ui_cards.st")
    def test_without_max_score(self, mock_st):
        from ui.components.ui_cards import render_score_card
        render_score_card(95, "NPS", "#00C9A7", max_score=0)
        call_args = mock_st.markdown.call_args[0][0]
        assert "95" in call_args
        assert " NPS" in call_args  # max_score=0 时不显示 "/X"，但保留 label


class TestRenderBorderItem:
    """左边框列表项测试"""

    @patch("ui.components.ui_cards.st")
    def test_basic_render(self, mock_st):
        from ui.components.ui_cards import render_border_item
        render_border_item("标题", "描述文字", "#E83E4C")
        call_args = mock_st.markdown.call_args[0][0]
        assert "标题" in call_args
        assert "描述文字" in call_args
        assert "border-left:3px solid #E83E4C" in call_args

    @patch("ui.components.ui_cards.st")
    def test_with_right_text(self, mock_st):
        from ui.components.ui_cards import render_border_item
        render_border_item("待办", "审核材料", "#FFB800", right_text="剩余3天")
        call_args = mock_st.markdown.call_args[0][0]
        assert "剩余3天" in call_args


class TestRenderFlexRow:
    """Flex 布局行测试"""

    @patch("ui.components.ui_cards.st")
    def test_with_border(self, mock_st):
        from ui.components.ui_cards import render_flex_row
        render_flex_row("<b>左侧</b>", "<span>右侧</span>", border_color="#E83E4C")
        call_args = mock_st.markdown.call_args[0][0]
        assert "display:flex" in call_args
        assert "border-left:3px solid #E83E4C" in call_args


class TestRenderInfoCard:
    """信息卡片测试"""

    @patch("ui.components.ui_cards.st")
    def test_info_level(self, mock_st):
        from ui.components.ui_cards import render_info_card
        render_info_card("这是一条提示", level="info")
        call_args = mock_st.markdown.call_args[0][0]
        assert "这是一条提示" in call_args
        assert BRAND_COLORS["info"] in call_args

    @patch("ui.components.ui_cards.st")
    def test_success_level(self, mock_st):
        from ui.components.ui_cards import render_info_card
        render_info_card("操作成功", level="success")
        call_args = mock_st.markdown.call_args[0][0]
        assert "✅" in call_args


class TestRenderMetricRow:
    """指标行测试"""

    @patch("ui.components.ui_cards.st")
    def test_with_unit(self, mock_st):
        from ui.components.ui_cards import render_metric_row
        render_metric_row("费率", "0.05", unit="%")
        call_args = mock_st.markdown.call_args[0][0]
        assert "费率" in call_args
        assert "0.05" in call_args
        assert "%" in call_args
