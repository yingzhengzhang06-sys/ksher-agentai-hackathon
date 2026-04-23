"""
销售支持 — AI作战指挥部

6个Tab：作战包 / 产品百科 / 单证指南 / 合规风控 / 竞品雷达 / 客户评分
"""

import json
import re
import streamlit as st

from config import BRAND_COLORS, TYPE_SCALE, SPACING, RADIUS, STATUS_COLOR_MAP
from ui.components.content_refiner import render_content_refiner
from ui.components.ui_cards import hex_to_rgb
from ui.components.swarm_monitor import render_swarm_monitor, render_swarm_control
from ui.components.skill_library_ui import render_skill_library_ui


# ---- LLM helpers ----

def _get_llm():
    return st.session_state.get("llm_client")


def _is_mock_mode() -> bool:
    return not st.session_state.get("battle_router_ready", False)


def _llm_call(system: str, user_msg: str, agent_name: str = "knowledge",
              temperature: float = 0.3) -> str:
    llm = _get_llm()
    if not llm:
        return ""
    try:
        return llm.call_sync(agent_name=agent_name, system=system,
                             user_msg=user_msg, temperature=temperature)
    except Exception:
        return ""


def _parse_json_safe(text: str) -> dict | None:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    if text and "```" in text:
        m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except (json.JSONDecodeError, TypeError):
                pass
    return None


def _tavily_search(query: str, max_results: int = 5) -> str:
    """调用Tavily MCP搜索（如果可用），否则返回空"""
    try:
        from services.llm_client import _get_secret
        api_key = _get_secret("TAVILY_API_KEY", "")
        if not api_key:
            return ""
        import requests
        resp = requests.post(
            "https://api.tavily.com/search",
            json={"query": query, "max_results": max_results,
                  "search_depth": "basic", "api_key": api_key},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for r in data.get("results", [])[:max_results]:
                results.append(f"- {r.get('title', '')}: {r.get('content', '')[:300]}")
            return "\n".join(results) if results else ""
    except Exception:
        pass
    return ""


def _multi_search_research(company: str, industry: str, country: str) -> dict:
    """三维度并行深度搜索：公司基本面 / 收付汇画像 / 行业背景，并尝试抓取官网"""
    import concurrent.futures
    import requests as _req
    from services.llm_client import _get_secret

    api_key = _get_secret("TAVILY_API_KEY", "")
    empty = {"company": "", "payment": "", "industry_bg": "", "website": ""}
    if not api_key:
        return empty

    queries = {
        "company": (f"{company} 公司 主营业务 官网 简介", "advanced", 5),
        "payment": (f"{company} 跨境贸易 外汇收款 支付 {industry}", "advanced", 5),
        "industry_bg": (f"{industry} {country} 外贸支付 跨境收款 趋势 2025", "basic", 3),
    }

    def _single(key, query, depth, max_r):
        try:
            resp = _req.post(
                "https://api.tavily.com/search",
                json={"query": query, "max_results": max_r,
                      "search_depth": depth, "api_key": api_key},
                timeout=20,
            )
            if resp.status_code == 200:
                data = resp.json()
                lines, urls = [], []
                for r in data.get("results", [])[:max_r]:
                    lines.append(f"- [{r.get('title','')}] {r.get('content','')[:400]}")
                    if r.get("url"):
                        urls.append(r["url"])
                return key, "\n".join(lines), urls
        except Exception:
            pass
        return key, "", []

    results = dict(empty)
    official_urls = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(_single, k, q, d, m) for k, (q, d, m) in queries.items()]
        for fut in concurrent.futures.as_completed(futs):
            key, text, urls = fut.result()
            results[key] = text
            if key == "company" and urls:
                official_urls = urls

    # 尝试抓取官网首页原文（找不到或超时则静默跳过）
    if official_urls:
        try:
            resp = _req.post(
                "https://api.tavily.com/extract",
                json={"urls": [official_urls[0]], "api_key": api_key},
                timeout=20,
            )
            if resp.status_code == 200:
                raw = resp.json().get("results", [{}])[0].get("raw_content", "")
                if raw:
                    results["website"] = f"官网内容（{official_urls[0]}）：\n{raw[:800]}"
        except Exception:
            pass

    return results


# ---- KYC文档预审 System Prompt ----

KYC_REVIEW_SYSTEM_PROMPT = """你是一位跨境支付行业的KYC合规审核专家。

你的任务是对客户提交的KYC开户材料进行预审（Pre-Review），发现潜在问题并给出修改建议，
帮助销售人员在正式提交前减少退件和反复沟通。

## 审核维度

### 基本材料完整性
- 企业客户：营业执照、法人身份证、银行开户许可证、贸易证明、股东结构
- 个人客户：身份证、银行卡、贸易证明

### 常见退件原因（重点审查）
1. **证件有效期问题**：营业执照/身份证是否过期或即将过期（<3个月）
2. **信息一致性**：法人姓名、公司名称在不同文件间是否一致
3. **扫描质量**：是否提及模糊、截断、反光等问题
4. **经营范围匹配**：营业执照经营范围是否包含相关贸易/服务内容
5. **贸易背景真实性**：贸易证明是否与业务类型匹配
6. **股东穿透**：持股25%以上股东信息是否完整
7. **银行账户匹配**：开户行是否与公司名称对应

### 反洗钱红旗
- 注册地与经营地严重不一致
- 注册资本与预期流水极度不匹配
- 经营范围涉及敏感/限制行业
- 受益所有人信息模糊或链条过长

## 输出要求
返回JSON格式：
{
    "overall_status": "通过预审" | "需要修改" | "风险较高",
    "score": 0-100,
    "issues": [
        {
            "severity": "critical" | "warning" | "info",
            "category": "完整性" | "一致性" | "有效期" | "质量" | "合规" | "反洗钱",
            "detail": "具体问题描述",
            "suggestion": "修改建议"
        }
    ],
    "summary": "一段话总结预审结论和主要建议",
    "next_steps": ["建议的下一步操作列表"]
}

如果材料信息不够充分无法判断某些维度，在issues中以info级别标注，不要捏造问题。"""


def render_role_sales_support():
    """渲染销售支持角色页面"""
    st.title("销售支持 · AI作战指挥部")
    st.markdown(
        f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['md']};'>"
        "作战包生成、产品顾问、单证指南、合规风控、竞品分析、客户评分，一站式销售弹药库"
        "</span>",
        unsafe_allow_html=True,
    )

    # AI就绪状态
    if _is_mock_mode():
        st.warning("Mock模式（未连接AI）", icon="⚠️")
    else:
        st.success("AI已就绪", icon="✅")

    st.markdown("---")

    tab_battle, tab_product, tab_docs, tab_compliance, tab_competitor, tab_de = st.tabs(
        ["作战包", "产品顾问", "单证指南", "合规风控", "竞品分析", "🦾 数字员工"]
    )

    with tab_battle:
        _render_battle_pack_tab()

    with tab_product:
        _render_product_encyclopedia()

    with tab_docs:
        _render_document_guide()

    with tab_compliance:
        _render_compliance_risk()

    with tab_competitor:
        _render_competitor_radar()

    with tab_de:
        _render_digital_employee_tab()



# ============================================================
# Tab 1: 作战包（保留现有功能）
# ============================================================
def _render_battle_pack_tab():
    """作战包：一键生成完整销售弹药 + 拜访前调研"""
    from ui.pages.battle_station import (
        _render_customer_selector,
        _save_current_customer,
        _auto_save_and_link_battle_pack,
        _render_customer_battle_history,
        _render_customer_list_table,
        _generate_mock_battle_pack,
        _generate_real_battle_pack,
    )
    from ui.components.customer_input_form import render_customer_input_form
    from ui.components.error_handlers import (
        render_error,
        render_mock_fallback_notice,
    )

    # ---- K2.6集群模式开关（放在显眼位置）----
    col_swarm, _ = st.columns([1, 3])
    with col_swarm:
        use_swarm = st.toggle("🧠 K2.6集群模式", value=st.session_state.get("use_swarm_mode", False),
                              help="启用后，K2.6自动拆解任务并并行调度多个Agent执行")
    st.session_state.use_swarm_mode = use_swarm

    # ---- 拜访前调研 ----
    with st.expander("拜访前调研（输入公司名，AI自动搜索生成调研简报）", expanded=False):
        _render_pre_visit_research()

    st.markdown("---")

    # ---- 客户选择器 ----
    _render_customer_selector()

    # ---- 客户表单 ----
    context = render_customer_input_form()
    if "customer_context" not in st.session_state:
        st.session_state.customer_context = {}
    st.session_state.customer_context.update(context)
    st.markdown("---")

    # ---- 按钮区 ----
    col_btn1, col_btn2, col_btn3, _ = st.columns([1, 1, 1, 2])
    with col_btn1:
        btn_label = "🧠 Swarm生成" if use_swarm else "生成作战包"
        generate_clicked = st.button(btn_label, use_container_width=True, type="primary")
    with col_btn2:
        save_customer_clicked = st.button("保存客户", use_container_width=True)
    with col_btn3:
        clear_clicked = st.button("清空", use_container_width=True)

    if save_customer_clicked:
        if not context.get("company"):
            render_error("请输入客户公司名", "保存客户需要填写公司名。")
        else:
            _save_current_customer(context)

    if clear_clicked:
        st.session_state.battle_pack = None
        st.session_state.current_customer_id = None
        st.session_state.customer_context = {
            "company": "", "industry": "", "target_country": "",
            "monthly_volume": 0.0, "current_channel": "", "pain_points": [],
            "battlefield": "", "contact_name": "", "phone": "", "wechat": "",
            "email": "", "company_size": "", "years_established": 0,
            "main_products": "", "monthly_transactions": 0,
            "avg_transaction_amount": 0, "main_currency": "",
            "needs_hedging": False, "customer_stage": "初次接触",
            "next_followup_date": None, "notes": "",
        }
        st.rerun()

    if generate_clicked:
        if not context.get("company"):
            render_error("请输入客户公司名", "客户公司名是生成作战包的必填项。")
            return

        with st.spinner("AI 正在生成作战包，请稍候..."):
            if _is_mock_mode():
                battle_pack = _generate_mock_battle_pack(context)
            else:
                try:
                    battle_pack = _generate_real_battle_pack(context, use_swarm=use_swarm)
                except Exception as e:
                    render_mock_fallback_notice(
                        "真实模式调用失败，已自动回退到 Mock 模式",
                        f"错误：{str(e)[:200]}",
                    )
                    battle_pack = _generate_mock_battle_pack(context)
            st.session_state.battle_pack = battle_pack
            _auto_save_and_link_battle_pack(context, battle_pack)

        st.success("作战包生成完成！")
        st.balloons()

    # ---- 展示作战包（含方案PPT Tab） ----
    battle_pack = st.session_state.get("battle_pack")
    if battle_pack:
        st.markdown("---")

        from config import BATTLEFIELD_TYPES
        import html as _html
        from datetime import datetime

        bf_type = st.session_state.customer_context.get("battlefield", "increment")
        bf_info = BATTLEFIELD_TYPES.get(bf_type, {})
        bf_label = bf_info.get("label", bf_type)
        _company = _html.escape(str(st.session_state.customer_context.get("company", "")))
        _generated_at = battle_pack.get("generated_at", "")
        if _generated_at:
            try:
                _dt = datetime.fromisoformat(_generated_at.replace('Z', '+00:00'))
                _time_str = _dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                _time_str = _generated_at[:16] if len(_generated_at) >= 16 else _generated_at
        else:
            _time_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:{SPACING['md']};margin-bottom:{SPACING['lg']};'>"
            f"<span style='background:{BRAND_COLORS['primary']};color:#FFF;"
            f"padding:{SPACING['xs']} {SPACING['md']};border-radius:{RADIUS['lg']};font-size:{TYPE_SCALE['base']};font-weight:600;'>"
            f"{_html.escape(bf_label)}</span>"
            f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['base']};'>"
            f"为客户「{_company}」生成于 {_time_str}</span></div>",
            unsafe_allow_html=True,
        )

        from ui.components.battle_pack_display import (
            render_speech_tab,
            render_cost_tab,
            render_proposal_tab,
            render_objection_tab,
        )
        from ui.pages.design_studio import _render_ppt_tab

        tab_speech, tab_cost, tab_proposal, tab_objection, tab_ppt = st.tabs(
            ["话术", "成本对比", "方案", "异议预判", "方案PPT"]
        )

        with tab_speech:
            render_speech_tab(battle_pack.get("speech", {}))
        with tab_cost:
            render_cost_tab(battle_pack.get("cost", {}), st.session_state.customer_context)
        with tab_proposal:
            render_proposal_tab(battle_pack.get("proposal", {}))
        with tab_objection:
            render_objection_tab(battle_pack.get("objection", {}))
        with tab_ppt:
            _render_ppt_tab()

        # ---- 拜访结果追踪 ----
        st.markdown("---")
        st.markdown("#### 拜访结果标记")
        st.caption("拜访后标记结果，帮助系统学习哪些策略有效，持续优化输出。")

        visit_cols = st.columns([2, 2, 3])
        with visit_cols[0]:
            visit_result = st.selectbox(
                "拜访结果",
                options=["", "signed", "followup", "lost"],
                format_func=lambda x: {
                    "": "请选择...", "signed": "签约成功",
                    "followup": "需要跟进", "lost": "客户拒绝",
                }.get(x, x),
                key="bp_visit_result",
            )
        with visit_cols[1]:
            visit_reason = st.selectbox(
                "原因",
                options=["", "费率满意", "到账速度", "牌照信任", "竞品更优", "暂不需要", "流程复杂", "其他"],
                key="bp_visit_reason",
            )
        with visit_cols[2]:
            visit_notes = st.text_input(
                "备注（可选）", placeholder="补充说明...", key="bp_visit_notes",
            )

        helpful_agents = st.multiselect(
            "哪些模块在拜访中有帮助？",
            options=["话术", "成本对比", "方案", "异议预判"],
            key="bp_helpful_agents",
        )

        if st.button("提交拜访结果", type="primary", key="bp_submit_visit"):
            if not visit_result:
                st.warning("请选择拜访结果。")
            else:
                try:
                    from services.persistence import FeedbackPersistence
                    fp = FeedbackPersistence()
                    bp_id = f"{st.session_state.customer_context.get('company', 'unknown')}_{_time_str}"
                    fp.save_visit_result(
                        battle_pack_id=bp_id, result=visit_result,
                        reason=visit_reason, notes=visit_notes,
                        helpful_agents=helpful_agents,
                    )
                    result_labels = {"signed": "签约成功", "followup": "需要跟进", "lost": "客户拒绝"}
                    st.success(f"已记录拜访结果：{result_labels.get(visit_result, visit_result)}")
                except Exception as e:
                    st.error(f"保存失败：{str(e)[:100]}")

        _render_customer_battle_history()

    # ---- 底部：客户记录列表 ----
    _render_customer_list_table()


# ============================================================
# Tab 2: 产品百科
# ============================================================

# 产品知识数据（从knowledge目录结构化提取）
_PRODUCT_DB = {
    "b2b": {
        "label": "货物贸易(B2B)",
        "description": "面向B2B外贸企业，海外买家直接付款至Ksher本地账户 + 结汇入境人民币",
        "countries": {
            "thailand": {
                "name": "泰国", "currency": "THB", "fee_rate": "0.40%",
                "settlement": "T+1", "fx_benchmark": "泰国中行零售牌价",
                "account_type": "SCB本地THB账户", "withdraw": "CNH / USD",
                "selling_points": [
                    "SCB银行本地THB账户，买家付款如付国内款",
                    "T+1到账，比银行电汇快3-4天",
                    "费率0.05%~0.4%，比银行省90%",
                    "泰国持有BoT牌照，资金合规有保障",
                ],
                "speech": "您出口机械设备到泰国，银行电汇每笔¥150+1.5%手续费+3-5天到账。Ksher泰国本地账户，0.4%费率，T+1到账，一年省下来的钱够买一台新设备。",
            },
            "malaysia": {
                "name": "马来西亚", "currency": "MYR", "fee_rate": "0.40%",
                "settlement": "T+1", "fx_benchmark": "马来中行零售牌价",
                "account_type": "本地MYR账户", "withdraw": "CNH / USD",
                "selling_points": [
                    "本地MYR账户，BNM牌照监管",
                    "T+1到账，费率0.05%~0.4%",
                    "支持锁汇，7-90天远期合约",
                    "马来西亚电子产品/化工品贸易旺盛",
                ],
                "speech": "马来市场电子产品需求大，Ksher MYR本地账户直收，0.4%费率，T+1到账，比走银行电汇省一半以上。",
            },
            "philippines": {
                "name": "菲律宾", "currency": "PHP", "fee_rate": "0.40%",
                "settlement": "T+1", "fx_benchmark": "菲律宾中行零售牌价",
                "account_type": "本地PHP账户", "withdraw": "CNH / USD",
                "selling_points": [
                    "PHP本地账户，BSP牌照监管",
                    "最低手续费10 PHP/笔",
                    "菲律宾消费品/建材市场增长快",
                    "支持多币种归集",
                ],
                "speech": "菲律宾建材市场增速12%，Ksher PHP本地账户直收，T+1到账，比银行电汇快3天。",
            },
            "indonesia": {
                "name": "印尼", "currency": "IDR", "fee_rate": "0.40%",
                "settlement": "T+1", "fx_benchmark": "印尼中行零售牌价",
                "account_type": "本地IDR账户", "withdraw": "CNH / USD",
                "selling_points": [
                    "IDR本地账户，印尼持牌运营",
                    "最低手续费5000 IDR/笔",
                    "印尼是东南亚最大经济体",
                    "支持API对接自动对账",
                ],
                "speech": "印尼2.7亿人口，东南亚最大市场。Ksher IDR本地账户，你的印尼客户像转账国内一样方便，T+1到账。",
            },
            "vietnam": {
                "name": "越南", "currency": "VND", "fee_rate": "2.00%",
                "settlement": "T+1", "fx_benchmark": "Ksher报价汇率(XE中间价)",
                "account_type": "VND收款账户", "withdraw": "CNH / USD",
                "selling_points": [
                    "越南市场增速最快，制造业转移趋势",
                    "合规要求较高，Ksher全程合规保障",
                    "支持VND直收，无需中转行",
                ],
                "speech": "越南虽然费率稍高(2%)，但Ksher全程合规保障，不用担心退汇和冻卡风险。比走银行还是能省不少。",
                "_note": "⚠️ 越南费率较高(2%)，重点强调合规优势而非价格优势",
            },
            "hongkong": {
                "name": "香港(全球收)", "currency": "HKD", "fee_rate": "0.40%",
                "settlement": "T+1", "fx_benchmark": "中银香港零售牌价",
                "account_type": "HKD/CNH全球账户", "withdraw": "CNH / USD",
                "selling_points": [
                    "一个HKD账户收全球130+国家货款",
                    "简化财务对账，多币种归集",
                    "中银香港牌价，汇率透明",
                    "支持供应商付款：HKD付港/USD付全球",
                ],
                "speech": "如果你的客户分布在全球多个国家，一个Ksher香港账户就能收齐所有货款，免去开多个银行账户的麻烦。",
            },
            "europe": {
                "name": "欧洲", "currency": "EUR", "fee_rate": "0.40%",
                "settlement": "T+1", "fx_benchmark": "中银香港零售牌价",
                "account_type": "EUR收款账户", "withdraw": "CNH / USD",
                "selling_points": [
                    "支持EUR直收，覆盖欧洲主要市场",
                    "通过香港全球收通道",
                    "T+1到账，汇率透明",
                ],
                "speech": "出口欧洲的货款，Ksher EUR账户直收，T+1到账，费率0.4%，比银行电汇省60%以上。",
            },
        },
        "tier_pricing": {
            "S级": {"threshold": "≥50万USD/月", "rate": "0.05%", "vn_rate": "0.05%~0.2%"},
            "A级": {"threshold": "20-50万USD", "rate": "0.05%~0.1%", "vn_rate": "0.2%~0.3%"},
            "B级": {"threshold": "10-20万USD", "rate": "0.1%~0.2%", "vn_rate": "0.3%~0.4%"},
            "C级": {"threshold": "5-10万USD", "rate": "0.2%~0.3%", "vn_rate": "0.4%~0.5%"},
            "D/E/F级": {"threshold": "<5万USD", "rate": "0.3%~0.4%", "vn_rate": "0.5%~2%"},
        },
    },
    "b2c": {
        "label": "电商(B2C)",
        "description": "面向Shopee/Lazada/TikTok Shop等东南亚电商平台的中国卖家，本地币种收款+结汇入境",
        "countries": {
            "thailand": {
                "name": "泰国", "currency": "THB", "fee_rate": "0.80%",
                "settlement": "T+1", "fx_benchmark": "泰国中行零售牌价",
                "account_type": "SCB本地THB账户", "withdraw": "CNH",
                "min_fee": "15 THB/笔",
                "selling_points": [
                    "Shopee/Lazada泰国站直连收款",
                    "T+1到账，资金周转快",
                    "最低0.05%，量大优惠",
                    "泰国BoT牌照，合规无忧",
                ],
                "speech": "你在Shopee泰国站卖货，买家付泰铢，Ksher SCB账户直接收，T+1到账，费率最低0.05%。",
            },
            "malaysia": {
                "name": "马来西亚", "currency": "MYR", "fee_rate": "0.80%",
                "settlement": "T+1", "fx_benchmark": "马来中行零售牌价",
                "account_type": "本地MYR账户", "withdraw": "CNH",
                "min_fee": "1 MYR/笔",
                "selling_points": ["Shopee/Lazada马来站收款", "T+1到账", "最低0.05%", "BNM牌照"],
                "speech": "马来站单量起来了？Ksher MYR本地收款，0.8%标准费率，量大可谈到0.1%以下。",
            },
            "philippines": {
                "name": "菲律宾", "currency": "PHP", "fee_rate": "0.80%",
                "settlement": "T+1", "fx_benchmark": "菲律宾中行零售牌价",
                "account_type": "本地PHP账户", "withdraw": "CNH",
                "min_fee": "10 PHP/笔",
                "selling_points": ["TikTok Shop菲律宾站增长快", "T+1到账", "BSP牌照", "最低0.05%"],
                "speech": "TikTok Shop菲律宾站爆发期，Ksher PHP直收，T+1到账，先开个免费账户试试。",
            },
            "indonesia": {
                "name": "印尼", "currency": "IDR", "fee_rate": "0.80%",
                "settlement": "T+1", "fx_benchmark": "印尼中行零售牌价",
                "account_type": "本地IDR账户", "withdraw": "CNH",
                "min_fee": "5,000 IDR/笔",
                "selling_points": ["东南亚最大电商市场", "Shopee/Tokopedia覆盖", "T+1到账", "最低0.05%"],
                "speech": "印尼是东南亚最大电商市场，Ksher IDR本地账户，你的Shopee印尼站销售额直接收进来。",
            },
            "vietnam": {
                "name": "越南", "currency": "VND", "fee_rate": "1.00%",
                "settlement": "T+1", "fx_benchmark": "Ksher报价汇率",
                "account_type": "VND收款账户", "withdraw": "CNH",
                "selling_points": ["越南电商增速40%+", "Shopee/TikTok Shop覆盖", "合规收款无冻卡风险"],
                "speech": "越南电商增速惊人，Ksher合规收款，不用担心冻卡退汇。",
                "_note": "⚠️ 越南B2C费率1.0%，高于其他国家",
            },
        },
        "tier_pricing": {
            "S级": {"threshold": "≥50万USD/月", "rate": "0.05%", "vn_rate": "0.10%"},
            "A级": {"threshold": "20-50万USD", "rate": "0.05%~0.1%", "vn_rate": "0.1%~0.2%"},
            "B级": {"threshold": "10-20万USD", "rate": "0.1%~0.3%", "vn_rate": "0.2%~0.4%"},
            "C级": {"threshold": "5-10万USD", "rate": "0.3%~0.5%", "vn_rate": "0.4%~0.6%"},
            "D/E/F级": {"threshold": "<5万USD", "rate": "0.6%~0.8%", "vn_rate": "0.8%~1%"},
        },
    },
    "service": {
        "label": "服务贸易",
        "description": "面向物流/SaaS/游戏/教育/咨询/广告等非货物贸易场景的企业收款服务",
        "scenarios": {
            "logistics": {"name": "物流货代", "docs": "运输合同 + 发票 + 提单", "example": "中国物流公司收东南亚运费"},
            "saas": {"name": "SaaS订阅", "docs": "SaaS合同 + 发票", "example": "中国软件公司收东南亚企业订阅费"},
            "gaming": {"name": "游戏出海", "docs": "游戏发行合同 + 分成协议", "example": "游戏公司收海外玩家/渠道付款"},
            "education": {"name": "在线教育", "docs": "课程协议 + 发票", "example": "教育平台收东南亚学员学费"},
            "consulting": {"name": "咨询服务", "docs": "咨询合同 + 发票", "example": "咨询公司收海外客户咨询费"},
            "advertising": {"name": "广告代理", "docs": "广告合同 + 发票", "example": "广告公司收海外客户投放费"},
        },
        "pricing_note": "同B2B定价：标准0.40%，分层最低0.05%",
        "key_difference": "无实物货物交割 → 合同/发票替代报关单/提单",
        "selling_points": [
            "服务贸易不用报关单，合同+发票就能结汇",
            "比银行电汇省一半费用",
            "本地币种收款，客户付款更方便",
            "多币种归集，一个账户管多国",
            "API对接ERP/WMS，自动对账",
        ],
        "speech": "你们做服务贸易，传统银行要一堆单据还经常退汇。Ksher服务贸易收款，合同+发票就能结汇，费率0.4%封顶，比银行省一半。",
    },
}

# 增值产品
_ADDON_PRODUCTS = {
    "instant_settlement": {
        "name": "秒到宝(T+0)",
        "description": "当天到账增值服务，标准T+1升级为T+0",
        "selling_points": [
            "大促备货：早一天到账多一天采购时间",
            "供应商付款：不用等次日，当天回款当天付",
            "汇率锁定：早到账及时锁定有利汇率",
        ],
        "speech": "月流水100万，T+0比T+3每年省6万资金时间成本。够你多招一个运营。",
    },
    "supplier_payment": {
        "name": "供应商付款",
        "description": "账户内直接向全球供应商付款，无需转回国内银行",
        "pricing": "HKD付港：同结汇费率 | USD全球：$20(SHA)/$35(OUR)每笔",
        "selling_points": [
            "收款和付款一个账户搞定",
            "HKD付香港、USD付全球",
            "POBO代付：大额B2B定期付款",
        ],
        "speech": "收了东南亚货款还要付供应商？Ksher账户里直接付，不用先转回国内再换汇付出去。",
    },
    "fx_hedge": {
        "name": "锁汇工具",
        "description": "7-90天远期锁汇，规避汇率波动风险",
        "selling_points": [
            "锁定未来汇率，不怕市场波动",
            "7天到90天灵活选择",
            "特别适合大额B2B、账期长的客户",
        ],
        "speech": "做B2B的客户账期长，从下单到收款2-3个月，汇率波动可能吃掉全部利润。Ksher锁汇工具，下单时就锁定汇率。",
    },
}


def _render_product_encyclopedia():
    """产品百科 + AI产品顾问"""
    from ui.components.error_handlers import render_copy_button

    st.markdown("**产品顾问**")
    st.caption("手动查询产品信息，或使用AI智能推荐")

    # AI产品顾问（置顶）
    _render_ai_product_advisor()

    st.markdown("---")
    st.subheader("产品手册（手动查询）")
    st.caption("按贸易类型和国家查看产品能力、费率、卖点、话术")

    # 贸易类型选择
    trade_type = st.radio(
        "选择贸易类型",
        options=["b2b", "b2c", "service"],
        format_func=lambda x: _PRODUCT_DB[x]["label"],
        horizontal=True,
        key="prod_trade_type",
    )

    trade_data = _PRODUCT_DB[trade_type]
    st.info(trade_data["description"])

    if trade_type in ("b2b", "b2c"):
        # 国家选择
        country_keys = list(trade_data["countries"].keys())
        country_labels = {k: trade_data["countries"][k]["name"] for k in country_keys}
        selected_country = st.selectbox(
            "选择国家/地区",
            options=country_keys,
            format_func=lambda k: country_labels[k],
            key="prod_country",
        )

        country = trade_data["countries"][selected_country]

        # 产品能力卡
        st.markdown("---")
        st.markdown(f"### {country['name']} · {trade_data['label']}")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("标准费率", country["fee_rate"])
        with col2:
            st.metric("到账时效", country["settlement"])
        with col3:
            st.metric("币种", country["currency"])
        with col4:
            st.metric("提现", country.get("withdraw", "CNH"))

        # 详细信息
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**账户类型**")
            st.markdown(f"- {country['account_type']}")
            st.markdown("**汇率基准**")
            st.markdown(f"- {country['fx_benchmark']}")
            if country.get("min_fee"):
                st.markdown("**最低手续费**")
                st.markdown(f"- {country['min_fee']}")
            if country.get("_note"):
                st.warning(country["_note"])

        with c2:
            st.markdown("**核心卖点**")
            for sp in country["selling_points"]:
                st.markdown(f"- ✅ {sp}")

        # 一句话话术
        st.markdown("---")
        st.markdown("**场景话术（可直接复制）**")
        st.markdown(
            f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['accent'])},0.06);border-left:3px solid {BRAND_COLORS['accent']};"
            f"padding:{SPACING['md']} {SPACING['md']};border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;font-size:{TYPE_SCALE['md']};'>"
            f"💬 {country['speech']}</div>",
            unsafe_allow_html=True,
        )
        render_copy_button(country["speech"])

        # 费率阶梯表
        st.markdown("---")
        st.markdown("**分层定价**")
        tier_data = trade_data["tier_pricing"]
        tier_rows = []
        for tier, info in tier_data.items():
            tier_rows.append(f"| {tier} | {info['threshold']} | {info['rate']} | {info.get('vn_rate', '-')} |")
        st.markdown(
            "| 等级 | 月交易量(USD) | 泰/马/菲/印/欧/港 | 越南 |\n"
            "|------|-------------|-----------------|------|\n"
            + "\n".join(tier_rows)
        )

    else:
        # 服务贸易：按场景展示
        st.markdown("---")
        st.subheader("服务贸易支持场景")

        st.markdown(f"**核心区别**：{trade_data['key_difference']}")
        st.markdown(f"**定价**：{trade_data['pricing_note']}")

        st.markdown("")
        for key, scenario in trade_data["scenarios"].items():
            st.markdown(
                f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['surface'])},0.8);padding:{SPACING['sm']} {SPACING['md']};"
                f"border-radius:{RADIUS['md']};margin:{SPACING['xs']} 0;font-size:{TYPE_SCALE['base']};'>"
                f"<b>{scenario['name']}</b>：{scenario['example']}<br>"
                f"<span style='color:{BRAND_COLORS['text_secondary']};'>所需材料：{scenario['docs']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("**核心卖点**")
        for sp in trade_data["selling_points"]:
            st.markdown(f"- ✅ {sp}")

        st.markdown("**场景话术**")
        st.markdown(
            f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['accent'])},0.06);border-left:3px solid {BRAND_COLORS['accent']};"
            f"padding:{SPACING['md']} {SPACING['md']};border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;font-size:{TYPE_SCALE['md']};'>"
            f"💬 {trade_data['speech']}</div>",
            unsafe_allow_html=True,
        )
        render_copy_button(trade_data["speech"])

    # 增值产品
    st.markdown("---")
    st.markdown("**增值产品**")
    addon_cols = st.columns(3)
    for i, (key, addon) in enumerate(_ADDON_PRODUCTS.items()):
        with addon_cols[i]:
            with st.expander(addon["name"], expanded=False):
                st.caption(addon["description"])
                for sp in addon["selling_points"]:
                    st.markdown(f"- {sp}")
                if addon.get("pricing"):
                    st.markdown(f"**费用**：{addon['pricing']}")


# ============================================================
# Tab 3: 单证指南
# ============================================================

_GOODS_TRADE_DOCS = [
    {"name": "购销合同", "en": "Sales Contract", "when": "交易前", "desc": "买卖双方主合同，明确货物、价格、付款条件", "required": True},
    {"name": "形式发票(PI)", "en": "Proforma Invoice", "when": "发货前", "desc": "初步报价单，列明货物、数量、价格。买家据此安排付款或申请进口许可", "required": True},
    {"name": "商业发票(CI)", "en": "Commercial Invoice", "when": "发货时", "desc": "正式交易发票，含实际交易金额、贸易条款(FOB/CIF)。结汇必备文件", "required": True},
    {"name": "报关单(CD)", "en": "Customs Declaration", "when": "出口后", "desc": "中国海关出具，证明货物合法出口。B2B结汇的核心凭证", "required": True},
    {"name": "提单(B/L)", "en": "Bill of Lading", "when": "运输中", "desc": "海运：海运提单 / 空运：航空运单(AWB) / 陆运：运输单。证明货物在途", "required": True},
    {"name": "装箱单", "en": "Packing List", "when": "发货时", "desc": "货物包装明细：重量、尺寸、唛头", "required": False},
    {"name": "水单", "en": "Bank Slip", "when": "收款后", "desc": "付款/收款凭证，用于记账和报税", "required": False},
]

_SERVICE_TRADE_DOCS = [
    {"name": "服务合同", "en": "Service Agreement", "when": "服务开始前", "desc": "替代购销合同，需明确描述服务内容、金额、期限", "required": True},
    {"name": "服务发票", "en": "Service Invoice", "when": "服务完成后", "desc": "替代商业发票，金额需与合同一致", "required": True},
    {"name": "服务交付证明", "en": "Delivery Proof", "when": "服务完成后", "desc": "替代提单。可以是验收报告、系统日志、完成证书", "required": True},
]

_ECOMMERCE_DOCS = [
    {"name": "平台店铺链接", "en": "Store URL", "when": "开户时", "desc": "证明合法电商经营活动", "required": True},
    {"name": "平台协议/合同", "en": "Platform Agreement", "when": "开户时", "desc": "卖家入驻协议", "required": True},
    {"name": "平台交易记录", "en": "Transaction Records", "when": "结算时", "desc": "从Shopee/Lazada/TikTok Shop后台导出", "required": True},
    {"name": "物流凭证", "en": "Shipping Proof", "when": "结算时", "desc": "平台生成的发货确认（货物类目需要）", "required": False},
]

_KYC_DOCS = {
    "enterprise": [
        {"name": "营业执照", "desc": "中国大陆企业营业执照（彩色扫描件）", "required": True},
        {"name": "法人身份证", "desc": "正反面（彩色扫描件）", "required": True},
        {"name": "银行开户许可证", "desc": "或基本存款账户信息", "required": True},
        {"name": "贸易证明", "desc": "电商平台店铺链接/合同/发票（证明真实贸易背景）", "required": True},
        {"name": "股东结构", "desc": "持股25%以上股东信息（AML反洗钱要求）", "required": True},
    ],
    "individual": [
        {"name": "身份证", "desc": "正反面", "required": True},
        {"name": "银行卡", "desc": "用于提现", "required": True},
        {"name": "贸易证明", "desc": "店铺链接/交易记录", "required": True},
    ],
}


def _render_document_guide():
    """单证指南 + AI智能材料顾问"""
    st.markdown("**单证指南**")
    st.caption("AI智能分析材料需求，或手动查看标准清单")

    # AI智能材料顾问（置顶）
    _render_smart_doc_advisor()

    st.markdown("---")
    st.subheader("标准单证清单（手动查询）")
    st.caption("按贸易类型查看客户需要准备的全部材料，支持交互式勾选追踪")

    # 贸易类型选择
    doc_trade = st.radio(
        "选择贸易类型",
        options=["goods", "service", "ecommerce"],
        format_func=lambda x: {"goods": "货物贸易", "service": "服务贸易", "ecommerce": "电商"}[x],
        horizontal=True,
        key="doc_trade_type",
    )

    # 阶段选择
    stage = st.radio(
        "选择阶段",
        options=["onboarding", "first_tx", "routine"],
        format_func=lambda x: {"onboarding": "开户阶段", "first_tx": "首笔收款", "routine": "日常收款"}[x],
        horizontal=True,
        key="doc_stage",
    )

    st.markdown("---")

    # 根据贸易类型展示不同清单
    if doc_trade == "goods":
        _render_goods_docs(stage)
    elif doc_trade == "service":
        _render_service_docs(stage)
    else:
        _render_ecommerce_docs(stage)

    # 单证流转图
    st.markdown("---")
    st.markdown("**单证流转图**")
    if doc_trade == "goods":
        st.markdown(
            "```\n"
            "合同签订 → PI开具 → 备货发运(B/L) → 出口报关(CD) → CI开具\n"
            "    → 买家付款 → Ksher收款 → 结汇(需CI+CD) → 入账(水单)\n"
            "```"
        )
        st.info("💡 **结汇关键**：货物贸易结汇必须提供 商业发票(CI) + 报关单(CD)，缺一不可。")
    elif doc_trade == "service":
        st.markdown(
            "```\n"
            "合同签订 → 服务交付 → 发票开具 → 买家付款\n"
            "    → Ksher收款 → 结汇(需合同+发票) → 入账(水单)\n"
            "```"
        )
        st.success("✅ **服务贸易简化**：不需要报关单、不需要提单、不需要装箱单。合同+发票即可结汇。")
    else:
        st.markdown(
            "```\n"
            "平台开店 → 上架商品 → 买家下单付款 → 平台结算至Ksher\n"
            "    → 结汇(平台交易记录) → 入账\n"
            "```"
        )
        st.info("💡 **电商简化**：以平台交易记录作为贸易背景证明，无需单独准备贸易单据。")

    # PI/CI字段说明
    if doc_trade == "goods":
        st.markdown("---")
        with st.expander("PI/CI 必须包含的字段", expanded=False):
            st.markdown("""
| 字段 | 说明 | 示例 |
|------|------|------|
| 卖方信息 | 公司名称、地址、联系方式 | ABC Trading Co., Ltd. |
| 买方信息 | 公司名称、地址 | XYZ Import Co., Thailand |
| 发票编号 | 唯一编号 | INV-2026-0001 |
| 日期 | 开具日期 | 2026-04-19 |
| 货物描述 | 品名、型号、HS编码 | LED Lights, HS 9405.40 |
| 数量 | 数量及单位 | 10,000 PCS |
| 单价 | 单位价格及币种 | USD 2.50/PCS |
| 总价 | 合计金额 | USD 25,000.00 |
| 贸易条款 | FOB/CIF/EXW等 | FOB Shenzhen |
| 付款方式 | 付款条件 | T/T 30 days after shipment |
""")


def _render_goods_docs(stage: str):
    """渲染货物贸易单证清单"""
    st.subheader("货物贸易 — 所需单证")

    if stage == "onboarding":
        st.markdown("**开户阶段：KYC材料**")
        _render_kyc_checklist("enterprise")
    else:
        st.markdown(f"**{'首笔收款' if stage == 'first_tx' else '日常收款'}：贸易单证**")
        _render_doc_checklist(_GOODS_TRADE_DOCS, f"goods_{stage}")

    # 关键提醒
    st.markdown("")
    st.warning("⚠️ **货物贸易核心要求**：结汇必须同时提供 **商业发票(CI)** 和 **报关单(CD)**。缺少任何一项都无法完成外汇结算。")


def _render_service_docs(stage: str):
    """渲染服务贸易单证清单"""
    st.subheader("服务贸易 — 所需单证")

    if stage == "onboarding":
        st.markdown("**开户阶段：KYC材料**")
        _render_kyc_checklist("enterprise")
    else:
        st.markdown(f"**{'首笔收款' if stage == 'first_tx' else '日常收款'}：服务凭证**")
        _render_doc_checklist(_SERVICE_TRADE_DOCS, f"service_{stage}")

    # 与货物贸易的对比
    st.markdown("")
    st.success(
        "✅ **服务贸易 vs 货物贸易**\n\n"
        "- ❌ 不需要报关单(CD) — 服务贸易最大简化点\n"
        "- ❌ 不需要提单(B/L) — 无物流运输\n"
        "- ❌ 不需要装箱单 — 无实物商品\n"
        "- ✅ 服务合同需**明确描述服务内容**\n"
        "- ✅ 付款方与合同签署方需**一致或提供关联证明**"
    )

    # 按场景展示所需材料
    st.markdown("---")
    st.markdown("**各场景具体材料要求**")
    scenarios = _PRODUCT_DB["service"]["scenarios"]
    for key, s in scenarios.items():
        st.markdown(
            f"- **{s['name']}**：{s['docs']}"
        )


def _render_ecommerce_docs(stage: str):
    """渲染电商单证清单"""
    st.subheader("电商 — 所需材料")

    if stage == "onboarding":
        st.markdown("**开户阶段：KYC材料 + 平台信息**")
        _render_kyc_checklist("enterprise")
        st.markdown("---")
        st.markdown("**平台相关材料**")
        _render_doc_checklist(_ECOMMERCE_DOCS[:2], f"ecom_onboard")
    else:
        st.markdown(f"**{'首笔收款' if stage == 'first_tx' else '日常收款'}：平台凭证**")
        _render_doc_checklist(_ECOMMERCE_DOCS, f"ecom_{stage}")

    st.markdown("")
    st.info(
        "💡 **电商特点**\n\n"
        "- 以平台交易记录替代传统贸易单据\n"
        "- 支持平台：Shopee / Lazada / TikTok Shop / Amazon\n"
        "- 货物类目需提供物流凭证，虚拟商品类目可免"
    )


def _render_doc_checklist(docs: list, prefix: str):
    """渲染可勾选的单证清单"""
    checked_count = 0
    total_required = sum(1 for d in docs if d["required"])

    for i, doc in enumerate(docs):
        key = f"doc_check_{prefix}_{i}"
        required_tag = "必需" if doc["required"] else "可选"
        color = BRAND_COLORS["primary"] if doc["required"] else BRAND_COLORS["text_secondary"]
        checked = st.checkbox(
            f"**{doc['name']}** ({doc['en']}) — `{required_tag}` · {doc['when']}",
            key=key,
            help=doc["desc"],
        )
        if checked and doc["required"]:
            checked_count += 1

    # 进度条
    if total_required > 0:
        progress = checked_count / total_required
        st.progress(progress, text=f"必需材料完成度：{checked_count}/{total_required}")


def _render_kyc_checklist(customer_type: str):
    """渲染KYC材料清单"""
    docs = _KYC_DOCS.get(customer_type, _KYC_DOCS["enterprise"])
    checked_count = 0
    total = len(docs)

    for i, doc in enumerate(docs):
        key = f"kyc_check_{customer_type}_{i}"
        checked = st.checkbox(
            f"**{doc['name']}** — {doc['desc']}",
            key=key,
        )
        if checked:
            checked_count += 1

    st.progress(checked_count / total if total > 0 else 0, text=f"KYC材料完成度：{checked_count}/{total}")


# ============================================================
# Tab 4: 合规风控
# ============================================================

_COUNTRY_COMPLIANCE = {
    "thailand": {
        "name": "泰国", "regulator": "BoT (泰国央行)",
        "license": "MSB支付牌照", "difficulty": "简单",
        "notes": "SCB本地账户，监管环境友好，审批流程顺畅",
        "min_fee": "15 THB/笔",
    },
    "malaysia": {
        "name": "马来西亚", "regulator": "BNM (马来央行)",
        "license": "MSB支付牌照", "difficulty": "简单",
        "notes": "MYR本地清算，近期有新客户普调",
        "min_fee": "1 MYR/笔",
    },
    "philippines": {
        "name": "菲律宾", "regulator": "BSP (菲律宾央行)",
        "license": "支付牌照", "difficulty": "中等",
        "notes": "BSP监管严格，PHP交易有最低手续费要求",
        "min_fee": "10 PHP/笔",
    },
    "indonesia": {
        "name": "印尼", "regulator": "BI (印尼央行)",
        "license": "需通过本地持牌机构", "difficulty": "中等",
        "notes": "必须通过本地持牌实体运营，IDR最低5000/笔",
        "min_fee": "5,000 IDR/笔",
    },
    "vietnam": {
        "name": "越南", "regulator": "SBV (越南国家银行)",
        "license": "合作模式", "difficulty": "复杂",
        "notes": "监管环境最复杂，B2B标准费率2%，所有交易需加强审查",
        "min_fee": "—",
    },
    "hongkong": {
        "name": "香港", "regulator": "HKMA (金管局)",
        "license": "SVF牌照", "difficulty": "简单",
        "notes": "全球收通道，中银香港零售牌价，可收全球130+国家款项",
        "min_fee": "—",
    },
}

_PROHIBITED_INDUSTRIES = [
    "博彩/赌博", "虚拟货币/加密货币交易", "成人内容/色情",
    "军火/武器", "毒品/违禁品", "传销/资金盘",
]

_RESTRICTED_INDUSTRIES = [
    "游戏（需审核游戏类型和版号）",
    "虚拟商品（需证明真实交易背景）",
    "大宗商品期货（需额外合规审核）",
    "跨境金融服务（需持牌证明）",
]


def _render_compliance_risk():
    """合规风控：AI风险报告 + KYC预审 + 风险评估 + 国别合规"""
    st.markdown("**合规风控**")
    st.caption("AI风险评估报告、KYC预审、快速评估、国别合规要点")

    # AI风险评估报告（置顶）
    _render_ai_risk_report()

    # 快速评估输入
    st.subheader("客户快速评估")
    col1, col2 = st.columns(2)
    with col1:
        biz_type = st.selectbox(
            "业务类型",
            options=["一般贸易", "跨境电商", "服务贸易", "物流货代", "游戏出海", "SaaS", "其他"],
            key="comp_biz_type",
        )
        monthly_vol = st.number_input(
            "预估月流水(万美元)", value=10.0, min_value=0.0, step=5.0,
            key="comp_monthly_vol",
        )
    with col2:
        target_country = st.selectbox(
            "目标国家",
            options=list(_COUNTRY_COMPLIANCE.keys()),
            format_func=lambda k: _COUNTRY_COMPLIANCE[k]["name"],
            key="comp_country",
        )
        customer_type = st.radio(
            "客户类型", options=["enterprise", "individual"],
            format_func=lambda x: {"enterprise": "企业客户", "individual": "个人客户"}[x],
            horizontal=True,
            key="comp_customer_type",
        )

    if st.button("评估风险等级", type="primary", key="comp_assess"):
        st.markdown("---")
        _render_risk_assessment(biz_type, monthly_vol, target_country, customer_type)

    # KYC材料清单
    st.markdown("---")
    st.subheader("KYC开户材料")
    kyc_tab = st.radio(
        "客户类型",
        options=["enterprise", "individual"],
        format_func=lambda x: {"enterprise": "企业客户", "individual": "个人客户"}[x],
        horizontal=True,
        key="comp_kyc_type",
    )
    docs = _KYC_DOCS[kyc_tab]
    for doc in docs:
        st.markdown(
            f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['surface'])},0.8);padding:{SPACING['sm']} {SPACING['md']};"
            f"border-radius:{RADIUS['md']};margin:{SPACING['xs']} 0;font-size:{TYPE_SCALE['base']};'>"
            f"<b>{doc['name']}</b> — {doc['desc']}"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("")
    st.caption("开户流程：提交资料(Day1) → 初审(Day2) → 终审(Day3) → 开通(Day3-5)")

    # KYC材料预审
    st.markdown("---")
    _render_kyc_prereview()

    # 国别合规
    st.markdown("---")
    st.subheader("国别合规要点")
    for key, info in _COUNTRY_COMPLIANCE.items():
        difficulty_color = {
            "简单": BRAND_COLORS["accent"],
            "中等": BRAND_COLORS["warning"],
            "复杂": BRAND_COLORS["primary"],
        }.get(info["difficulty"], BRAND_COLORS["text_secondary"])
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:{SPACING['md']};"
            f"padding:{SPACING['sm']} 0;border-bottom:1px solid #eee;'>"
            f"<b style='min-width:5rem;'>{info['name']}</b>"
            f"<span style='background:{difficulty_color};color:#fff;padding:{SPACING['xs']} {SPACING['sm']};"
            f"border-radius:{RADIUS['lg']};font-size:{TYPE_SCALE['xs']};'>{info['difficulty']}</span>"
            f"<span style='font-size:{TYPE_SCALE['base']};'>{info['regulator']} · {info['license']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"  {info['notes']}")

    # 交易监控红线
    st.markdown("---")
    st.subheader("交易监控红线")
    red_lines = [
        ("单笔>10万美金（服务贸易）", "触发加强审查"),
        ("申报流水与实际偏差>50%", "可能降级或暂停账户"),
        ("付款方与合同方不一致", "需提供关联证明"),
        ("突发大额交易", "可能触发反洗钱审查"),
        ("贸易背景不真实", "严重：账户冻结/关闭"),
    ]
    for trigger, consequence in red_lines:
        st.markdown(
            f"<div style='display:flex;gap:{SPACING['sm']};padding:{SPACING['xs']} 0;font-size:{TYPE_SCALE['base']};'>"
            f"<span style='color:{BRAND_COLORS['primary']};'>⚠️</span>"
            f"<b>{trigger}</b> → <span style='color:{BRAND_COLORS['text_secondary']};'>{consequence}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # 禁止/限制行业
    st.markdown("---")
    col_p, col_r = st.columns(2)
    with col_p:
        st.subheader("🚫 禁止行业")
        for ind in _PROHIBITED_INDUSTRIES:
            st.markdown(f"- ❌ {ind}")
    with col_r:
        st.subheader("⚠️ 限制行业（需特审）")
        for ind in _RESTRICTED_INDUSTRIES:
            st.markdown(f"- ⚠️ {ind}")


def _render_kyc_prereview():
    """KYC材料预审：上传客户材料 → AI预审 → 给出修改建议"""
    st.subheader("📋 KYC材料预审")
    st.caption("上传客户准备的KYC材料，AI预审发现潜在问题，减少退件和反复沟通")

    # 客户基本信息（辅助AI判断）
    col1, col2 = st.columns(2)
    with col1:
        prereview_company = st.text_input(
            "客户公司名", key="prereview_company", placeholder="选填，帮助AI交叉验证"
        )
        prereview_biz = st.selectbox(
            "业务类型",
            options=["一般贸易", "跨境电商", "服务贸易", "物流货代", "游戏出海", "SaaS", "其他"],
            key="prereview_biz",
        )
    with col2:
        prereview_type = st.radio(
            "客户类型", options=["enterprise", "individual"],
            format_func=lambda x: {"enterprise": "企业客户", "individual": "个人客户"}[x],
            horizontal=True,
            key="prereview_cust_type",
        )
        prereview_country = st.selectbox(
            "目标国家",
            options=list(_COUNTRY_COMPLIANCE.keys()),
            format_func=lambda k: _COUNTRY_COMPLIANCE[k]["name"],
            key="prereview_country",
        )

    # 文件上传
    st.markdown("**上传材料**")
    st.caption("支持图片（JPG/PNG）和PDF，可同时上传多个文件")
    uploaded_files = st.file_uploader(
        "选择KYC材料文件",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True,
        key="prereview_files",
    )

    # 补充说明
    prereview_notes = st.text_area(
        "补充说明（选填）",
        placeholder="如：客户营业执照刚换发过，法人近期有变更…",
        height=80,
        key="prereview_notes",
    )

    if uploaded_files:
        st.caption(f"已选择 {len(uploaded_files)} 个文件：" +
                   "、".join(f.name for f in uploaded_files))

    if st.button("开始AI预审", type="primary", key="prereview_submit",
                 disabled=not uploaded_files, help="请先上传KYC文件"):
        _run_kyc_prereview(
            uploaded_files, prereview_company, prereview_biz,
            prereview_type, prereview_country, prereview_notes
        )

    # 显示历史预审结果
    result = st.session_state.get("prereview_result")
    if result:
        _display_prereview_result(result)


def _run_kyc_prereview(files, company, biz_type, customer_type, country, notes):
    """执行KYC预审"""
    import io

    with st.spinner("AI正在审核材料..."):
        # 构造材料描述
        file_descriptions = []
        for f in files:
            file_info = f"文件名: {f.name}, 类型: {f.type}, 大小: {f.size/1024:.1f}KB"
            # 对于文本型PDF，尝试提取文字信息
            if f.type == "application/pdf":
                try:
                    import PyPDF2
                    reader = PyPDF2.PdfReader(io.BytesIO(f.read()))
                    text_content = ""
                    for page in reader.pages[:5]:  # 最多5页
                        text_content += page.extract_text() or ""
                    f.seek(0)
                    if text_content.strip():
                        file_info += f"\n内容摘要（前1500字）:\n{text_content[:1500]}"
                    else:
                        file_info += "\n（PDF为扫描件，无法提取文字）"
                except Exception:
                    f.seek(0)
                    file_info += "\n（PDF解析失败，可能是扫描件）"
            file_descriptions.append(file_info)

        # 组装用户消息
        country_info = _COUNTRY_COMPLIANCE.get(country, {})
        kyc_docs = _KYC_DOCS.get(customer_type, _KYC_DOCS["enterprise"])
        required_docs = [d["name"] for d in kyc_docs]

        user_msg = f"""请对以下客户的KYC开户材料进行预审。

## 客户信息
- 公司名称: {company or '未提供'}
- 业务类型: {biz_type}
- 客户类型: {'企业客户' if customer_type == 'enterprise' else '个人客户'}
- 目标国家: {country_info.get('name', country)}（监管机构: {country_info.get('regulator', '未知')}，合规难度: {country_info.get('difficulty', '未知')}）

## 所需材料清单
{chr(10).join(f'- {d["name"]}: {d["desc"]}' for d in kyc_docs)}

## 已上传材料
{chr(10).join(f'### 文件{i+1}: {desc}' for i, desc in enumerate(file_descriptions))}

## 补充说明
{notes or '无'}

请根据已上传材料和所需清单进行预审，按JSON格式输出审核结果。"""

        if _is_mock_mode():
            # Mock模式
            result = _mock_prereview_result(company, customer_type, len(files), required_docs)
        else:
            raw = _llm_call(KYC_REVIEW_SYSTEM_PROMPT, user_msg, agent_name="knowledge")
            result = _parse_json_safe(raw)
            if not result:
                result = _mock_prereview_result(company, customer_type, len(files), required_docs)

        st.session_state["prereview_result"] = result


def _mock_prereview_result(company: str, customer_type: str, file_count: int,
                           required_docs: list) -> dict:
    """Mock预审结果"""
    company_name = company or "示例公司"
    issues = [
        {
            "severity": "warning",
            "category": "完整性",
            "detail": f"已上传{file_count}个文件，但{customer_type == 'enterprise' and '企业' or '个人'}客户需要{len(required_docs)}项材料，请确认是否齐全",
            "suggestion": f"请对照清单确认以下材料均已提供：{'、'.join(required_docs)}"
        },
        {
            "severity": "info",
            "category": "有效期",
            "detail": "建议确认营业执照和身份证的有效期",
            "suggestion": "如证件将在3个月内到期，建议客户先完成换证再申请开户"
        },
        {
            "severity": "warning",
            "category": "一致性",
            "detail": "请确认各文件中的公司名称、法人姓名完全一致",
            "suggestion": "特别注意：营业执照上的公司名称须与银行开户许可证完全一致（含标点符号）"
        },
    ]

    if customer_type == "enterprise":
        issues.append({
            "severity": "info",
            "category": "合规",
            "detail": "企业客户需提供持股25%以上股东信息",
            "suggestion": "如股权结构复杂（多层嵌套），建议提供完整的股权穿透图"
        })

    return {
        "overall_status": "需要修改",
        "score": 65,
        "issues": issues,
        "summary": f"⚠️ 当前为模拟预审模式。{company_name}的材料初步审核发现{len(issues)}个关注点，"
                   f"主要涉及材料完整性和信息一致性。建议按照下方修改建议逐项核对后再正式提交。",
        "next_steps": [
            "对照KYC清单逐项确认材料齐全",
            "核对各文件间的公司名称、法人信息一致性",
            "确认证件有效期充足（>3个月）",
            "准备好后可正式提交至合规部门审核",
        ],
    }


def _display_prereview_result(result: dict):
    """展示预审结果"""
    st.markdown("---")
    st.subheader("预审结果")

    # 总体状态卡片
    status = result.get("overall_status", "未知")
    score = result.get("score", 0)
    status_config = {
        "通过预审": (BRAND_COLORS["accent"], "✅"),
        "需要修改": (BRAND_COLORS["warning"], "⚠️"),
        "风险较高": (BRAND_COLORS["primary"], "🚨"),
    }
    color, icon = status_config.get(status, (BRAND_COLORS["text_secondary"], "❓"))

    st.markdown(
        f"<div style='text-align:center;padding:{SPACING['md']};background:rgba({hex_to_rgb(color)},0.08);"
        f"border:2px solid {color};border-radius:{RADIUS['lg']};margin-bottom:{SPACING['md']};'>"
        f"<div style='font-size:{TYPE_SCALE['xl']};font-weight:700;color:{color};'>{icon} {status}</div>"
        f"<div style='font-size:{TYPE_SCALE['display']};font-weight:700;color:{color};margin:{SPACING['xs']} 0;'>{score}分</div>"
        f"<div style='font-size:{TYPE_SCALE['base']};color:{BRAND_COLORS['text_secondary']};'>"
        f"预审评分（100分为完全合规）</div></div>",
        unsafe_allow_html=True,
    )

    # 总结
    summary = result.get("summary", "")
    if summary:
        st.info(summary)

    # 问题列表
    issues = result.get("issues", [])
    if issues:
        st.markdown("**发现的问题：**")
        severity_icons = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
        severity_labels = {"critical": "严重", "warning": "需注意", "info": "建议"}

        for issue in issues:
            sev = issue.get("severity", "info")
            icon = severity_icons.get(sev, "🔵")
            label = severity_labels.get(sev, "信息")
            cat = issue.get("category", "")

            st.markdown(
                f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['surface'])},0.8);padding:{SPACING['sm']} {SPACING['md']};"
                f"border-radius:{RADIUS['md']};margin:{SPACING['sm']} 0;border-left:3px solid {color};'>"
                f"<div style='font-size:{TYPE_SCALE['base']};'>"
                f"{icon} <b>[{label}·{cat}]</b> {issue.get('detail', '')}"
                f"</div>"
                f"<div style='font-size:{TYPE_SCALE['base']};color:{BRAND_COLORS['text_secondary']};"
                f"margin-top:{SPACING['xs']};padding-left:{SPACING['lg']};'>"
                f"💡 {issue.get('suggestion', '')}"
                f"</div></div>",
                unsafe_allow_html=True,
            )

    # 下一步建议
    next_steps = result.get("next_steps", [])
    if next_steps:
        st.markdown("**建议下一步：**")
        for i, step in enumerate(next_steps, 1):
            st.markdown(f"{i}. {step}")

    # 操作按钮
    col1, col2 = st.columns(2)
    with col1:
        # 导出预审报告
        report_text = _format_prereview_report(result)
        st.download_button(
            "📄 下载预审报告",
            data=report_text,
            file_name="KYC预审报告.txt",
            mime="text/plain",
            key="prereview_download",
        )
    with col2:
        if st.button("🔄 重新预审", key="prereview_reset"):
            st.session_state.pop("prereview_result", None)
            st.rerun()


def _format_prereview_report(result: dict) -> str:
    """格式化预审报告为纯文本"""
    lines = [
        "=" * 50,
        "KYC 材料预审报告",
        "=" * 50,
        "",
        f"预审状态: {result.get('overall_status', '未知')}",
        f"预审评分: {result.get('score', 0)} / 100",
        "",
        "--- 总结 ---",
        result.get("summary", ""),
        "",
        "--- 发现问题 ---",
    ]

    severity_labels = {"critical": "严重", "warning": "需注意", "info": "建议"}
    for i, issue in enumerate(result.get("issues", []), 1):
        sev = severity_labels.get(issue.get("severity", "info"), "信息")
        lines.append(f"\n{i}. [{sev}·{issue.get('category', '')}]")
        lines.append(f"   问题: {issue.get('detail', '')}")
        lines.append(f"   建议: {issue.get('suggestion', '')}")

    lines.append("\n--- 建议下一步 ---")
    for i, step in enumerate(result.get("next_steps", []), 1):
        lines.append(f"{i}. {step}")

    lines.append("\n" + "=" * 50)
    lines.append("本报告由AI预审生成，仅供参考，最终以合规部门审核结果为准。")

    return "\n".join(lines)


def _render_risk_assessment(biz_type: str, monthly_vol: float, country: str, customer_type: str):
    """渲染风险评估结果"""
    risk_level = "低"
    risk_color = BRAND_COLORS["accent"]
    notes = []

    # 行业风险
    if biz_type in ("游戏出海",):
        risk_level = "中"
        risk_color = BRAND_COLORS["warning"]
        notes.append("游戏行业需审核游戏类型和版号")
    elif biz_type == "其他":
        notes.append("需进一步确认具体业务类型")

    # 流水风险
    if monthly_vol >= 50:
        if risk_level == "低":
            risk_level = "中"
            risk_color = BRAND_COLORS["warning"]
        notes.append(f"月流水{monthly_vol:.0f}万USD，需加强尽调（Enhanced Due Diligence）")
    elif monthly_vol >= 20:
        notes.append(f"月流水{monthly_vol:.0f}万USD，区域经理审批")

    # 国家风险
    country_info = _COUNTRY_COMPLIANCE.get(country, {})
    if country_info.get("difficulty") == "复杂":
        risk_level = "高"
        risk_color = BRAND_COLORS["primary"]
        notes.append(f"{country_info['name']}合规环境复杂，费率较高，所有交易加强审查")
    elif country_info.get("difficulty") == "中等":
        if risk_level == "低":
            risk_level = "中"
            risk_color = BRAND_COLORS["warning"]
        notes.append(f"{country_info['name']}监管较严格，需关注合规要求")

    # 展示结果
    st.markdown(
        f"<div style='text-align:center;padding:{SPACING['md']};background:rgba({hex_to_rgb(risk_color)},0.08);"
        f"border:2px solid {risk_color};border-radius:{RADIUS['lg']};margin-bottom:{SPACING['md']};'>"
        f"<div style='font-size:{TYPE_SCALE['display']};font-weight:700;color:{risk_color};'>风险等级：{risk_level}</div>"
        f"<div style='font-size:{TYPE_SCALE['base']};color:{BRAND_COLORS['text_secondary']};margin-top:{SPACING['xs']};'>"
        f"{biz_type} · 月流水{monthly_vol:.0f}万USD · {country_info.get('name', '')}"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    if notes:
        st.markdown("**评估说明：**")
        for note in notes:
            st.markdown(f"- {note}")

    # 推荐KYC材料
    st.markdown("**需准备的KYC材料：**")
    docs = _KYC_DOCS.get(customer_type, _KYC_DOCS["enterprise"])
    for doc in docs:
        st.markdown(f"- ✅ {doc['name']}：{doc['desc']}")


# ============================================================
# Tab 5: 竞品雷达
# ============================================================
def _render_competitor_radar():
    """竞品分析：静态情报 + AI深度分析"""
    from services.competitor_knowledge import COMPETITOR_DB
    from ui.components.error_handlers import render_copy_button

    st.markdown("**竞品分析**")
    st.caption("查看竞品情报，或使用AI生成深度攻防策略")

    competitor_names = list(COMPETITOR_DB.keys())

    # 单竞品查看
    selected = st.selectbox(
        "选择竞品",
        options=competitor_names,
        key="radar_competitor",
    )

    info = COMPETITOR_DB.get(selected, {})
    if not info:
        return

    # 威胁等级标签
    threat_colors = {"高": BRAND_COLORS["primary"], "中": BRAND_COLORS["warning"], "低": BRAND_COLORS["accent"]}
    threat_color = threat_colors.get(info.get("threat_level", "中"), BRAND_COLORS["warning"])

    st.markdown(
        f"<div style='display:flex;align-items:center;gap:{SPACING['md']};margin:{SPACING['sm']} 0;'>"
        f"<span style='font-size:{TYPE_SCALE['xl']};font-weight:700;'>{info['name_cn']} ({info['name_en']})</span>"
        f"<span style='background:{threat_color};color:#fff;padding:{SPACING['xs']} {SPACING['sm']};"
        f"border-radius:{RADIUS['lg']};font-size:{TYPE_SCALE['sm']};'>威胁等级：{info.get('threat_level', '中')}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # 基本信息
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**基本信息**")
        if info.get("parent"):
            st.markdown(f"- 母公司：{info['parent']}")
        st.markdown(f"- 成立：{info['founded']}年 | 总部：{info['hq']}")
        st.markdown(f"- 规模：{info['scale']}")
        st.markdown(f"- 市场：{info['markets']}")
        st.markdown(f"- 费率：{info['fee_rate']}")
        st.markdown(f"- 结算：{info['settlement']}")
        if info.get("licenses"):
            st.markdown(f"- 牌照：{info['licenses']}")

    with col2:
        st.markdown("**竞品优势（需注意）**")
        for s in info.get("strengths", []):
            st.markdown(f"- 🔴 {s}")

        st.markdown("")
        st.markdown("**竞品弱点（可攻击）**")
        for w in info.get("weaknesses", []):
            st.markdown(f"- ⚡ {w}")

    # Ksher打法
    st.markdown("---")
    st.markdown("**Ksher打法**")
    for a in info.get("ksher_advantages", []):
        st.markdown(f"- ✅ {a}")

    # 一句话攻击角度
    attack = info.get("attack_angle", "")
    if attack:
        st.markdown("---")
        st.markdown("**一句话攻击角度（可直接使用）**")
        st.markdown(
            f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['primary'])},0.06);border-left:3px solid {BRAND_COLORS['primary']};"
            f"padding:{SPACING['md']} {SPACING['md']};border-radius:0 {RADIUS['md']} {RADIUS['md']} 0;font-size:{TYPE_SCALE['md']};font-weight:500;'>"
            f"💬 {attack}</div>",
            unsafe_allow_html=True,
        )
        render_copy_button(attack)

    # 多竞品对比
    st.markdown("---")
    st.subheader("多竞品对比")
    compare_options = [n for n in competitor_names if n != selected]
    compare_with = st.multiselect(
        "选择对比竞品（最多3个）",
        options=compare_options,
        max_selections=3,
        key="radar_compare",
    )

    if compare_with:
        all_compare = [selected] + compare_with

        # 构建对比表
        header = "| 维度 | Ksher | " + " | ".join(all_compare) + " |"
        divider = "|------|-------|" + "|".join(["-------"] * len(all_compare)) + "|"

        rows = []
        rows.append("| 成立 | 2016 | " + " | ".join(str(COMPETITOR_DB[n]["founded"]) for n in all_compare) + " |")
        rows.append("| 总部 | 曼谷/深圳 | " + " | ".join(COMPETITOR_DB[n]["hq"] for n in all_compare) + " |")
        rows.append("| 费率 | 0.05%~0.4% | " + " | ".join(COMPETITOR_DB[n]["fee_rate"] for n in all_compare) + " |")
        rows.append("| 结算 | T+1 | " + " | ".join(COMPETITOR_DB[n]["settlement"] for n in all_compare) + " |")
        rows.append("| 威胁 | — | " + " | ".join(COMPETITOR_DB[n].get("threat_level", "中") for n in all_compare) + " |")
        rows.append("| 东南亚牌照 | ✅ 8国 | " + " | ".join("❌" if "无" in COMPETITOR_DB[n].get("licenses", "无") else "部分" for n in all_compare) + " |")

        st.markdown("\n".join([header, divider] + rows))

    # ---- AI竞品深度分析 ----
    st.markdown("---")
    st.subheader("AI竞品深度分析")
    st.caption("选择竞品，AI生成详细的攻防策略和实战话术")

    ai_competitor = st.selectbox(
        "选择要深度分析的竞品",
        options=[""] + competitor_names,
        format_func=lambda x: "请选择..." if x == "" else x,
        key="radar_ai_competitor",
    )

    # 自定义竞品
    custom_competitor = st.text_input(
        "或输入自定义竞品名称",
        placeholder="如：Payoneer、Airwallex...",
        key="radar_custom_competitor",
    )

    analysis_target = custom_competitor.strip() if custom_competitor.strip() else ai_competitor
    customer_industry = st.session_state.get("customer_context", {}).get("industry", "")
    customer_channel = st.session_state.get("customer_context", {}).get("current_channel", "")

    if st.button("生成AI竞品分析", type="primary", key="radar_ai_analyze",
                 disabled=not analysis_target, help="请先选择分析对象"):
        with st.spinner("AI正在分析竞品..."):
            # 搜集竞品信息
            competitor_info_text = ""
            if analysis_target in COMPETITOR_DB:
                ci = COMPETITOR_DB[analysis_target]
                competitor_info_text = (
                    f"名称: {ci['name_cn']}({ci['name_en']})\n"
                    f"成立: {ci['founded']}年, 总部: {ci['hq']}\n"
                    f"规模: {ci['scale']}, 市场: {ci['markets']}\n"
                    f"费率: {ci['fee_rate']}, 结算: {ci['settlement']}\n"
                    f"优势: {', '.join(ci.get('strengths', []))}\n"
                    f"弱点: {', '.join(ci.get('weaknesses', []))}"
                )

            # 尝试搜索补充信息
            search_results = _tavily_search(f"{analysis_target} 跨境支付 费率 评价")

            if not _is_mock_mode():
                from prompts.sales_prompts import (
                    COMPETITOR_ANALYSIS_SYSTEM_PROMPT,
                    COMPETITOR_ANALYSIS_USER_TEMPLATE,
                )
                raw = _llm_call(
                    COMPETITOR_ANALYSIS_SYSTEM_PROMPT,
                    COMPETITOR_ANALYSIS_USER_TEMPLATE.format(
                        competitor_name=analysis_target,
                        competitor_info=competitor_info_text or "未知，请基于行业知识分析",
                        industry=customer_industry or "未指定",
                        current_channel=customer_channel or "未指定",
                        search_results=search_results or "无搜索结果",
                    ),
                    agent_name="sales_competitor",
                )
                result = _parse_json_safe(raw)
            else:
                result = None

            if not result:
                result = _mock_competitor_analysis(analysis_target)

            st.session_state["radar_ai_result"] = result

    # 展示AI分析结果
    ai_result = st.session_state.get("radar_ai_result")
    if ai_result:
        _display_competitor_analysis(ai_result)


def _display_competitor_analysis(result: dict):
    """展示AI竞品分析结果"""
    profile = result.get("competitor_profile", {})

    st.markdown(f"#### {profile.get('name', '竞品')} 深度分析")
    st.info(profile.get("positioning", ""))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**竞品优势**")
        for s in profile.get("strengths", []):
            st.markdown(f"- {s}")
    with col2:
        st.markdown("**竞品弱点**")
        for w in profile.get("weaknesses", []):
            st.markdown(f"- {w}")

    # 维度对比
    dims = result.get("dimension_comparison", [])
    if dims:
        st.markdown("---")
        st.markdown("**维度对比**")
        header = "| 维度 | 竞品 | Ksher | 结论 |"
        divider = "|------|------|-------|------|"
        rows = [f"| {d.get('dimension','')} | {d.get('competitor','')} | {d.get('ksher','')} | {d.get('verdict','')} |"
                for d in dims]
        st.markdown("\n".join([header, divider] + rows))

    # 攻击策略
    strategies = result.get("attack_strategies", [])
    if strategies:
        st.markdown("---")
        st.markdown("**攻击策略**")
        for s in strategies:
            st.markdown(
                f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['primary'])},0.04);padding:{SPACING['sm']} {SPACING['md']};"
                f"border-radius:{RADIUS['md']};margin:{SPACING['sm']} 0;border-left:3px solid {BRAND_COLORS['primary']};'>"
                f"<b>{s.get('scenario','')}</b><br>"
                f"<span style='font-size:{TYPE_SCALE['base']};'>{s.get('strategy','')}</span><br>"
                f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['base']};'>"
                f"话术：{s.get('script','')}</span></div>",
                unsafe_allow_html=True,
            )

    # 防御准备
    defenses = result.get("defense_prep", [])
    if defenses:
        st.markdown("---")
        st.markdown("**防御准备（客户可能替竞品说话）**")
        for d in defenses:
            with st.expander(f"客户说：\"{d.get('objection', '')}\""):
                render_content_refiner(
                    d.get("response", ""),
                    f"radar_defense_{d.get('objection', '')[:20]}",
                    context_prompt="这是竞品防御话术",
                )

    # 一句话攻击
    one_liner = result.get("one_liner", "")
    if one_liner:
        st.markdown("---")
        st.markdown("**一句话核心攻击角度**")
        render_content_refiner(one_liner, "radar_one_liner", context_prompt="这是竞品攻击话术")


def _mock_competitor_analysis(name: str) -> dict:
    return {
        "competitor_profile": {
            "name": name,
            "positioning": f"{name}是跨境支付领域的主要竞争对手",
            "strengths": ["品牌知名度高", "市场份额大", "产品线齐全"],
            "weaknesses": ["东南亚本地化不足", "费率不透明", "客服响应慢"],
        },
        "dimension_comparison": [
            {"dimension": "东南亚牌照", "competitor": "部分国家", "ksher": "8国本地持牌", "verdict": "Ksher胜 - 合规优势明显"},
            {"dimension": "费率", "competitor": "0.3%-1%", "ksher": "0.05%-0.4%", "verdict": "Ksher胜 - 费率更低"},
            {"dimension": "到账速度", "competitor": "T+2~T+5", "ksher": "T+1", "verdict": "Ksher胜 - 更快到账"},
            {"dimension": "品牌认知", "competitor": "高", "ksher": "中", "verdict": "竞品胜 - 需加强品牌建设"},
        ],
        "attack_strategies": [
            {"scenario": "客户正在用该竞品", "strategy": "从费率切入，算一笔年度总成本账",
             "script": f"您现在用{name}，每月手续费大概多少？我帮您算一下，换到Ksher一年能省多少。"},
            {"scenario": "客户在对比中", "strategy": "强调东南亚本地牌照的合规优势",
             "script": f"做东南亚市场，本地牌照是关键。Ksher泰国有BoT牌照，{name}在东南亚是什么牌照？"},
        ],
        "defense_prep": [
            {"objection": f"{name}品牌更大更安全", "response": f"品牌大不代表费率低。{name}的费率是多少？Ksher东南亚8国持牌，合规安全一样有保障，但费率能帮您省60%。"},
            {"objection": f"我用{name}很久了，不想换", "response": "理解，换供应商确实有成本。不过您可以先开个Ksher账户做对比，不冲突。实际跑一两笔看看到账速度和费率差异。"},
        ],
        "one_liner": f"[Mock] {name}做全球，Ksher专注东南亚——在东南亚这个战场，本地持牌+最低费率，没有比Ksher更合适的选择。",
    }


# ============================================================
# 新增功能：拜访前调研
# ============================================================

def _render_pre_visit_research():
    """拜访前调研：输入公司名 → 搜索 → AI生成调研简报"""
    st.caption("输入目标客户公司名，AI自动搜索公开信息并生成拜访准备简报")

    col1, col2 = st.columns([2, 1])
    with col1:
        research_company = st.text_input(
            "公司名称", placeholder="如：深圳市xxx贸易有限公司",
            key="research_company",
        )
    with col2:
        _industry_preset = st.selectbox(
            "行业（选填）",
            options=[
                "",
                # 贸易类
                "一般贸易（货物出口）",
                "跨境电商 B2C（Shopee/Lazada/TikTok Shop）",
                "跨境电商 B2B（阿里国际/环球资源）",
                "新能源/光伏/储能设备",
                "机械设备/工业品",
                "纺织服装/面料",
                "电子元器件/消费电子",
                "化工原材料",
                "农产品/食品出口",
                "汽车配件/改装件",
                "家居建材/家具",
                "医疗器械/健康产品",
                "玩具/礼品/文具",
                # 服务类
                "物流货代/海外仓",
                "游戏出海/互联网娱乐",
                "SaaS/软件出海",
                "广告营销/MCN/海外直播",
                "在线教育/留学服务",
                "餐饮连锁/品牌出海",
                "版权/IP授权/内容出海",
                "咨询/律所/财税服务",
                "航运/船代/报关行",
                "其他（自定义）",
            ],
            key="research_industry_preset",
        )
        if _industry_preset == "其他（自定义）":
            research_industry = st.text_input(
                "自定义行业", placeholder="如：新能源设备、医疗器械...",
                key="research_industry_custom",
            )
        else:
            research_industry = _industry_preset

    col3, col4 = st.columns(2)
    with col3:
        research_country = st.text_input(
            "目标国家（选填）", placeholder="如：泰国",
            key="research_country",
        )
    with col4:
        research_volume = st.text_input(
            "预估月流水（选填）", placeholder="如：20万美元",
            key="research_volume",
        )

    if st.button("开始调研", type="primary", key="research_start",
                 disabled=not research_company, help="请先输入公司名称"):
        with st.spinner("正在多维度搜索并分析，通常需要 10-20 秒..."):
            # 三维度并行搜索
            search_data = _multi_search_research(
                research_company,
                research_industry or "外贸",
                research_country or "东南亚",
            )

            if not _is_mock_mode():
                from prompts.sales_prompts import (
                    RESEARCH_SYSTEM_PROMPT,
                    RESEARCH_USER_TEMPLATE,
                )
                website_section = search_data["website"] if search_data["website"] else ""
                if website_section:
                    website_section = f"## 官网内容（直接抓取）\n{website_section}"
                raw = _llm_call(
                    RESEARCH_SYSTEM_PROMPT,
                    RESEARCH_USER_TEMPLATE.format(
                        company=research_company,
                        industry=research_industry or "未指定",
                        country=research_country or "未指定",
                        volume=research_volume or "未知",
                        search_company=search_data["company"] or f"未找到 {research_company} 的公司信息。",
                        search_payment=search_data["payment"] or "未找到相关收付汇信息。",
                        search_industry=search_data["industry_bg"] or "未找到行业背景信息。",
                        website_section=website_section,
                    ),
                    agent_name="sales_research",
                )
                result = _parse_json_safe(raw)
            else:
                result = None

            if not result:
                result = _mock_research_result(research_company, research_industry)

            st.session_state["research_result"] = result

    # 展示调研结果
    result = st.session_state.get("research_result")
    if result:
        st.markdown("---")
        st.markdown("#### 深度调研简报")

        # ── 区块一：公司基本面 ──
        basics = result.get("company_basics", {})
        if basics:
            quality = basics.get("data_quality", "low")
            quality_label = {"high": "数据充足", "medium": "数据有限", "low": "信息不足"}.get(quality, quality)
            quality_color = {"high": BRAND_COLORS["accent"], "medium": "#f7a800", "low": "#8a8f99"}.get(quality, "#8a8f99")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                f'<span style="font-weight:600;font-size:0.95rem;">公司基本面</span>'
                f'<span style="background:{quality_color};color:#fff;padding:1px 8px;border-radius:10px;font-size:0.72rem;">{quality_label}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if basics.get("main_business"):
                st.markdown(basics["main_business"])
            cols = st.columns(2)
            with cols[0]:
                if basics.get("scale_estimate"):
                    st.caption(f"规模：{basics['scale_estimate']}")
            with cols[1]:
                markets = basics.get("key_markets", [])
                if markets:
                    st.caption(f"主要市场：{' / '.join(markets)}")

        st.markdown("---")

        # ── 区块二：跨境收付汇画像 ──
        profile = result.get("payment_profile", {})
        if profile:
            st.markdown("**跨境收付汇画像**")
            currencies = profile.get("currency_needs", [])
            if currencies:
                st.caption(f"货币需求：{' · '.join(currencies)}")
            pains = profile.get("likely_pain_points", [])
            if pains:
                st.markdown("痛点：")
                for p in pains:
                    st.markdown(f"- {p}")
            if profile.get("ksher_fit_reason"):
                st.info(f"Ksher 切入点：{profile['ksher_fit_reason']}")
            if profile.get("entry_angle"):
                st.markdown(f"**话术方向**：{profile['entry_angle']}")

        st.markdown("---")

        # ── 区块三：行业宏观背景 ──
        ctx_industry = result.get("industry_context", {})
        if ctx_industry:
            st.markdown("**行业宏观背景**")
            if ctx_industry.get("trend_summary"):
                st.markdown(ctx_industry["trend_summary"])
            if ctx_industry.get("policy_notes"):
                st.caption(f"政策：{ctx_industry['policy_notes']}")
            if ctx_industry.get("competitive_landscape"):
                st.caption(f"同行常用方案：{ctx_industry['competitive_landscape']}")

        st.markdown("---")

        # ── 区块四：拜访准备 ──
        prep = result.get("visit_prep", {})
        if prep:
            st.markdown("**拜访准备**")
            questions = prep.get("key_questions", [])
            if questions:
                st.markdown("要问的关键问题：")
                for q in questions:
                    st.markdown(f"- {q}")
            opening = prep.get("opening_line", "")
            if opening:
                st.markdown("**建议开场白**")
                st.markdown(opening)
            risks = prep.get("risk_flags", [])
            if risks:
                st.markdown("**风险提醒**")
                for r in risks:
                    st.warning(r)

        # 注入按钮：将调研结果填入客户画像
        if st.button("将调研结果注入客户画像", key="research_inject"):
            ctx = st.session_state.get("customer_context", {})
            if not ctx.get("company") and research_company:
                ctx["company"] = research_company
            if not ctx.get("industry") and research_industry:
                ctx["industry"] = research_industry
            if not ctx.get("target_country") and research_country:
                ctx["target_country"] = research_country
            st.session_state.customer_context = ctx
            st.success("已注入客户画像，可直接生成作战包。")


def _mock_research_result(company: str, industry: str) -> dict:
    ind = industry or "外贸"
    return {
        "company_basics": {
            "main_business": f"[Mock] {company} 是一家 {ind} 企业，主营业务涉及跨境贸易及相关供应链服务。",
            "scale_estimate": "推断：中小型企业，员工规模 50-200 人（Mock 数据，实际需确认）",
            "key_markets": ["东南亚", "中国大陆"],
            "data_quality": "low",
        },
        "payment_profile": {
            "currency_needs": ["美元", "泰铢/马来令吉（东南亚收款）"],
            "likely_pain_points": [
                f"推断：{ind}行业银行汇款手续费约 0.5-1%，月流水大时成本显著",
                "推断：买家付款到账周期 3-7 天，影响资金周转",
                "推断：多国收款账户管理复杂，对账效率低",
            ],
            "ksher_fit_reason": f"Ksher 在东南亚持本地牌照，{ind} 企业可通过本地账户直收，费率低至 0.4% 且 T+1 到账。",
            "entry_angle": "先问当前收款方式和到账周期，再用费率和到账速度做对比",
        },
        "industry_context": {
            "trend_summary": f"{ind} 行业跨境支付需求持续增长，东南亚本地支付覆盖率提升，企业对降费增效诉求强烈。",
            "policy_notes": "外汇管理趋严，持牌机构收款合规性成为选型关键因素。",
            "competitive_landscape": "多数同行仍用银行电汇或 WorldFirst/XTransfer 等平台，费率普遍在 0.5-1% 区间。",
        },
        "visit_prep": {
            "key_questions": [
                "目前收款主要走哪个渠道？费率大概是多少？",
                "到账通常几天？有没有遇到被卡单或汇损的情况？",
                "东南亚哪个国家的买家占比最大？",
            ],
            "opening_line": f"[Mock] {company} 您好，我是 Ksher 的业务顾问。了解到贵司在做 {ind}，"
                           "想聊聊东南亚收款这块——现在很多同行都在转用本地账户直收，到账从 5 天压到 1 天，"
                           "费率也从 1% 降到 0.4%。您这边目前怎么处理海外货款的？",
            "risk_flags": [],
        },
    }


# ============================================================
# 改造：产品百科 → AI产品顾问
# ============================================================

def _render_ai_product_advisor():
    """AI产品顾问：根据客户画像智能推荐产品"""
    st.markdown("---")
    st.subheader("AI产品顾问")
    st.caption("输入客户画像，AI智能匹配最佳产品组合并生成推荐话术")

    # 从customer_context读取默认值
    ctx = st.session_state.get("customer_context", {})

    col1, col2 = st.columns(2)
    with col1:
        adv_company = st.text_input(
            "客户公司", value=ctx.get("company", ""), key="adv_company",
        )
        adv_industry = st.selectbox(
            "行业",
            options=["一般贸易", "跨境电商", "服务贸易", "物流货代", "游戏出海", "SaaS", "其他"],
            key="adv_industry",
        )
        adv_country = st.text_input(
            "目标国家", value=ctx.get("target_country", ""), key="adv_country",
            placeholder="如：泰国、马来西亚",
        )
    with col2:
        adv_volume = st.text_input(
            "月流水(万USD)",
            value=str(ctx.get("monthly_volume", "")),
            placeholder="如：30",
            key="adv_volume",
        )
        _adv_channel_preset = st.selectbox(
            "当前收款方式",
            options=[
                "无/新客户",
                # 银行渠道
                "银行电汇（T/T）",
                "中国银行跨境汇款",
                "招行跨境汇款",
                # 国内主流跨境收款平台
                "万里汇 WorldFirst（蚂蚁）",
                "XTransfer（外贸专属）",
                "连连国际 LianLian",
                "PingPong",
                "Payoneer（派安盈）",
                "空中云汇 Airwallex",
                "光子易 PhotonPay",
                "汇付海外（汇付天下）",
                "易宝国际",
                "收钱吧出海",
                "OFX",
                "Stripe",
                # 平台代收
                "亚马逊平台代收",
                "速卖通/敦煌平台代收",
                "Shopee/Lazada平台代收",
                # 其他
                "其他（自定义）",
            ],
            key="adv_channel_preset",
        )
        if _adv_channel_preset == "其他（自定义）":
            adv_channel = st.text_input(
                "自定义收款方式", placeholder="如：富途证券收款、币圈USDT结算...",
                key="adv_channel_custom",
            )
        else:
            adv_channel = _adv_channel_preset
        adv_pain = st.text_input(
            "主要痛点", value=", ".join(ctx.get("pain_points", [])),
            key="adv_pain", placeholder="如：费率高、到账慢",
        )

    if st.button("生成产品推荐", type="primary", key="adv_generate"):
        with st.spinner("AI正在分析匹配..."):
            # 构建产品知识摘要
            product_knowledge = _build_product_knowledge_summary(
                adv_industry, adv_country, adv_volume,
            )

            if not _is_mock_mode():
                from prompts.sales_prompts import (
                    PRODUCT_ADVISOR_SYSTEM_PROMPT,
                    PRODUCT_ADVISOR_USER_TEMPLATE,
                )
                raw = _llm_call(
                    PRODUCT_ADVISOR_SYSTEM_PROMPT,
                    PRODUCT_ADVISOR_USER_TEMPLATE.format(
                        company=adv_company or "未指定",
                        industry=adv_industry,
                        country=adv_country or "东南亚",
                        volume=adv_volume,
                        current_channel=adv_channel,
                        pain_points=adv_pain or "未明确",
                        company_size=ctx.get("company_size", "未知"),
                        main_products=ctx.get("main_products", "未知"),
                        product_knowledge=product_knowledge,
                    ),
                    agent_name="sales_product",
                    temperature=0.5,
                )
                result = _parse_json_safe(raw)
            else:
                result = None

            if not result:
                result = _mock_product_advisor(adv_company, adv_industry, adv_volume, adv_channel)

            st.session_state["adv_result"] = result

    # 展示推荐结果
    result = st.session_state.get("adv_result")
    if result:
        st.markdown("---")

        # 推荐产品
        products = result.get("recommended_products", [])
        if products:
            st.markdown("#### 推荐产品组合")
            for p in products:
                st.markdown(
                    f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['accent'])},0.05);padding:{SPACING['sm']} {SPACING['md']};"
                    f"border-radius:{RADIUS['md']};margin:{SPACING['sm']} 0;border-left:3px solid {BRAND_COLORS['accent']};'>"
                    f"<b>{p.get('product','')}</b> · 费率 {p.get('fee_rate','')}<br>"
                    f"<span style='font-size:{TYPE_SCALE['base']};'>{p.get('reason','')}</span><br>"
                    f"<span style='color:{BRAND_COLORS['text_secondary']};font-size:{TYPE_SCALE['base']};'>"
                    f"核心卖点：{p.get('highlight','')}</span></div>",
                    unsafe_allow_html=True,
                )

        # 费率方案
        fee_plan = result.get("fee_plan", "")
        if fee_plan:
            st.markdown("#### 费率方案")
            st.success(fee_plan)

        # 对比现有方案
        vs_current = result.get("vs_current", "")
        if vs_current:
            st.markdown("#### 对比现有方案")
            st.info(vs_current)

        # 增值建议
        addons = result.get("addon_suggestions", [])
        if addons:
            st.markdown("#### 增值产品建议")
            for a in addons:
                st.markdown(f"- {a}")

        # 推荐话术
        pitch = result.get("pitch_script", "")
        if pitch:
            st.markdown("#### 推荐话术")
            st.markdown(pitch)

        # FAQ准备
        faqs = result.get("faq_prep", [])
        if faqs:
            st.markdown("#### 客户可能问的问题")
            for faq in faqs:
                with st.expander(faq.get("question", "")):
                    st.markdown(faq.get("answer", ""))


def _build_product_knowledge_summary(industry: str, country: str, volume) -> str:
    """从静态产品数据库构建知识摘要"""
    # 安全转换 volume 为 float
    try:
        volume = float(volume) if volume else 0.0
    except (ValueError, TypeError):
        volume = 0.0

    lines = []

    # 判断贸易类型
    if "电商" in industry:
        trade = "b2c"
    elif "服务" in industry or "SaaS" in industry or "游戏" in industry or "物流" in industry:
        trade = "service"
    else:
        trade = "b2b"

    data = _PRODUCT_DB.get(trade, _PRODUCT_DB["b2b"])
    lines.append(f"贸易类型：{data['label']}")
    lines.append(f"说明：{data['description']}")

    # 匹配国家
    if trade in ("b2b", "b2c") and "countries" in data:
        country_lower = country.lower() if country else ""
        country_map = {"泰": "thailand", "马来": "malaysia", "菲": "philippines",
                       "印尼": "indonesia", "越": "vietnam", "香港": "hongkong", "欧": "europe"}
        matched = None
        for cn, en in country_map.items():
            if cn in country_lower or en in country_lower:
                matched = en
                break
        if matched and matched in data["countries"]:
            c = data["countries"][matched]
            lines.append(f"\n目标国家：{c['name']}")
            lines.append(f"费率：{c['fee_rate']}，结算：{c['settlement']}，币种：{c['currency']}")
            lines.append(f"卖点：{'; '.join(c['selling_points'])}")

    # 费率阶梯
    if volume >= 50:
        lines.append("\n费率等级：S级（0.05%）")
    elif volume >= 20:
        lines.append("\n费率等级：A级（0.05%-0.1%）")
    elif volume >= 10:
        lines.append("\n费率等级：B级（0.1%-0.2%）")
    elif volume >= 5:
        lines.append("\n费率等级：C级（0.2%-0.3%）")
    else:
        lines.append("\n费率等级：D/E/F级（0.3%-0.4%）")

    # 增值产品
    lines.append("\n增值产品：")
    for key, addon in _ADDON_PRODUCTS.items():
        lines.append(f"- {addon['name']}：{addon['description']}")

    return "\n".join(lines)


def _mock_product_advisor(company: str, industry: str, volume, channel: str) -> dict:
    # 安全转换 volume 为 float
    try:
        volume = float(volume) if volume else 0.0
    except (ValueError, TypeError):
        volume = 0.0

    fee_tier = "0.1%-0.2%" if volume >= 10 else "0.3%-0.4%"
    annual_save = volume * 10000 * 0.005 * 12  # 假设省0.5%
    return {
        "recommended_products": [
            {"product": "B2B货物贸易收款", "reason": f"匹配{industry}企业的海外收款需求",
             "fee_rate": fee_tier, "highlight": "本地银行账户直收，T+1到账"},
            {"product": "香港全球收", "reason": "一个账户收全球多国货款",
             "fee_rate": "0.4%", "highlight": "覆盖130+国家"},
        ],
        "fee_plan": f"[Mock] 基于月流水{volume}万USD，预估费率{fee_tier}，年度手续费约¥{volume*float(fee_tier.split('-')[0].replace('%',''))*120:.0f}。"
                   f"相比银行电汇（约1.5%），年省约¥{annual_save:.0f}。",
        "vs_current": f"[Mock] 对比{channel}：Ksher东南亚本地持牌，费率更低，T+1到账更快。",
        "addon_suggestions": [
            "建议追加「秒到宝T+0」：适合资金周转要求高的客户",
            "建议了解「锁汇工具」：适合大额B2B、账期长的场景",
        ],
        "pitch_script": f"[Mock] {company or '贵公司'}做{industry}，海外收款这块我帮您算了一笔账。"
                       f"您现在{channel}的费率大概1%-1.5%，Ksher本地账户直收，费率{fee_tier}，"
                       f"一年光手续费就能省¥{annual_save:.0f}。而且T+1到账，比银行电汇快3-4天。",
        "faq_prep": [
            {"question": "Ksher安全吗？", "answer": "[Mock] Ksher在东南亚8国持有本地支付牌照，受各国央行监管。泰国有BoT牌照，马来有BNM牌照。"},
            {"question": "转换成本高不高？", "answer": "[Mock] 开户免费，无年费。可以先开户试跑一两笔，跟现有渠道并行使用，零风险对比。"},
        ],
    }


# ============================================================
# 改造：单证指南AI智能判断
# ============================================================

def _render_smart_doc_advisor():
    """AI智能单证顾问：根据客户信息自动判断所需材料"""
    st.markdown("---")
    st.subheader("AI智能材料顾问")
    st.caption("输入客户信息，AI自动判断需要准备的全部材料并给出个性化建议")

    ctx = st.session_state.get("customer_context", {})

    col1, col2 = st.columns(2)
    with col1:
        doc_company = st.text_input("公司名称", value=ctx.get("company", ""), key="doc_adv_company")
        doc_biz = st.selectbox(
            "业务类型",
            options=["一般贸易", "跨境电商", "服务贸易", "物流货代", "游戏出海", "SaaS", "其他"],
            key="doc_adv_biz",
        )
    with col2:
        doc_ctype = st.radio(
            "客户类型", options=["enterprise", "individual"],
            format_func=lambda x: {"enterprise": "企业客户", "individual": "个人客户"}[x],
            horizontal=True, key="doc_adv_ctype",
        )
        doc_country = st.selectbox(
            "目标国家",
            options=list(_COUNTRY_COMPLIANCE.keys()),
            format_func=lambda k: _COUNTRY_COMPLIANCE[k]["name"],
            key="doc_adv_country",
        )

    doc_notes = st.text_input("补充说明（选填）", placeholder="如：客户是新注册公司...", key="doc_adv_notes")

    if st.button("AI智能分析", type="primary", key="doc_adv_start"):
        with st.spinner("AI正在分析材料需求..."):
            if not _is_mock_mode():
                from prompts.sales_prompts import (
                    DOCS_ADVISOR_SYSTEM_PROMPT,
                    DOCS_ADVISOR_USER_TEMPLATE,
                )
                raw = _llm_call(
                    DOCS_ADVISOR_SYSTEM_PROMPT,
                    DOCS_ADVISOR_USER_TEMPLATE.format(
                        company=doc_company or "未指定",
                        biz_type=doc_biz,
                        customer_type="企业客户" if doc_ctype == "enterprise" else "个人客户",
                        country=_COUNTRY_COMPLIANCE.get(doc_country, {}).get("name", doc_country),
                        volume=ctx.get("monthly_volume", "未知"),
                        industry=doc_biz,
                        notes=doc_notes or "无",
                    ),
                    agent_name="sales_docs",
                )
                result = _parse_json_safe(raw)
            else:
                result = None

            if not result:
                result = _mock_doc_advisor(doc_biz, doc_ctype, doc_country)

            st.session_state["doc_adv_result"] = result

    result = st.session_state.get("doc_adv_result")
    if result:
        st.markdown("---")

        # 材料清单
        docs = result.get("required_docs", [])
        if docs:
            st.markdown("#### 所需材料清单")
            for d in docs:
                priority_color = STATUS_COLOR_MAP["priority"].get(d.get("priority"), BRAND_COLORS["text_secondary"])
                st.markdown(
                    f"<div style='background:rgba({hex_to_rgb(BRAND_COLORS['surface'])},0.8);padding:{SPACING['sm']} {SPACING['md']};"
                    f"border-radius:{RADIUS['md']};margin:{SPACING['xs']} 0;border-left:3px solid {priority_color};'>"
                    f"<b>{d.get('name','')}</b> "
                    f"<span style='color:{priority_color};font-size:{TYPE_SCALE['sm']};'>[{d.get('priority','必需')}]</span><br>"
                    f"<span style='font-size:{TYPE_SCALE['base']};'>{d.get('description','')}</span>"
                    f"{'<br><span style=\"color:' + BRAND_COLORS['warning'] + ';font-size:' + TYPE_SCALE['base'] + ';\">常见问题：' + d.get('common_issues','') + '</span>' if d.get('common_issues') else ''}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # 准备建议
        tips = result.get("preparation_tips", [])
        if tips:
            st.markdown("#### 准备建议")
            for t in tips:
                st.markdown(f"- {t}")

        # 预估周期
        timeline = result.get("estimated_timeline", "")
        if timeline:
            st.info(f"预估开户周期：{timeline}")

        # 风险提醒
        risks = result.get("risk_reminders", [])
        if risks:
            for r in risks:
                st.warning(r)


def _mock_doc_advisor(biz_type: str, customer_type: str, country: str) -> dict:
    docs = [
        {"name": "营业执照", "priority": "必需", "description": "彩色扫描件，确认在有效期内",
         "common_issues": "最常见退件原因：营业执照模糊或过期"},
        {"name": "法人身份证", "priority": "必需", "description": "正反面彩色扫描件",
         "common_issues": "注意身份证有效期，临期<3个月建议先换证"},
        {"name": "银行开户许可证", "priority": "必需", "description": "或基本存款账户信息",
         "common_issues": "公司名必须与营业执照完全一致"},
    ]
    if "电商" in biz_type:
        docs.append({"name": "平台店铺链接", "priority": "必需",
                     "description": "Shopee/Lazada/TikTok Shop后台截图", "common_issues": ""})
    elif "服务" in biz_type or "SaaS" in biz_type:
        docs.append({"name": "服务合同", "priority": "必需",
                     "description": "需明确描述服务内容和金额", "common_issues": "合同方与付款方需一致"})
    else:
        docs.append({"name": "贸易合同/发票", "priority": "必需",
                     "description": "购销合同+商业发票", "common_issues": "金额需与申报流水匹配"})

    return {
        "required_docs": docs,
        "preparation_tips": [
            "[Mock] 所有文件建议彩色扫描，分辨率300dpi以上",
            "[Mock] 提前核对各文件间公司名称完全一致",
            "[Mock] 准备好近3个月的贸易凭证作为补充材料",
        ],
        "estimated_timeline": "[Mock] 资料齐全情况下，3-5个工作日完成开户",
        "risk_reminders": [],
    }


# ============================================================
# 改造：合规风控AI增强
# ============================================================

def _render_ai_risk_report():
    """AI风险评估报告"""
    st.markdown("---")
    st.subheader("AI风险评估报告")
    st.caption("输入客户信息，AI生成详细的风险评估和合规建议")

    ctx = st.session_state.get("customer_context", {})

    col1, col2 = st.columns(2)
    with col1:
        risk_company = st.text_input("公司名称", value=ctx.get("company", ""), key="risk_company")
        risk_industry = st.selectbox(
            "行业",
            options=["一般贸易", "跨境电商", "服务贸易", "物流货代", "游戏出海", "SaaS", "其他"],
            key="risk_industry",
        )
    with col2:
        risk_biz = st.selectbox(
            "业务类型",
            options=["货物贸易", "电商", "服务贸易"],
            key="risk_biz",
        )
        risk_country = st.selectbox(
            "目标国家",
            options=list(_COUNTRY_COMPLIANCE.keys()),
            format_func=lambda k: _COUNTRY_COMPLIANCE[k]["name"],
            key="risk_ai_country",
        )

    col3, col4 = st.columns(2)
    with col3:
        risk_volume = st.number_input(
            "预估月流水(万USD)", value=10.0, min_value=0.0, step=5.0,
            key="risk_volume",
        )
    with col4:
        risk_ctype = st.radio(
            "客户类型", options=["enterprise", "individual"],
            format_func=lambda x: {"enterprise": "企业", "individual": "个人"}[x],
            horizontal=True, key="risk_ctype",
        )

    risk_notes = st.text_input("补充说明", placeholder="如：客户曾被其他平台拒绝过...", key="risk_notes")

    if st.button("生成AI风险报告", type="primary", key="risk_ai_start"):
        with st.spinner("AI正在评估风险..."):
            if not _is_mock_mode():
                from prompts.sales_prompts import (
                    RISK_REPORT_SYSTEM_PROMPT,
                    RISK_REPORT_USER_TEMPLATE,
                )
                raw = _llm_call(
                    RISK_REPORT_SYSTEM_PROMPT,
                    RISK_REPORT_USER_TEMPLATE.format(
                        company=risk_company or "未指定",
                        industry=risk_industry,
                        biz_type=risk_biz,
                        country=_COUNTRY_COMPLIANCE.get(risk_country, {}).get("name", risk_country),
                        volume=risk_volume,
                        customer_type="企业" if risk_ctype == "enterprise" else "个人",
                        notes=risk_notes or "无",
                    ),
                    agent_name="sales_risk",
                )
                result = _parse_json_safe(raw)
            else:
                result = None

            if not result:
                result = _mock_risk_report(risk_industry, risk_volume, risk_country)

            st.session_state["risk_ai_result"] = result

    result = st.session_state.get("risk_ai_result")
    if result:
        st.markdown("---")

        # 风险等级大卡片
        level = result.get("risk_level", "中")
        score = result.get("risk_score", 50)
        level_colors = {"低": BRAND_COLORS["accent"], "中": BRAND_COLORS["warning"], "高": BRAND_COLORS["primary"]}
        color = level_colors.get(level, BRAND_COLORS["warning"])

        st.markdown(
            f"<div style='text-align:center;padding:{SPACING['md']};background:rgba({hex_to_rgb(color)},0.08);"
            f"border:2px solid {color};border-radius:{RADIUS['lg']};margin-bottom:{SPACING['md']};'>"
            f"<div style='font-size:{TYPE_SCALE['xl']};font-weight:700;color:{color};'>风险等级：{level}</div>"
            f"<div style='font-size:{TYPE_SCALE['xl']};color:{color};margin:{SPACING['xs']} 0;'>风险评分：{score}/100</div>"
            f"<div style='font-size:{TYPE_SCALE['base']};color:{BRAND_COLORS['text_secondary']};'>"
            f"开户通过率预估：{result.get('approval_probability', '中')}</div></div>",
            unsafe_allow_html=True,
        )

        # 各维度评分
        dims = result.get("dimension_scores", {})
        if dims:
            st.markdown("**各维度评估**")
            for dim_name, dim_info in dims.items():
                dim_labels = {
                    "industry": "行业风险", "volume": "流水合理性",
                    "country": "国家风险", "compliance": "合规历史",
                    "kyc_difficulty": "KYC难度",
                }
                label = dim_labels.get(dim_name, dim_name)
                st.markdown(f"- **{label}**：{dim_info.get('score', '')} — {dim_info.get('detail', '')}")

        # 主要风险
        risks = result.get("key_risks", [])
        if risks:
            st.markdown("**主要风险点**")
            for r in risks:
                st.markdown(f"- {r}")

        # 缓释建议
        mitigations = result.get("mitigation", [])
        if mitigations:
            st.markdown("**风险缓释建议**")
            for m in mitigations:
                st.markdown(f"- {m}")

        # 销售建议
        rec = result.get("sales_recommendation", "")
        if rec:
            st.markdown("**给销售的建议**")
            st.info(rec)


def _mock_risk_report(industry: str, volume, country: str) -> dict:
    # 安全转换 volume 为 float
    try:
        volume = float(volume) if volume else 0.0
    except (ValueError, TypeError):
        volume = 0.0

    country_info = _COUNTRY_COMPLIANCE.get(country, {})
    difficulty = country_info.get("difficulty", "简单")
    level = "低" if difficulty == "简单" and volume < 50 else ("高" if difficulty == "复杂" else "中")
    score = {"低": 25, "中": 55, "高": 80}.get(level, 50)
    return {
        "risk_level": level,
        "risk_score": score,
        "dimension_scores": {
            "industry": {"score": "低", "detail": f"[Mock] {industry}属于正常行业"},
            "volume": {"score": "低" if volume < 50 else "中",
                      "detail": f"[Mock] 月流水{volume}万USD，{'正常范围' if volume < 50 else '需加强尽调'}"},
            "country": {"score": difficulty, "detail": f"[Mock] {country_info.get('name', '')}合规{difficulty}"},
            "compliance": {"score": "低", "detail": "[Mock] 无已知合规历史问题"},
            "kyc_difficulty": {"score": difficulty, "detail": f"[Mock] {country_info.get('name', '')}开户难度{difficulty}"},
        },
        "approval_probability": {"低": "高", "中": "中", "高": "低"}.get(level, "中"),
        "key_risks": [f"[Mock] {country_info.get('name', '')}监管环境{difficulty}"] if difficulty != "简单" else [],
        "mitigation": ["[Mock] 提前准备齐全KYC材料", "[Mock] 确保贸易背景真实可查"],
        "sales_recommendation": f"[Mock] 综合评估风险{level}，{'建议正常推进' if level == '低' else '建议谨慎评估后推进'}。",
    }


# ============================================================
# ============================================================
# Tab 6: 数字员工（销售支持数字员工中控台）
# ============================================================

def _render_digital_employee_tab():
    """销售支持数字员工中控台 — 集成工作流/推送/客户阶段/Agent效果"""
    st.markdown("**AI驱动的主动销售支持中枢**")
    st.caption("客户管理 · 智能推送 · 自动报告 · 效果追踪")

    # ── 数据加载 ─────────────────────────────────────────────
    try:
        from services.customer_stage_manager import get_customer_stage_manager
        stage_mgr = get_customer_stage_manager()
        funnel = stage_mgr.get_funnel_stats()
        overdue = stage_mgr.get_overdue_customers()
        metrics = stage_mgr.get_stage_metrics()
    except Exception:
        stage_mgr = None
        funnel = {"total_customers": 0, "signed_customers": 0, "active_customers": 0, "overall_conversion_rate": 0}
        overdue = []
        metrics = []

    try:
        from services.intelligence_pusher import get_intelligence_pusher
        pusher = get_intelligence_pusher()
        push_stats = pusher.get_stats(days=7)
        push_rules = pusher.list_rules(enabled_only=False)
        push_history = pusher.get_push_history(days=7, limit=10)
    except Exception:
        pusher = None
        push_stats = {"total_pushes": 0, "success_rate": 0}
        push_rules = []
        push_history = []

    try:
        from services.agent_effectiveness import get_effectiveness_tracker
        tracker = get_effectiveness_tracker()
        agent_stats = tracker.get_agent_stats(days=7)
        total_calls = sum(s.get("call_count", 0) for s in agent_stats.values())
    except Exception:
        agent_stats = {}
        total_calls = 0

    # ── 概览指标 ─────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("客户总数", funnel.get("total_customers", 0), help="系统中所有客户")
    with c2:
        st.metric("已签约", funnel.get("signed_customers", 0),
                  delta=f"{funnel.get('overall_conversion_rate', 0)}%", help="整体转化率")
    with c3:
        st.metric("智能推送", push_stats.get("total_pushes", 0),
                  delta=f"成功{push_stats.get('success_rate', 0)}%", help="近7天自动推送")
    with c4:
        st.metric("Agent调用", total_calls, help="近7天AI Agent调用次数")

    st.markdown("---")

    # ── 子 Tab ───────────────────────────────────────────────
    sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5, sub_tab6, sub_tab7, sub_tab8 = st.tabs(
        ["📊 客户漏斗", "📡 智能推送", "⚙️ 工作流", "🤖 Agent效果", "📈 数据洞察", "🧠 Swarm监控", "📂 技能库", "💻 终端"]
    )

    # ── 客户漏斗 ─────────────────────────────────────────────
    with sub_tab1:
        st.markdown("**阶段分布**")
        if metrics:
            cols = st.columns(len(metrics))
            for i, m in enumerate(metrics):
                with cols[i]:
                    st.markdown(
                        f"<div style='text-align:center;padding:8px;"
                        f"background:rgba(0,0,0,0.03);border-radius:8px;'>"
                        f"<div style='font-size:1.5rem;font-weight:700;'>{m.customer_count}</div>"
                        f"<div style='font-size:0.85rem;color:#8a8f99;'>{m.stage}</div>"
                        f"<div style='font-size:0.72rem;color:#8a8f99;'>"
                        f"均{m.avg_days}天 · 转化{m.conversion_rate}%</div></div>",
                        unsafe_allow_html=True,
                    )
        else:
            st.info("暂无客户阶段数据")

        st.markdown("---")
        st.markdown("**⚠️ 超期客户预警**")
        if overdue:
            for o in overdue[:10]:
                color = BRAND_COLORS["primary"] if o.get("overdue_by", 0) > 7 else BRAND_COLORS["warning"]
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"padding:8px 12px;border-left:3px solid {color};"
                    f"background:rgba(0,0,0,0.02);border-radius:0 8px 8px 0;'>"
                    f"<div><b>{o.get('company_name', '未知')}</b> · {o.get('current_stage', '')}</div>"
                    f"<div style='color:{color};font-size:0.85rem;'>超期 {o.get('overdue_by', 0)} 天</div></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.success("✅ 本周无超期客户")

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            with st.expander("➕ 新增客户"):
                company = st.text_input("公司名", key="de_new_company")
                industry = st.selectbox("行业", ["一般贸易", "跨境电商", "服务贸易", "物流货代", "其他"], key="de_new_industry")
                assigned = st.text_input("负责销售", key="de_new_sales")
                if st.button("创建客户", key="de_create_customer"):
                    if company and stage_mgr:
                        try:
                            profile = stage_mgr.create_company(company_name=company, industry=industry, assigned_sales=assigned)
                            st.success(f"✅ 已创建: {profile.company_name}")
                        except Exception as e:
                            st.error(f"创建失败: {e}")
                    else:
                        st.warning("请输入公司名")
        with col2:
            with st.expander("🔄 阶段转换"):
                if stage_mgr:
                    try:
                        customers = stage_mgr.list_customers(limit=50)
                        cust_opts = {f"{c.company_name} ({c.current_stage})": c.customer_id for c in customers}
                    except Exception:
                        cust_opts = {}
                    if cust_opts:
                        selected = st.selectbox("选择客户", options=list(cust_opts.keys()), key="de_trans_cust")
                        to_stage = st.selectbox("目标阶段", ["潜在客户", "初次接触", "需求确认", "方案沟通", "签约中", "已签约", "已流失"], key="de_trans_stage")
                        reason = st.text_input("转换原因", key="de_trans_reason")
                        if st.button("执行转换", key="de_do_trans"):
                            result = stage_mgr.transition_stage(cust_opts[selected], to_stage, reason=reason)
                            st.success(result["message"]) if result["success"] else st.error(result["message"])
                    else:
                        st.info("暂无客户")

    # ── 智能推送 ─────────────────────────────────────────────
    with sub_tab2:
        st.markdown("**推送规则**")
        for rule in push_rules:
            icon = "🟢" if rule.enabled else "⚪"
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(f"{icon} <b>{rule.name}</b> <span style='font-size:0.75rem;color:#8a8f99;'>{rule.trigger_type.value} · 冷却{rule.cooldown_minutes}分</span>", unsafe_allow_html=True)
            with col2:
                if pusher:
                    if rule.enabled:
                        if st.button("禁用", key=f"de_dis_{rule.rule_id}"):
                            pusher.disable_rule(rule.rule_id)
                            st.rerun()
                    else:
                        if st.button("启用", key=f"de_en_{rule.rule_id}"):
                            pusher.enable_rule(rule.rule_id)
                            st.rerun()
            with col3:
                if pusher and st.button("测试", key=f"de_test_{rule.rule_id}"):
                    result = pusher.push(rule.rule_id, {"test": True}, force=True)
                    st.success("✅ 已推送") if result["success"] else st.warning(result["message"])

        st.markdown("---")
        st.markdown("**近7天推送记录**")
        if push_history:
            for h in push_history:
                icon = "✅" if h.get("status") == "sent" else "❌"
                st.markdown(f"{icon} <b>{h.get('rule_name', '未知')}</b> <span style='font-size:0.75rem;color:#8a8f99;'>{h.get('pushed_at', '')}</span>", unsafe_allow_html=True)
        else:
            st.info("近7天无推送记录")

    # ── 工作流 ───────────────────────────────────────────────
    with sub_tab3:
        st.markdown("**⚡ 手动触发任务**")
        st.caption("手动执行数字员工的周期性任务")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📰 生成晨报", type="primary", use_container_width=True, key="de_btn_morning"):
                with st.spinner("生成中..."):
                    try:
                        from services.morning_briefing import generate_and_push_morning_briefing
                        generate_and_push_morning_briefing()
                        st.success("✅ 晨报已生成")
                    except Exception as e:
                        st.error(f"失败: {e}")
        with c2:
            if st.button("💱 汇率检查", use_container_width=True, key="de_btn_fx"):
                with st.spinner("检查中..."):
                    try:
                        from services.workflow_scheduler import get_workflow_scheduler
                        scheduler = get_workflow_scheduler()
                        result = scheduler._handlers.get("exchange_rate_alert")()
                        st.success(f"✅ {result.get('alerts_triggered', 0)} 条汇率预警")
                    except Exception as e:
                        st.error(f"失败: {e}")
        with c3:
            if st.button("🏥 健康度检查", use_container_width=True, key="de_btn_health"):
                with st.spinner("检查中..."):
                    try:
                        from services.workflow_scheduler import get_workflow_scheduler
                        scheduler = get_workflow_scheduler()
                        result = scheduler._handlers.get("channel_health_check")()
                        st.success(f"✅ {result.get('alerts', 0)} 条健康度预警")
                    except Exception as e:
                        st.error(f"失败: {e}")

        if st.button("📊 生成周报", use_container_width=True, key="de_btn_weekly"):
            with st.spinner("生成中..."):
                try:
                    from services.workflow_scheduler import get_workflow_scheduler
                    scheduler = get_workflow_scheduler()
                    result = scheduler._handlers.get("weekly_report")()
                    if result.get("status") == "success":
                        st.success("✅ 周报已生成")
                        with st.expander("查看周报"):
                            st.markdown(result.get("report", ""))
                    else:
                        st.warning(result.get("message", ""))
                except Exception as e:
                    st.error(f"失败: {e}")

    # ── Agent效果 ────────────────────────────────────────────
    with sub_tab4:
        st.markdown("**Agent调用统计（近7天）**")
        if agent_stats:
            import pandas as pd
            rows = []
            for name, data in agent_stats.items():
                rows.append({
                    "Agent": name, "调用": data.get("call_count", 0),
                    "均耗时(ms)": data.get("avg_duration_ms", 0),
                    "满意度": f"{data.get('satisfaction', 0)}%", "评分": data.get("avg_score", 0),
                })
            df = pd.DataFrame(rows).sort_values("调用", ascending=False)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("暂无Agent调用数据")

        st.markdown("---")
        st.markdown("**📚 知识使用排行**")
        try:
            from services.knowledge_hub import get_knowledge_hub
            kh = get_knowledge_hub()
            popular = kh.get_popular_knowledge(limit=5)
            if popular:
                cols = st.columns(len(popular))
                for i, item in enumerate(popular):
                    with cols[i]:
                        st.metric(label=item.get("name", item.get("category", "")), value=f"{item.get('count', 0)}次")
            else:
                st.info("暂无知识使用记录")
        except Exception:
            st.info("暂无知识使用记录")

    # ── 数据洞察（原数据驾驶舱内容）───────────────────────────
    with sub_tab5:
        st.markdown("**知识中枢状态**")
        try:
            from services.knowledge_hub import get_knowledge_hub
            kh = get_knowledge_hub()
            stats = kh.get_stats()
            kc1, kc2, kc3, kc4 = st.columns(4)
            with kc1:
                st.metric("总查询次数", stats.get("total_queries", 0))
            with kc2:
                st.metric("长期记忆条数", stats.get("long_term_memory_count", 0))
            with kc3:
                st.metric("服务客户数", stats.get("short_term_customers", 0))
            with kc4:
                st.metric("知识分类数", len(kh.KNOWLEDGE_CATEGORIES))
        except Exception:
            st.info("知识中枢状态暂不可用")

        st.markdown("---")
        st.markdown("**💡 智能推荐测试**")
        with st.expander("测试知识推荐", expanded=False):
            test_col1, test_col2 = st.columns(2)
            with test_col1:
                test_industry = st.selectbox("行业", ["b2c", "b2b", "service"], key="de_test_industry")
            with test_col2:
                test_stage = st.selectbox(
                    "客户阶段",
                    ["潜在客户", "初次接触", "需求确认", "方案沟通", "签约中", "已签约"],
                    key="de_test_stage",
                )
            if st.button("测试推荐", key="de_test_recommend"):
                try:
                    from services.knowledge_hub import get_knowledge_hub
                    kh = get_knowledge_hub()
                    suggestions = kh.suggest_knowledge({"industry": test_industry, "stage": test_stage})
                    if suggestions:
                        for s in suggestions:
                            st.markdown(f"- **{s['topic']}** ({s['category']}) — {s['reason']}")
                    else:
                        st.info("暂无推荐")
                except Exception as e:
                    st.error(f"推荐失败: {e}")

    # ── Swarm监控 ────────────────────────────────────────────
    with sub_tab6:
        st.markdown("**🧠 K2.6 Agent集群实时监控**")
        st.caption("任务拆解 → 并行调度 → 结果聚合")

        render_swarm_control()

        # 获取swarm状态
        swarm_state = st.session_state.get("swarm_state")
        render_swarm_monitor(swarm_state)

        # 如果有PPT生成结果，提供下载
        if swarm_state and swarm_state.get("ppt_file"):
            st.markdown("---")
            st.markdown("**📎 生成文件**")
            ppt_data = swarm_state["ppt_file"]
            st.download_button(
                label="⬇️ 下载PPT方案",
                data=ppt_data["bytes"],
                file_name=ppt_data["name"],
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True,
            )

    # ── 技能库 ───────────────────────────────────────────────
    with sub_tab7:
        render_skill_library_ui()

    # ── 终端 ─────────────────────────────────────────────────
    with sub_tab8:
        st.markdown("**💻 本地终端**")
        st.caption("在浏览器中直接执行命令，与 Cloud Code 体验一致")

        # 检查终端服务器是否运行
        import socket
        terminal_ready = False
        try:
            sock = socket.create_connection(("localhost", 8765), timeout=0.5)
            sock.close()
            terminal_ready = True
        except Exception:
            pass

        if terminal_ready:
            st.success("✅ 终端服务器已连接 (ws://localhost:8765)")
        else:
            st.warning("⚠️ 终端服务器未启动")
            st.info("""
            **启动方式：**
            1. 打开新终端窗口
            2. 运行：`python terminal_server.py`
            3. 刷新本页面
            """)

        # 渲染终端小部件
        from ui.components.terminal_widget import render_terminal_widget
        render_terminal_widget()

