"""
通用内容精修组件 — 去AI味 + 多轮修改

嵌入任何内容展示点，替代 st.markdown() + render_copy_button() 模式。
提供：
1. 一键去AI味：基于7类AI写作特征诊断改写
2. 多轮修改：用户自然语言指令迭代微调
3. 版本管理：查看/切换历史版本
"""

import re
import streamlit as st
from ui.components.error_handlers import render_copy_button
from prompts.refiner_prompts import (
    DEAI_SYSTEM_PROMPT,
    DEAI_USER_TEMPLATE,
    REFINER_SYSTEM_PROMPT,
)


# ============================================================
# 公开 API
# ============================================================

def render_content_refiner(
    content: str,
    content_key: str,
    agent_name: str = "refiner",
    context_prompt: str = "",
):
    """内容展示 + 去AI味 + 多轮修改 组件。

    Args:
        content: 生成的原始内容文本
        content_key: 全局唯一键，用于隔离 session state
        agent_name: LLM 路由的 agent 名称
        context_prompt: 可选上下文提示（如"这是朋友圈文案，面向跨境电商卖家"）
    """
    state = _ensure_state(content, content_key)

    # ---- 展示当前版本 ----
    active = state["versions"][state["active_idx"]]
    st.markdown(active["content"])

    # ---- 操作行：复制 / 去AI味 / 版本切换 ----
    col_copy, col_deai, col_ver = st.columns([1, 1, 2])

    with col_copy:
        render_copy_button(active["content"])

    with col_deai:
        if st.button("去AI味", key=f"rfn_deai_{content_key}"):
            try:
                with st.spinner("正在去AI味..."):
                    ok = _handle_deai(content_key, agent_name, context_prompt)
                if ok:
                    st.rerun()
                else:
                    st.error("去AI味失败，请检查AI连接状态后重试")
            except Exception as e:
                st.error(f"去AI味出错：{e}")

    with col_ver:
        if len(state["versions"]) > 1:
            labels = [v["label"] for v in state["versions"]]
            selected = st.selectbox(
                "版本",
                labels,
                index=state["active_idx"],
                key=f"rfn_ver_{content_key}",
                label_visibility="collapsed",
            )
            new_idx = labels.index(selected)
            if new_idx != state["active_idx"]:
                state["active_idx"] = new_idx
                st.rerun()

    # ---- 修改指令 ----
    col_input, col_send = st.columns([5, 1])
    with col_input:
        instruction = st.text_input(
            "修改指令",
            placeholder="例：把语气改得更口语化、加入具体数据、缩短到100字...",
            key=f"rfn_inst_{content_key}",
            label_visibility="collapsed",
        )
    with col_send:
        if st.button("发送修改", key=f"rfn_send_{content_key}"):
            if not instruction or not instruction.strip():
                st.warning("请输入修改指令")
            else:
                try:
                    with st.spinner("正在修改..."):
                        ok = _handle_refine(content_key, instruction.strip(), agent_name)
                    if ok:
                        st.rerun()
                    else:
                        st.error("修改失败：AI未返回有效内容，请检查连接状态后重试")
                except Exception as e:
                    st.error(f"修改出错：{e}")


def get_active_content(content_key: str, fallback: str = "") -> str:
    """获取指定 content_key 当前激活版本的内容。

    供下游功能使用（如导出图片、生成SRT时取最新修改版）。
    """
    refiner = st.session_state.get("refiner", {})
    state = refiner.get(content_key)
    if state and state["versions"]:
        return state["versions"][state["active_idx"]]["content"]
    return fallback


# ============================================================
# 内部：状态管理
# ============================================================

def _ensure_state(content: str, content_key: str) -> dict:
    """确保 session state 中有此 key 的条目，content 变化时重置。"""
    if "refiner" not in st.session_state:
        st.session_state["refiner"] = {}

    refiner = st.session_state["refiner"]

    if content_key not in refiner or refiner[content_key]["original"] != content:
        refiner[content_key] = {
            "original": content,
            "versions": [
                {"content": content, "label": "V0 原始", "source": "generate"},
            ],
            "active_idx": 0,
            "messages": [
                {"role": "assistant", "content": content},
            ],
        }

    return refiner[content_key]


# ============================================================
# 内部：去AI味
# ============================================================

def _handle_deai(content_key: str, agent_name: str, context_prompt: str) -> bool:
    """执行去AI味改写。返回是否成功。"""
    refiner = st.session_state.get("refiner", {})
    state = refiner.get(content_key)
    if not state:
        return False

    current = state["versions"][state["active_idx"]]["content"]

    if _is_mock_mode():
        result = _mock_deai(current)
    else:
        result = _call_deai(current, agent_name, context_prompt)

    if not result or not result.strip():
        return False

    ver_num = len(state["versions"])
    state["versions"].append({
        "content": result,
        "label": f"V{ver_num} 去AI味",
        "source": "de_ai",
    })
    # 更新对话历史
    state["messages"].append({"role": "user", "content": "请对上面的内容进行去AI味改写，消除AI写作痕迹"})
    state["messages"].append({"role": "assistant", "content": result})
    state["active_idx"] = ver_num
    return True


def _call_deai(content: str, agent_name: str, context_prompt: str) -> str:
    """调用LLM执行去AI味。"""
    llm = st.session_state.get("llm_client")
    if not llm:
        st.error("LLM客户端未初始化，请检查API配置")
        return ""
    try:
        user_msg = DEAI_USER_TEMPLATE.format(
            content=content,
            context=context_prompt if context_prompt else "",
        )
        return llm.call_sync(agent_name, DEAI_SYSTEM_PROMPT, user_msg)
    except Exception as e:
        st.error(f"去AI味调用失败：{e}")
        return ""


def _mock_deai(content: str) -> str:
    """Mock模式：简单替换常见AI痕迹。"""
    replacements = [
        ("综上所述，", ""),
        ("总而言之，", ""),
        ("值得注意的是，", ""),
        ("在当今社会，", ""),
        ("随着科技的发展，", ""),
        ("越来越多的人", "不少人"),
        ("首先，", "一是，"),
        ("其次，", "二是，"),
        ("此外，", "另外，"),
        ("不仅如此，", ""),
        ("与此同时，", "同时，"),
        ("更重要的是，", "关键是，"),
        ("希望本文能对你有所帮助。", ""),
        ("让我们共同", "我们一起"),
    ]
    result = content
    for old, new in replacements:
        result = result.replace(old, new)
    return "[已去AI味] " + result


# ============================================================
# 内部：多轮修改
# ============================================================

def _handle_refine(content_key: str, instruction: str, agent_name: str) -> bool:
    """执行用户指令修改。返回是否成功。"""
    refiner = st.session_state.get("refiner", {})
    state = refiner.get(content_key)
    if not state:
        return False

    current = state["versions"][state["active_idx"]]["content"]

    if _is_mock_mode():
        result = f"[已修改: {instruction}]\n\n{current}"
    else:
        result = _call_refine(state["messages"], instruction, agent_name)

    if not result or not result.strip():
        return False

    ver_num = len(state["versions"])
    state["versions"].append({
        "content": result,
        "label": f"V{ver_num} 修改",
        "source": "refine",
        "instruction": instruction,
    })
    state["messages"].append({"role": "user", "content": instruction})
    state["messages"].append({"role": "assistant", "content": result})
    state["active_idx"] = ver_num

    # 对话历史上限：保留前2条 + 最近18条
    if len(state["messages"]) > 20:
        state["messages"] = state["messages"][:2] + state["messages"][-18:]
    return True


def _call_refine(messages: list, instruction: str, agent_name: str) -> str:
    """调用LLM执行多轮修改。"""
    llm = st.session_state.get("llm_client")
    if not llm:
        st.error("LLM客户端未初始化，请检查API配置")
        return ""
    try:
        msgs = list(messages) + [{"role": "user", "content": instruction}]
        return llm.call_with_history(agent_name, REFINER_SYSTEM_PROMPT, msgs)
    except Exception as e:
        st.error(f"修改调用失败：{e}")
        return ""


# ============================================================
# 内部：工具函数
# ============================================================

def _is_mock_mode() -> bool:
    return not st.session_state.get("battle_router_ready", False)
