"""
Agent 管理中心 — 统一管理所有 AI Agent

包含 3 个 Tab：
- 角色浏览：按员工角色分组展示所有 Agent，支持查看 Prompt、配置调整、测试运行
- Prompt 管理：7 个核心 Agent 的 System Prompt 只读展示 + 版本历史 + 版本对比
- 训练中心：训练数据上传、知识注入、反馈记录、调用采集、版本管理
"""
import os
import logging
from datetime import datetime

import streamlit as st

from config import BRAND_COLORS, ADMIN_SECRET_KEY, TYPE_SCALE, RADIUS
from services.agent_manager import (
    init_agent_registry_db,
    sync_agent_registry,
    get_all_agents,
    get_agent_stats,
    get_or_create_virtual_agent,
    unregister_agent,
    toggle_agent_active,
    ROLE_GROUPS,
)
from services.training_service import (
    init_training_db,
    get_training_stats,
    get_training_pairs,
    get_feedback_records,
    get_feedback_stats,
    get_knowledge_chunks,
    get_prompt_versions,
    get_active_prompt_version,
    create_prompt_version,
    activate_prompt_version,
    add_training_pair,
    add_feedback,
    toggle_pair_starred,
    delete_training_pair,
    get_unprocessed_calls,
    promote_call_to_training_pair,
    CATEGORY_LABELS as TRAIN_CATEGORY_LABELS,
    CATEGORY_ICONS as TRAIN_CATEGORY_ICONS,
)
from services.knowledge_injection import (
    process_text_knowledge,
    process_distilled_knowledge,
    build_training_knowledge_section,
    CATEGORY_LABELS as KI_CATEGORY_LABELS,
    CATEGORY_ICONS as KI_CATEGORY_ICONS,
    CHUNK_SIZE,
)
from prompts.system_prompts import AGENT_PROMPTS
from services.llm_client import AGENT_MODEL_MAP

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# 常量
# ──────────────────────────────────────────────────────────────
ROLE_ICONS = {
    "市场专员": "📣",
    "销售支持": "💼",
    "客户经理": "🤝",
    "话术培训师": "🎓",
    "数据分析": "📊",
    "财务经理": "💰",
    "行政助手": "🏢",
    "内容精修": "✏️",
}

MODEL_LABELS = {
    "kimi": "Kimi 创意型",
    "sonnet": "Claude 精准型",
    "minimax": "MiniMax 通识型",
}

# 核心 Agent（与 prompts/system_prompts.py 对应）
CORE_AGENTS = [
    ("speech",     "销售话术生成", "销售支持"),
    ("cost",       "成本分析专家", "销售支持"),
    ("proposal",   "解决方案顾问", "销售支持"),
    ("objection",  "异议处理教练", "销售支持"),
    ("content",    "内容营销专家", "市场专员"),
    ("design",     "品牌设计顾问", "市场专员"),
    ("knowledge",  "知识问答专家", "话术培训师"),
]


# ──────────────────────────────────────────────────────────────
# 1. 管理后台密码验证
# ──────────────────────────────────────────────────────────────
def _check_admin_auth():
    if st.session_state.get("admin_authed"):
        return True

    st.title("🔐 管理后台")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            f"""
            <div style='background:{BRAND_COLORS["surface"]};border-radius:{RADIUS["lg"]};
                padding:2.5rem 2rem;text-align:center;border:1px solid #e5e6ea;'>
                <div style='font-size:3rem;margin-bottom:1rem;'>🔐</div>
                <div style='font-size:{TYPE_SCALE["lg"]};font-weight:700;margin-bottom:0.5rem;'>管理后台</div>
                <div style='font-size:{TYPE_SCALE["sm"]};color:{BRAND_COLORS["text_secondary"]};margin-bottom:1.5rem;'>
                    此区域仅对管理员开放
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        password = st.text_input("请输入密码", type="password", label_visibility="collapsed",
                                 placeholder="输入管理后台密码")
        if st.button("🚀 进入后台", use_container_width=True):
            if password == ADMIN_SECRET_KEY:
                st.session_state["admin_authed"] = True
                st.rerun()
            else:
                st.error("密码错误，请重试")
    return False


# ──────────────────────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────────────────────
def _model_badge(key: str) -> str:
    label = MODEL_LABELS.get(key, key)
    color = "#10B981" if key == "sonnet" else "#F59E0B"
    return f'<span style="background:{color}18;color:{color};padding:0.15rem 0.5rem;border-radius:0.25rem;font-size:0.7rem;font-weight:500;">{label}</span>'


def _rating_stars(rating: int) -> str:
    filled = "⭐" * rating
    empty = "☆" * (5 - rating)
    return f"{filled}{empty}"


def _temp_bar(temp: float) -> str:
    filled = int(temp * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f'<span style="font-family:monospace;font-size:0.75rem;">{bar}</span> {temp:.1f}'


def _category_badge(cat: str) -> str:
    icon = KI_CATEGORY_ICONS.get(cat, "📋")
    label = KI_CATEGORY_LABELS.get(cat, cat)
    return f'<span style="background:#f3f4f6;color:#374151;padding:0.1rem 0.4rem;border-radius:0.25rem;font-size:0.65rem;">{icon} {label}</span>'


# ──────────────────────────────────────────────────────────────
# 2. Agent 卡片（角色浏览 Tab）
# ──────────────────────────────────────────────────────────────
def _render_agent_card(agent, role: str):
    icon = ROLE_ICONS.get(role, "🤖")
    virtual_badge = '<span style="background:#8B5CF618;color:#8B5CF6;padding:0.1rem 0.4rem;border-radius:0.25rem;font-size:0.65rem;">虚拟</span>' if agent.is_virtual else ""
    inactive_badge = '<span style="background:#E83E4C18;color:#E83E4C;padding:0.1rem 0.4rem;border-radius:0.25rem;font-size:0.65rem;">已停用</span>' if agent.is_active == 0 else ""

    with st.container():
        col_l, col_r = st.columns([5, 1])
        with col_l:
            badges = " ".join([b for b in [virtual_badge, inactive_badge] if b])
            st.markdown(f"**{icon} {agent.display_name}** {badges}" if badges else f"**{icon} {agent.display_name}**")
        with col_r:
            st.markdown(_model_badge(agent.model_key), unsafe_allow_html=True)

        col_desc, col_temp = st.columns([5, 1])
        with col_desc:
            if agent.description:
                st.caption(f"📝 {agent.description}")
        with col_temp:
            st.markdown(f"<div style='text-align:right;'>{_temp_bar(agent.temperature)}</div>",
                        unsafe_allow_html=True)

        col_meta1, col_meta2, col_meta3 = st.columns(3)
        with col_meta1:
            st.caption(f"🔢 调用 {agent.usage_count} 次")
        with col_meta2:
            if agent.last_used:
                st.caption(f"🕐 {agent.last_used[:16]}")
        with col_meta3:
            rate = round(agent.success_count / agent.usage_count * 100, 1) if agent.usage_count > 0 else 0
            color = BRAND_COLORS["success"] if rate >= 80 else BRAND_COLORS["danger"] if rate < 50 else BRAND_COLORS["warning"]
            st.caption(f"📊 成功率 {rate}%")

        col_ops = st.columns([1, 1, 1, 1] if agent.is_virtual else [1, 1, 1])
        with col_ops[0]:
            expanded = st.session_state.get(f"view_prompt_{agent.agent_name}", False)
            new_label = "收起 Prompt" if expanded else "👁️ 查看 Prompt"
            if st.button(new_label, key=f"vp_{agent.agent_name}", use_container_width=True):
                st.session_state[f"view_prompt_{agent.agent_name}"] = not expanded
                st.rerun()
        with col_ops[1]:
            expanded_cfg = st.session_state.get(f"edit_cfg_{agent.agent_name}", False)
            new_label = "收起配置" if expanded_cfg else "⚙️ 调整配置"
            if st.button(new_label, key=f"ecfg_{agent.agent_name}", use_container_width=True):
                st.session_state[f"edit_cfg_{agent.agent_name}"] = not expanded_cfg
                st.rerun()
        with col_ops[2]:
            if st.button("🧪 测试", key=f"tst_{agent.agent_name}", use_container_width=True):
                _run_agent_test(agent)
        if agent.is_virtual:
            with col_ops[3]:
                toggle_label = "✅ 激活" if agent.is_active == 0 else "⏸ 停用"
                if st.button(toggle_label, key=f"tgl_{agent.agent_name}", use_container_width=True):
                    result = toggle_agent_active(agent.agent_name)
                    st.success(result.get("message", ""))
                    st.rerun()

        if st.session_state.get(f"view_prompt_{agent.agent_name}"):
            _render_prompt_panel(agent)
        if st.session_state.get(f"edit_cfg_{agent.agent_name}"):
            _render_config_panel(agent)
        st.markdown("---")


def _render_prompt_panel(agent):
    prompt_text = AGENT_PROMPTS.get(agent.agent_name, "（未在 system_prompts.py 中注册）")
    st.markdown("**📋 System Prompt**")
    with st.expander("查看完整 Prompt"):
        st.code(prompt_text, language=None)

    has_rules = "{KNOWLEDGE_FUSION_RULES}" in prompt_text
    if has_rules:
        st.success("✓ 使用 KNOWLEDGE_FUSION_RULES 占位符，运行时注入知识融合规则")
    else:
        st.warning("✗ 未使用 KNOWLEDGE_FUSION_RULES 占位符")

    mapped = AGENT_MODEL_MAP.get(agent.agent_name, "kimi")
    st.info(f"🔗 LLM 路由：{agent.agent_name} → {mapped}（{MODEL_LABELS.get(mapped, mapped)}）")


def _render_config_panel(agent):
    st.markdown("**⚙️ Agent 配置**")
    with st.form(f"cfg_f_{agent.agent_name}", clear_on_submit=True):
        new_temp = st.slider("Temperature", 0.0, 1.0, float(agent.temperature), 0.1)
        st.text_input("Agent Name（只读）", agent.agent_name, disabled=True, key=f"an_{agent.agent_name}")
        st.caption("📌 System Prompt 由 prompts/system_prompts.py 管理，模型路由由 services/llm_client.py 管理")
        submitted = st.form_submit_button("💾 保存", use_container_width=True)
        if submitted:
            st.info("配置保存功能开发中，修改请联系开发者直接编辑代码文件")


def _run_agent_test(agent):
    from services.app_initializer import get_agent_by_name
    try:
        agent_obj = get_agent_by_name(agent.agent_name)
        if not agent_obj:
            st.error(f"未找到 Agent：{agent.agent_name}")
            return
        ctx = {
            "company": "测试公司", "industry": "b2c", "target_country": "泰国",
            "monthly_volume": 50000, "current_channel": "银行电汇",
            "pain_points": ["手续费高", "到账慢"],
        }
        result = agent_obj.generate(ctx)
        st.success("✅ 测试成功")
        with st.expander("查看结果"):
            import json
            st.json(result)
    except Exception as e:
        st.error(f"❌ 测试失败：{e}")


def _render_role_group(group, agents_by_role: dict):
    role = group["role"]
    icon = ROLE_ICONS.get(role, "🤖")
    color = "#3B82F6"
    agents = agents_by_role.get(role, [])
    if not agents:
        return
    with st.container():
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:0.75rem;margin:1.5rem 0 0.75rem 0;">
                <span style="font-size:1.5rem;">{icon}</span>
                <span style="font-size:{TYPE_SCALE["lg"]};font-weight:700;">{role}</span>
                <span style="background:#3B82F618;color:#3B82F6;padding:0.15rem 0.6rem;
                           border-radius:0.25rem;font-size:0.75rem;font-weight:500;">
                    {len(agents)} 个 Agent
                </span>
                <span style="font-size:{TYPE_SCALE["xs"]};color:{BRAND_COLORS["text_secondary"]};">
                    {group['description']}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for agent in agents:
            _render_agent_card(agent, role)


# ──────────────────────────────────────────────────────────────
# 3. Prompt 管理 Tab
# ──────────────────────────────────────────────────────────────
def _render_prompt_management_tab():
    st.subheader("📝 Prompt 版本管理")

    # Agent 选择器
    agent_options = [f"{name}（{role}）" for name, display, role in CORE_AGENTS]
    selected_idx = st.selectbox("选择 Agent", range(len(agent_options)),
                                format_func=lambda i: agent_options[i])
    selected_agent = CORE_AGENTS[selected_idx][0]
    selected_display = CORE_AGENTS[selected_idx][1]

    st.markdown("---")

    # 当前 Prompt（只读）
    current_prompt = AGENT_PROMPTS.get(selected_agent, "（未注册）")
    has_rules = "{KNOWLEDGE_FUSION_RULES}" in current_prompt

    col_active, col_history = st.columns([2, 1])
    with col_active:
        st.markdown(f"**当前活跃版本 — {selected_display}**")
        with st.expander("查看完整 System Prompt", expanded=True):
            st.code(current_prompt, language=None)
        if has_rules:
            st.success("✓ 运行时注入知识融合规则")
        else:
            st.warning("✗ 未使用知识融合规则占位符")
        mapped = AGENT_MODEL_MAP.get(selected_agent, "kimi")
        st.info(f"🔗 路由：{selected_agent} → {mapped}（{MODEL_LABELS.get(mapped)}）")

    with col_history:
        st.markdown("**版本历史**")
        init_training_db()
        versions = get_prompt_versions(selected_agent, limit=20)
        if versions:
            for v in versions:
                tag = "🟢" if v.is_active else "  "
                st.markdown(f"{tag} v{v.version_num} · {v.created_at[:10]} · {v.usage_count}次调用")
                if v.change_description:
                    st.caption(f"   {v.change_description}")
        else:
            st.info("暂无版本记录，可通过下方「记录版本」保存当前版本")

    st.markdown("---")

    # 记录新版本
    with st.expander("📌 记录新版本"):
        st.markdown("将当前 system_prompts.py 中的 Prompt 保存为新版本，附带变更说明（只读保存，不覆盖代码）")
        with st.form("save_version_form", clear_on_submit=True):
            change_desc = st.text_area("变更说明", placeholder="本次变更了哪些内容？为什么要改？",
                                     help="记录变更原因，方便后续追溯")
            submitted = st.form_submit_button("💾 保存版本", use_container_width=True)
            if submitted:
                init_training_db()
                vid = create_prompt_version(selected_agent, current_prompt, change_desc)
                st.success(f"✅ 版本已保存（vID: {vid[:8]}...），后续可在「版本历史」中激活")
                st.rerun()


# ──────────────────────────────────────────────────────────────
# 4. 训练中心 Tab
# ──────────────────────────────────────────────────────────────
def _render_training_center_tab():
    st.subheader("🎯 持续训练中心")
    st.caption("通过知识注入 + 反馈闭环，持续提升每个 Agent 的能力")

    init_training_db()
    stats = get_training_stats()

    # 统计概览
    col1, col2, col3, col4, col5 = st.columns(5)
    for col, label, value, color in [
        (col1, "训练对", stats["total_pairs"], BRAND_COLORS["primary"]),
        (col2, "⭐精选", stats["starred_pairs"], "#F59E0B"),
        (col3, "反馈", stats["total_feedback"], "#3B82F6"),
        (col4, "知识块", stats["total_chunks"], BRAND_COLORS["success"]),
        (col5, "调用记录", stats["total_calls"], "#8B5CF6"),
    ]:
        with col:
            st.markdown(
                f"""
                <div style='background:{BRAND_COLORS["surface"]};border-radius:{RADIUS["lg"]};
                    padding:1rem;text-align:center;border:1px solid #e5e6ea;'>
                    <div style='font-size:1.4rem;font-weight:700;color:{color};'>{value}</div>
                    <div style='font-size:0.75rem;color:{BRAND_COLORS["text_secondary"]};margin-top:0.2rem;'>{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # Agent 选择
    agent_options = [f"{d}（{r}）" for name, d, r in CORE_AGENTS]
    sel_idx = st.selectbox("选择 Agent 进行训练", range(len(agent_options)),
                           format_func=lambda i: agent_options[i])
    sel_agent = CORE_AGENTS[sel_idx][0]
    sel_display = CORE_AGENTS[sel_idx][1]

    st.markdown("---")

    # 子 Tab：训练数据 | 知识注入 | 反馈记录 | 调用采集
    sub_tabs = ["📚 训练数据", "📥 知识注入", "⭐ 反馈记录", "📡 调用采集"]
    active_sub = st.radio("子分类", sub_tabs, horizontal=True,
                          label_visibility="collapsed",
                          index=st.session_state.get("train_sub_tab", 0))

    sub_tab_map = {t: i for i, t in enumerate(sub_tabs)}
    st.session_state["train_sub_tab"] = sub_tab_map[active_sub]
    st.markdown("---")

    if active_sub == "📚 训练数据":
        _render_training_data_subtab(sel_agent, sel_display)
    elif active_sub == "📥 知识注入":
        _render_knowledge_injection_subtab(sel_agent, sel_display)
    elif active_sub == "⭐ 反馈记录":
        _render_feedback_subtab(sel_agent, sel_display)
    elif active_sub == "📡 调用采集":
        _render_call_capture_subtab(sel_agent, sel_display)


def _render_training_data_subtab(agent_name: str, display_name: str):
    st.markdown(f"**📚 训练数据 — {display_name}**")
    st.caption("训练对 = 输入上下文 + 输出结果。优质训练对可标记为⭐，供 fine-tune 使用")

    # 筛选
    col_src, col_rating = st.columns([1, 1])
    with col_src:
        src_filter = st.selectbox("来源", ["全部", "手动添加", "自动采集", "⭐精选"])
    with col_rating:
        min_rating = st.selectbox("最低评分", ["全部", "⭐⭐⭐⭐⭐(5)", "⭐⭐⭐⭐+(4+)", "⭐⭐⭐+(3+)"],
                                  index=0)

    source_map = {"全部": None, "手动添加": "manual_upload", "自动采集": "auto_captured", "⭐精选": None}
    starred = src_filter == "⭐精选"
    min_r = {"全部": 0, "⭐⭐⭐⭐⭐(5)": 5, "⭐⭐⭐⭐+(4+)": 4, "⭐⭐⭐+(3+)": 3}[min_rating]
    source_type = source_map.get(src_filter)
    pairs = get_training_pairs(agent_name, source_type=source_type,
                              min_rating=min_r, starred_only=starred, limit=50)

    st.markdown(f"共 {len(pairs)} 条训练对")
    for pair in pairs:
        with st.container():
            col_l, col_r = st.columns([5, 1])
            with col_l:
                stars = "⭐" * (pair.quality_rating or 0)
                src_icon = {"manual_upload": "✏️", "auto_captured": "🤖"}.get(pair.source_type, "📝")
                st.markdown(f"**{src_icon} {pair.source_type}** {stars}")
            with col_r:
                if st.button("⭐" if pair.is_starred else "☆", key=f"star_{pair.pair_id}",
                           use_container_width=True):
                    toggle_pair_starred(pair.pair_id)
                    st.rerun()
            if pair.input_context:
                with st.expander("输入上下文"):
                    st.json(pair.input_context)
            if pair.output_text:
                st.text_area("输出", pair.output_text[:500], height=120,
                            label_visibility="collapsed", key=f"out_{pair.pair_id}")
            st.caption(f"🕐 {pair.created_at[:16]}")
            col_del = st.columns([1])
            with col_del[0]:
                if st.button("🗑️ 删除", key=f"del_{pair.pair_id}", use_container_width=True):
                    delete_training_pair(pair.pair_id)
                    st.rerun()
            st.markdown("---")

    # 添加训练对
    with st.expander("➕ 添加训练对"):
        with st.form("add_pair_form", clear_on_submit=True):
            input_ctx_json = st.text_area("输入上下文（JSON）", "{}",
                                          help="可以是客户画像、参数等")
            output_text = st.text_area("输出结果", height=150)
            rating = st.slider("质量评分", 0, 5, 3)
            submitted = st.form_submit_button("💾 添加", use_container_width=True)
            if submitted:
                import json as _json
                try:
                    ctx = _json.loads(input_ctx_json)
                except Exception:
                    ctx = {}
                add_training_pair(agent_name, "manual_upload",
                                  input_context=input_ctx_json,
                                  output_text=output_text,
                                  quality_rating=rating)
                st.success("✅ 训练对已添加")
                st.rerun()


def _render_knowledge_injection_subtab(agent_name: str, display_name: str):
    st.markdown(f"**📥 知识注入 — {display_name}**")
    st.caption("上传领域知识文档，系统自动分块并关联到 Agent。Agent 生成时会自动检索相关知识补充到 Prompt")

    # 当前知识块
    chunks = get_knowledge_chunks(agent_name, limit=20)
    st.markdown(f"**当前知识块（{len(chunks)} 个）**")
    if chunks:
        # 按分类分组
        by_cat = {}
        for c in chunks:
            by_cat.setdefault(c.category, []).append(c)
        for cat, cat_chunks in by_cat.items():
            st.markdown(f"**{_category_badge(cat)} ({len(cat_chunks)}块)**")
            for c in cat_chunks[:3]:
                with st.expander(f"块 {c.chunk_index+1}（检索{c.retrieval_count}次）"):
                    st.text(c.content[:400], height=100)
            if len(cat_chunks) > 3:
                st.caption(f"...还有 {len(cat_chunks)-3} 个知识块")
    else:
        st.info("暂无知识块，请通过下方上传")

    st.markdown("---")

    # 上传知识
    with st.expander("📌 上传新知识"):
        cats = list(KI_CATEGORY_LABELS.items())
        cat_options = [f"{KI_CATEGORY_ICONS.get(k,'📋')} {v}" for k, v in cats]
        sel_cat_idx = st.selectbox("知识分类", range(len(cat_options)),
                                   format_func=lambda i: cat_options[i])
        sel_cat = cats[sel_cat_idx][0]

        title = st.text_input("标题", placeholder="如：泰国电商市场趋势报告2025")
        knowledge_text = st.text_area("知识内容", height=200,
                                      placeholder="粘贴或输入要注入的知识内容...")
        col_upload, col_preview = st.columns([1, 1])
        with col_upload:
            submitted = st.form_submit_button("💾 注入知识", use_container_width=True)
        with col_preview:
            if knowledge_text:
                word_count = len(knowledge_text)
                est_chunks = (word_count // CHUNK_SIZE) + 1
                st.caption(f"约 {word_count} 字，预计分成 {est_chunks} 个知识块")

        if submitted:
            if len(knowledge_text) < 20:
                st.warning("内容过少，请至少输入 20 个字符")
            else:
                # 优先使用知识蒸馏器（PARA 语义分块）
                result = process_distilled_knowledge(knowledge_text, title, agent_name)
                if result.get("success"):
                    routing = result.get("agent_routing", [])
                    st.success(
                        f"✅ 知识蒸馏完成！{result['total_chunks']} 个语义块 → "
                        f"{routing} · PARA分类：{result.get('para_category', 'N/A')}"
                    )
                    if result.get('core_thesis'):
                        st.info(f"💡 核心论点：{result['core_thesis'][:100]}")
                    st.rerun()
                else:
                    # Fallback to legacy method
                    result = process_text_knowledge(knowledge_text, title, agent_name, sel_cat)
                    if result["success"]:
                        st.success(f"✅ 已注入 {result['total_chunks']} 个知识块到 {len(result['agents'])} 个 Agent")
                        st.rerun()
                    else:
                        st.error(f"❌ 失败：{result['message']}")


def _render_feedback_subtab(agent_name: str, display_name: str):
    st.markdown(f"**⭐ 反馈记录 — {display_name}**")

    fb_stats = get_feedback_stats(agent_name, days=30)
    col_dist, col_avg = st.columns([2, 1])
    with col_dist:
        st.markdown("**评分分布（近30天）**")
        dist = fb_stats["distribution"]
        total = fb_stats["total"]
        if total > 0:
            bar_data = {f"⭐{k}": v for k, v in dist.items()}
            st.bar_chart(bar_data)
        else:
            st.info("暂无反馈数据")
    with col_avg:
        st.markdown(f"**平均评分**")
        avg = fb_stats["avg_rating"]
        st.markdown(
            f"""<div style="text-align:center;padding:1rem;">
                <div style="font-size:2rem;font-weight:700;color:{'#F59E0B' if avg >= 4 else BRAND_COLORS['danger']};">
                    {avg:.1f}
                </div>
                <div style="font-size:0.75rem;color:{BRAND_COLORS['text_secondary']};">/ 5.0</div>
                <div style="font-size:0.75rem;color:{BRAND_COLORS['text_muted']};">共 {total} 条</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 添加反馈
    with st.expander("📌 添加反馈"):
        with st.form("add_feedback_form", clear_on_submit=True):
            rating = st.slider("输出质量评分", 1, 5, 4,
                              help="5=优秀，4=良好，3=一般，2=较差，1=很差")
            tags_options = ["accurate", "too_short", "too_long", "missing_data",
                            "helpful", "creative", "factual"]
            selected_tags = st.multiselect("质量标签", tags_options)
            improvement = st.text_area("改进建议", height=80,
                                      placeholder="指出输出中需要改进的地方...")
            submitted = st.form_submit_button("💾 提交反馈", use_container_width=True)
            if submitted:
                fid = add_feedback(agent_name, rating, quality_tags=selected_tags,
                                  improvement=improvement)
                st.success(f"✅ 反馈已记录（{fid[:8]}...），平均评分将更新")
                st.rerun()

    # 最近反馈列表
    st.markdown("**最近反馈**")
    feedbacks = get_feedback_records(agent_name, limit=30)
    for fb in feedbacks:
        with st.container():
            col_l, col_r = st.columns([3, 1])
            with col_l:
                st.markdown(f"{_rating_stars(fb.rating)} — {fb.quality_tags} {fb.improvement[:60]}")
            with col_r:
                st.caption(fb.created_at[:16])
            st.markdown("---")


def _render_call_capture_subtab(agent_name: str, display_name: str):
    st.markdown(f"**📡 自动调用采集 — {display_name}**")
    st.caption("系统自动记录的 Agent 调用，供审核后将优质结果转为训练对")

    calls = get_unprocessed_calls(agent_name, limit=20)
    st.markdown(f"**待审核（{len(calls)} 条）**")
    if not calls:
        st.info("暂无未处理的调用记录。调用 Agent 后会自动采集。")
    for call in calls:
        with st.container():
            col_l, col_ops = st.columns([5, 1])
            with col_l:
                if call["error_detected"]:
                    st.error(f"❌ 错误调用（{call['latency_ms']}ms）")
                else:
                    st.success(f"✅ 成功（{call['latency_ms']}ms）")
                if call["input_context"]:
                    try:
                        import json as _json
                        ctx = _json.loads(call["input_context"])
                        st.caption(f"公司：{ctx.get('company','未知')} | 国家：{ctx.get('target_country','未知')}")
                    except Exception:
                        pass
            with col_ops:
                if st.button("⭐转为训练对", key=f"promo_{call['record_id']}", use_container_width=True):
                    pair_id = promote_call_to_training_pair(call["record_id"])
                    if pair_id:
                        st.success(f"✅ 已转为训练对")
                    else:
                        st.warning("转换失败，可能已被处理")
                    st.rerun()
            st.markdown("---")


# ──────────────────────────────────────────────────────────────
# 主渲染
# ──────────────────────────────────────────────────────────────
def render_agent_center():
    if not _check_admin_auth():
        return

    st.subheader("🤖 Agent 管理中心")
    st.caption("统一管理所有 AI Agent，支持 Prompt 查看、配置调整和持续训练")

    init_agent_registry_db()
    sync_agent_registry()
    init_training_db()

    # 顶层 Tab
    tab_labels = ["👁️ 角色浏览", "📝 Prompt管理", "🎯 训练中心"]
    active_tab = st.radio(
        "管理分类",
        tab_labels,
        index=st.session_state.get("agent_center_tab", 0),
        horizontal=True,
        label_visibility="collapsed",
    )
    tab_idx_map = {t: i for i, t in enumerate(tab_labels)}
    st.session_state["agent_center_tab"] = tab_idx_map[active_tab]
    st.markdown("---")

    if active_tab == "👁️ 角色浏览":
        stats = get_agent_stats()
        all_agents = get_all_agents()
        agents_by_role = {}
        for a in all_agents:
            agents_by_role.setdefault(a.role, []).append(a)

        total_agents = len(all_agents)
        _render_role_overview(stats, total_agents)
        st.markdown("---")

        role_options = [g["role"] for g in ROLE_GROUPS]
        selected_role = st.selectbox(
            "选择角色组",
            options=["全部"] + role_options,
            format_func=lambda x: f"{ROLE_ICONS.get(x, '🤖')} {x}" if x != "全部" else "📋 全部角色",
        )
        st.markdown("---")

        if selected_role == "全部":
            for group in ROLE_GROUPS:
                _render_role_group(group, agents_by_role)
        else:
            group = next(g for g in ROLE_GROUPS if g["role"] == selected_role)
            _render_role_group(group, agents_by_role)

        st.markdown("---")

        # ── 虚拟 Agent 专区 ──
        _render_virtual_agents_section(all_agents)

        st.caption(
            f"📌 共 {total_agents} 个 Agent（{stats.get('active', 0)} 活跃 + {stats.get('virtual', 0)} 虚拟）"
            f" · 累计调用 {stats['total_calls']} 次 · 成功率 {stats['avg_success_rate']}%"
            f" · 🕐 {datetime.now().strftime('%H:%M:%S')}"
        )
        if st.button("🔄 重新同步"):
            sync_agent_registry()
            st.rerun()

    elif active_tab == "📝 Prompt管理":
        _render_prompt_management_tab()

    elif active_tab == "🎯 训练中心":
        _render_training_center_tab()


# ──────────────────────────────────────────────────────────────
# 辅助：虚拟 Agent 专区
# ──────────────────────────────────────────────────────────────
def _render_virtual_agents_section(all_agents: list):
    """虚拟 Agent 创建 + 展示"""
    virtual_agents = [a for a in all_agents if a.is_virtual == 1]

    with st.expander(f"🌟 虚拟 Agent 管理（{len(virtual_agents)} 个）", expanded=False):
        # 创建虚拟 Agent
        st.markdown("**创建新虚拟 Agent**")
        with st.form("create_virtual_agent", clear_on_submit=True):
            col_name, col_display = st.columns([1, 1])
            with col_name:
                agent_name = st.text_input(
                    "Agent ID",
                    placeholder="如：custom_sales_assistant",
                    help="唯一标识符，只能用英文+下划线"
                )
            with col_display:
                display_name = st.text_input("显示名称", placeholder="如：自定义销售助手")
            col_role, col_model, col_temp = st.columns([1, 1, 1])
            with col_role:
                role_options = list(ROLE_ICONS.keys())
                selected_role = st.selectbox("所属角色", role_options,
                                           format_func=lambda x: f"{ROLE_ICONS.get(x,'🤖')} {x}")
            with col_model:
                model = st.selectbox("模型", ["kimi", "sonnet"],
                                    format_func=lambda x: MODEL_LABELS.get(x, x))
            with col_temp:
                temperature = st.slider("温度", 0.0, 1.0, 0.7, 0.1)
            description = st.text_input("描述", placeholder="该 Agent 的职责说明")
            submitted = st.form_submit_button("🌟 创建虚拟 Agent", use_container_width=True)
            if submitted:
                if not agent_name or not display_name:
                    st.warning("请填写 Agent ID 和显示名称")
                elif not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", agent_name):
                    st.warning("Agent ID 只能包含英文字母、数字和下划线，且不能以数字开头")
                else:
                    result = get_or_create_virtual_agent(
                        agent_name=agent_name,
                        display_name=display_name,
                        role=selected_role,
                        description=description,
                        model_key=model,
                        temperature=temperature,
                    )
                    if result.get("success"):
                        st.success(f"✅ 虚拟 Agent「{display_name}」创建成功，将出现在 Agent 管理列表中")
                        st.rerun()
                    else:
                        st.error(f"❌ 创建失败：{result.get('message', '未知错误')}")

        st.markdown("---")

        # 虚拟 Agent 列表
        st.markdown(f"**已有虚拟 Agent（{len(virtual_agents)} 个）**")
        if not virtual_agents:
            st.info("暂无虚拟 Agent，通过上方表单创建一个")
        else:
            for va in virtual_agents:
                col_l, col_r = st.columns([5, 1])
                with col_l:
                    status_icon = "🟢" if va.is_active else "🔴"
                    st.markdown(
                        f"**{status_icon} {va.display_name}**"
                        f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:0.75rem;'>"
                        f" · {va.agent_name} · {va.role}</span>",
                        unsafe_allow_html=True
                    )
                with col_r:
                    if st.button("🗑️", key=f"del_va_{va.agent_name}", use_container_width=True):
                        result = unregister_agent(va.agent_name)
                        if result.get("success"):
                            st.success("已删除")
                        else:
                            st.error(result.get("message", ""))
                        st.rerun()
                st.caption(f"📝 {va.description or '（无描述）'}")
                st.markdown("")


# ──────────────────────────────────────────────────────────────
# 辅助：角色概览卡片
# ──────────────────────────────────────────────────────────────
def _render_role_overview(stats: dict, total_agents: int):
    col1, col2, col3, col4, col5 = st.columns(5)
    for col, label, value, color in [
        (col1, "角色组", len(stats["by_role"]), BRAND_COLORS["primary"]),
        (col2, "活跃Agent", stats.get("active", total_agents), "#3B82F6"),
        (col3, "虚拟Agent", stats.get("virtual", 0), "#8B5CF6"),
        (col4, "累计调用", stats["total_calls"], BRAND_COLORS["success"]),
        (col5, "成功率", f"{stats['avg_success_rate']}%", "#F59E0B"),
    ]:
        with col:
            st.markdown(
                f"""<div style='background:{BRAND_COLORS["surface"]};border-radius:{RADIUS["lg"]};
                    padding:1.25rem;text-align:center;border:1px solid #e5e6ea;'>
                    <div style='font-size:1.6rem;font-weight:700;color:{color};'>{value}</div>
                    <div style='font-size:0.8rem;color:{BRAND_COLORS["text_secondary"]};margin-top:0.25rem;'>{label}</div>
                </div>""",
                unsafe_allow_html=True,
            )
