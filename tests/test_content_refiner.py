"""
内容精修组件测试 — content_refiner.py

运行: source .venv/bin/activate && pytest tests/test_content_refiner.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
import streamlit as st


class TestEnsureState:
    """状态管理测试"""

    def test_creates_new_state(self):
        from ui.components.content_refiner import _ensure_state
        with patch.dict('streamlit.session_state', {}, clear=True):
            state = _ensure_state("原始内容", "test_key_1")
            assert state["original"] == "原始内容"
            assert state["active_idx"] == 0
            assert len(state["versions"]) == 1
            assert state["versions"][0]["content"] == "原始内容"

    def test_resets_when_content_changes(self):
        from ui.components.content_refiner import _ensure_state
        with patch.dict('streamlit.session_state', {"refiner": {"key1": {"original": "旧内容", "versions": [{"content": "旧内容"}], "active_idx": 2}}}, clear=True):
            state = _ensure_state("新内容", "key1")
            assert state["original"] == "新内容"
            assert state["active_idx"] == 0

    def test_keeps_state_when_content_same(self):
        from ui.components.content_refiner import _ensure_state
        existing = {
            "key2": {
                "original": "相同内容",
                "versions": [{"content": "相同内容"}, {"content": "修改版"}],
                "active_idx": 1,
                "messages": []
            }
        }
        with patch.dict('streamlit.session_state', {"refiner": existing}, clear=True):
            state = _ensure_state("相同内容", "key2")
            assert state["active_idx"] == 1
            assert len(state["versions"]) == 2


class TestHandleRefine:
    """多轮修改逻辑测试"""

    @patch("ui.components.content_refiner._is_mock_mode")
    def test_mock_mode_adds_version(self, mock_is_mock):
        from ui.components.content_refiner import _handle_refine
        mock_is_mock.return_value = True

        with patch.dict('streamlit.session_state', {
            "refiner": {
                "key3": {
                    "original": "原始",
                    "versions": [{"content": "原始"}],
                    "active_idx": 0,
                    "messages": [{"role": "assistant", "content": "原始"}]
                }
            }
        }, clear=True):
            ok = _handle_refine("key3", "改短一点", "refiner")
            assert ok is True
            state = st.session_state["refiner"]["key3"]
            assert len(state["versions"]) == 2
            assert state["active_idx"] == 1
            assert "改短一点" in state["versions"][1]["content"]

    def test_missing_state_returns_false(self):
        from ui.components.content_refiner import _handle_refine
        with patch.dict('streamlit.session_state', {}, clear=True):
            ok = _handle_refine("missing_key", "指令", "refiner")
            assert ok is False


class TestHandleDeai:
    """去AI味测试"""

    @patch("ui.components.content_refiner._is_mock_mode")
    def test_mock_deai(self, mock_is_mock):
        from ui.components.content_refiner import _handle_deai
        mock_is_mock.return_value = True

        with patch.dict('streamlit.session_state', {
            "refiner": {
                "key4": {
                    "original": "综上所述，这是一个好产品。",
                    "versions": [{"content": "综上所述，这是一个好产品。"}],
                    "active_idx": 0,
                    "messages": []
                }
            }
        }, clear=True):
            ok = _handle_deai("key4", "refiner", "")
            assert ok is True
            state = st.session_state["refiner"]["key4"]
            assert len(state["versions"]) == 2
            assert "综上所述" not in state["versions"][1]["content"]


class TestGetActiveContent:
    """获取当前版本内容测试"""

    def test_returns_active_version(self):
        from ui.components.content_refiner import get_active_content
        with patch.dict('streamlit.session_state', {
            "refiner": {
                "key5": {
                    "versions": [
                        {"content": "V0原始"},
                        {"content": "V1修改"},
                    ],
                    "active_idx": 1,
                }
            }
        }, clear=True):
            assert get_active_content("key5") == "V1修改"

    def test_fallback_when_no_state(self):
        from ui.components.content_refiner import get_active_content
        with patch.dict('streamlit.session_state', {}, clear=True):
            assert get_active_content("missing", "fallback") == "fallback"


class TestCallRefine:
    """LLM 调用测试"""

    @patch("ui.components.content_refiner.st")
    def test_no_llm_client_shows_error(self, mock_st):
        from ui.components.content_refiner import _call_refine
        mock_st.session_state.get.return_value = None
        result = _call_refine([], "指令", "refiner")
        assert result == ""
        mock_st.error.assert_called_once()

    def test_successful_call(self):
        from ui.components.content_refiner import _call_refine
        mock_llm = MagicMock()
        mock_llm.call_with_history.return_value = "修改后的内容"

        with patch.dict('streamlit.session_state', {"llm_client": mock_llm}, clear=True):
            result = _call_refine([{"role": "assistant", "content": "原始"}], "改短", "refiner")
            assert result == "修改后的内容"
            mock_llm.call_with_history.assert_called_once()
