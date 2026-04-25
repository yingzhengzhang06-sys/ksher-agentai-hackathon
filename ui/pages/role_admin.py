"""
行政助手 — AI行政管理中心

5个Tab：入职离职 / 采购管理 / 资质证照 / 公文通知 / IT资产管理
"""

import html
import json
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

from config import BRAND_COLORS, TYPE_SCALE, SPACING, RADIUS
from ui.components.ui_cards import hex_to_rgb, render_kpi_card, render_status_badge, render_border_item, render_flex_row
from prompts.admin_prompts import (
    ONBOARDING_PROMPT, OFFBOARDING_PROMPT,
    NOTICE_GENERATION_PROMPT, MEETING_MINUTES_PROMPT,
    PROCUREMENT_ANALYSIS_PROMPT, PROCUREMENT_USER_TEMPLATE,
    COMPLIANCE_ANALYSIS_PROMPT, COMPLIANCE_USER_TEMPLATE,
    ASSET_ANALYSIS_PROMPT, ASSET_ANALYSIS_USER_TEMPLATE,
)


# ============================================================
# 工具函数
# ============================================================

def _get_llm():
    return st.session_state.get("llm_client")


def _is_mock_mode() -> bool:
    return not st.session_state.get("battle_router_ready", False)


def _llm_call(system: str, user_msg: str, agent_name: str = "knowledge") -> str:
    llm = _get_llm()
    if not llm:
        return ""
    try:
        return llm.call_sync(agent_name=agent_name, system=system,
                             user_msg=user_msg, temperature=0.4)
    except Exception:
        return ""


def _parse_json(text: str):
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    if "```" in text:
        for block in text.split("```"):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            try:
                return json.loads(block)
            except (json.JSONDecodeError, TypeError):
                continue
    return None


def _today() -> str:
    return date.today().isoformat()


# ============================================================
# Mock 数据
# ============================================================

def _mock_onboarding_templates() -> dict:
    """各岗位入职清单模板"""
    return {
        "销售": [
            {"item": "签署劳动合同", "category": "文档", "day_offset": 0, "done": False},
            {"item": "签署保密协议", "category": "文档", "day_offset": 0, "done": False},
            {"item": "提交身份证/银行卡/学历复印件", "category": "文档", "day_offset": 0, "done": False},
            {"item": "发放笔记本电脑", "category": "物品", "day_offset": 0, "done": False},
            {"item": "发放工牌和门禁卡", "category": "物品", "day_offset": 0, "done": False},
            {"item": "开通企业邮箱", "category": "账号", "day_offset": 0, "done": False},
            {"item": "开通CRM系统账号", "category": "账号", "day_offset": 0, "done": False},
            {"item": "开通企业微信/钉钉", "category": "账号", "day_offset": 0, "done": False},
            {"item": "产品知识培训（跨境支付基础）", "category": "培训", "day_offset": 1, "done": False},
            {"item": "销售流程与话术培训", "category": "培训", "day_offset": 2, "done": False},
            {"item": "竞品分析培训", "category": "培训", "day_offset": 3, "done": False},
            {"item": "与团队成员逐一介绍", "category": "其他", "day_offset": 0, "done": False},
            {"item": "熟悉办公环境和就餐指引", "category": "其他", "day_offset": 0, "done": False},
        ],
        "技术": [
            {"item": "签署劳动合同", "category": "文档", "day_offset": 0, "done": False},
            {"item": "签署保密协议", "category": "文档", "day_offset": 0, "done": False},
            {"item": "提交证件复印件", "category": "文档", "day_offset": 0, "done": False},
            {"item": "发放开发用笔记本", "category": "物品", "day_offset": 0, "done": False},
            {"item": "发放工牌和门禁卡", "category": "物品", "day_offset": 0, "done": False},
            {"item": "开通企业邮箱", "category": "账号", "day_offset": 0, "done": False},
            {"item": "开通GitHub/GitLab权限", "category": "账号", "day_offset": 0, "done": False},
            {"item": "开通云服务器/数据库访问权限", "category": "账号", "day_offset": 1, "done": False},
            {"item": "配置开发环境", "category": "账号", "day_offset": 1, "done": False},
            {"item": "代码架构与技术栈培训", "category": "培训", "day_offset": 1, "done": False},
            {"item": "安全合规培训（PCI DSS要点）", "category": "培训", "day_offset": 2, "done": False},
            {"item": "指定Mentor/Buddy", "category": "其他", "day_offset": 0, "done": False},
        ],
        "行政": [
            {"item": "签署劳动合同", "category": "文档", "day_offset": 0, "done": False},
            {"item": "签署保密协议", "category": "文档", "day_offset": 0, "done": False},
            {"item": "提交证件复印件", "category": "文档", "day_offset": 0, "done": False},
            {"item": "发放笔记本电脑", "category": "物品", "day_offset": 0, "done": False},
            {"item": "发放工牌和门禁卡", "category": "物品", "day_offset": 0, "done": False},
            {"item": "发放办公用品（文具包）", "category": "物品", "day_offset": 0, "done": False},
            {"item": "开通OA系统和企业邮箱", "category": "账号", "day_offset": 0, "done": False},
            {"item": "公司制度与流程培训", "category": "培训", "day_offset": 1, "done": False},
            {"item": "供应商联络表交接", "category": "培训", "day_offset": 2, "done": False},
            {"item": "团队介绍和办公环境熟悉", "category": "其他", "day_offset": 0, "done": False},
        ],
        "财务": [
            {"item": "签署劳动合同", "category": "文档", "day_offset": 0, "done": False},
            {"item": "签署保密协议", "category": "文档", "day_offset": 0, "done": False},
            {"item": "提交证件复印件", "category": "文档", "day_offset": 0, "done": False},
            {"item": "发放笔记本电脑", "category": "物品", "day_offset": 0, "done": False},
            {"item": "发放工牌和门禁卡", "category": "物品", "day_offset": 0, "done": False},
            {"item": "开通企业邮箱", "category": "账号", "day_offset": 0, "done": False},
            {"item": "开通财务系统/ERP账号", "category": "账号", "day_offset": 0, "done": False},
            {"item": "开通网银操作权限（需主管审批）", "category": "账号", "day_offset": 1, "done": False},
            {"item": "财务制度与审批流程培训", "category": "培训", "day_offset": 1, "done": False},
            {"item": "税务与合规基础培训", "category": "培训", "day_offset": 2, "done": False},
            {"item": "银行Token发放", "category": "物品", "day_offset": 1, "done": False},
        ],
        "运营": [
            {"item": "签署劳动合同", "category": "文档", "day_offset": 0, "done": False},
            {"item": "签署保密协议", "category": "文档", "day_offset": 0, "done": False},
            {"item": "提交证件复印件", "category": "文档", "day_offset": 0, "done": False},
            {"item": "发放笔记本电脑", "category": "物品", "day_offset": 0, "done": False},
            {"item": "发放工牌和门禁卡", "category": "物品", "day_offset": 0, "done": False},
            {"item": "开通企业邮箱和企业微信", "category": "账号", "day_offset": 0, "done": False},
            {"item": "开通数据看板/BI工具权限", "category": "账号", "day_offset": 0, "done": False},
            {"item": "业务流程与产品培训", "category": "培训", "day_offset": 1, "done": False},
            {"item": "客户服务流程培训", "category": "培训", "day_offset": 2, "done": False},
            {"item": "团队介绍", "category": "其他", "day_offset": 0, "done": False},
        ],
    }


def _mock_offboarding_template() -> list:
    """通用离职清单"""
    return [
        {"item": "归还笔记本电脑", "category": "设备", "day_offset": 0, "done": False},
        {"item": "归还工牌和门禁卡", "category": "设备", "day_offset": 0, "done": False},
        {"item": "归还公司手机（如有）", "category": "设备", "day_offset": 0, "done": False},
        {"item": "关闭企业邮箱账号", "category": "权限", "day_offset": 0, "done": False},
        {"item": "关闭CRM/ERP系统权限", "category": "权限", "day_offset": 0, "done": False},
        {"item": "关闭代码仓库权限（技术岗）", "category": "权限", "day_offset": 0, "done": False},
        {"item": "移出企业微信/钉钉", "category": "权限", "day_offset": 0, "done": False},
        {"item": "工作交接文档整理", "category": "交接", "day_offset": -3, "done": False},
        {"item": "客户/项目交接确认", "category": "交接", "day_offset": -2, "done": False},
        {"item": "文件/资料归档", "category": "文档", "day_offset": -1, "done": False},
        {"item": "离职面谈", "category": "手续", "day_offset": 0, "done": False},
        {"item": "签署离职确认书", "category": "手续", "day_offset": 0, "done": False},
        {"item": "社保/公积金停缴手续", "category": "手续", "day_offset": 0, "done": False},
        {"item": "开具离职证明", "category": "手续", "day_offset": 0, "done": False},
    ]


def _mock_onboarding_records() -> list:
    """预置的入职/离职进度记录"""
    templates = _mock_onboarding_templates()
    sales_list = [dict(item, done=True) if i < 8 else dict(item) for i, item in enumerate(templates["销售"])]
    tech_list = [dict(item, done=True) if i < 5 else dict(item) for i, item in enumerate(templates["技术"])]
    off_list = [dict(item, done=True) if i < 3 else dict(item) for i, item in enumerate(_mock_offboarding_template())]

    return [
        {"id": "ONB-001", "name": "李明", "position": "销售", "department": "商务部",
         "type": "onboarding", "start_date": "2026-04-21", "checklist": sales_list,
         "created_at": "2026-04-18T10:00:00"},
        {"id": "ONB-002", "name": "王芳", "position": "技术", "department": "技术部",
         "type": "onboarding", "start_date": "2026-04-28", "checklist": tech_list,
         "created_at": "2026-04-19T09:00:00"},
        {"id": "OFF-001", "name": "陈刚", "position": "运营", "department": "运营部",
         "type": "offboarding", "start_date": "2026-04-25", "checklist": off_list,
         "created_at": "2026-04-15T14:00:00"},
    ]


def _mock_inventory() -> list:
    return [
        {"id": "INV-001", "name": "A4打印纸", "category": "办公耗材", "quantity": 15, "unit": "箱", "min_stock": 5, "unit_price": 45.0},
        {"id": "INV-002", "name": "黑色签字笔", "category": "文具", "quantity": 48, "unit": "支", "min_stock": 20, "unit_price": 3.0},
        {"id": "INV-003", "name": "打印机墨盒（黑色）", "category": "办公耗材", "quantity": 2, "unit": "个", "min_stock": 3, "unit_price": 180.0},
        {"id": "INV-004", "name": "文件夹", "category": "文具", "quantity": 30, "unit": "个", "min_stock": 10, "unit_price": 8.0},
        {"id": "INV-005", "name": "饮用水（桶装）", "category": "日用", "quantity": 3, "unit": "桶", "min_stock": 2, "unit_price": 25.0},
        {"id": "INV-006", "name": "咖啡豆", "category": "日用", "quantity": 1, "unit": "袋", "min_stock": 2, "unit_price": 88.0},
        {"id": "INV-007", "name": "垃圾袋", "category": "清洁", "quantity": 5, "unit": "卷", "min_stock": 3, "unit_price": 12.0},
        {"id": "INV-008", "name": "洗手液", "category": "清洁", "quantity": 4, "unit": "瓶", "min_stock": 2, "unit_price": 18.0},
        {"id": "INV-009", "name": "便签本", "category": "文具", "quantity": 12, "unit": "本", "min_stock": 5, "unit_price": 5.0},
        {"id": "INV-010", "name": "HDMI线", "category": "IT耗材", "quantity": 3, "unit": "条", "min_stock": 2, "unit_price": 35.0},
        {"id": "INV-011", "name": "USB-C转接头", "category": "IT耗材", "quantity": 5, "unit": "个", "min_stock": 3, "unit_price": 45.0},
        {"id": "INV-012", "name": "纸巾", "category": "日用", "quantity": 8, "unit": "包", "min_stock": 5, "unit_price": 6.0},
    ]


def _mock_vendors() -> list:
    return [
        {"name": "京东企业购", "category": "办公用品", "contact": "李经理", "phone": "400-000-0000", "terms": "月结30天"},
        {"name": "深圳XX办公", "category": "办公设备", "contact": "张总", "phone": "13800138001", "terms": "预付款"},
        {"name": "顺丰速运", "category": "物流快递", "contact": "客服", "phone": "95338", "terms": "月结"},
    ]


def _mock_purchase_history() -> list:
    return [
        {"date": "2026-04-10", "item": "A4打印纸", "quantity": 20, "cost": 900.0, "vendor": "京东企业购", "status": "已完成"},
        {"date": "2026-04-05", "item": "咖啡豆", "quantity": 3, "cost": 264.0, "vendor": "京东企业购", "status": "已完成"},
        {"date": "2026-03-28", "item": "打印机墨盒", "quantity": 4, "cost": 720.0, "vendor": "京东企业购", "status": "已完成"},
        {"date": "2026-03-15", "item": "员工椅（人体工学）", "quantity": 2, "cost": 3200.0, "vendor": "深圳XX办公", "status": "已完成"},
        {"date": "2026-03-01", "item": "饮用水", "quantity": 10, "cost": 250.0, "vendor": "京东企业购", "status": "已完成"},
    ]


def _mock_licenses() -> list:
    today = date.today()
    return [
        {"id": "LIC-001", "name": "营业执照", "authority": "深圳市市场监督管理局", "number": "91440300XXXXXXXX",
         "issue_date": "2024-01-15", "expiry_date": "2029-01-14", "category": "基础证照", "person": "王总"},
        {"id": "LIC-002", "name": "泰国MSO牌照", "authority": "Bank of Thailand (BoT)", "number": "MSO-TH-XXXX",
         "issue_date": "2024-06-01", "expiry_date": (today + timedelta(days=60)).isoformat(), "category": "支付牌照", "person": "合规部"},
        {"id": "LIC-003", "name": "外汇经营许可", "authority": "国家外汇管理局", "number": "FX-XXXXX",
         "issue_date": "2023-05-10", "expiry_date": (today + timedelta(days=25)).isoformat(), "category": "外汇许可", "person": "合规部"},
        {"id": "LIC-004", "name": "马来西亚EMI牌照", "authority": "Bank Negara Malaysia (BNM)", "number": "EMI-MY-XXXX",
         "issue_date": "2024-03-01", "expiry_date": "2027-02-28", "category": "支付牌照", "person": "合规部"},
        {"id": "LIC-005", "name": "菲律宾BSP许可", "authority": "Bangko Sentral ng Pilipinas", "number": "BSP-PH-XXXX",
         "issue_date": "2024-09-01", "expiry_date": "2027-08-31", "category": "支付牌照", "person": "合规部"},
        {"id": "LIC-006", "name": "印尼OJK许可", "authority": "OJK Indonesia", "number": "OJK-ID-XXXX",
         "issue_date": "2025-01-15", "expiry_date": "2028-01-14", "category": "支付牌照", "person": "合规部"},
        {"id": "LIC-007", "name": "增值电信业务经营许可", "authority": "工业和信息化部", "number": "ICP-XXXXXXX",
         "issue_date": "2024-07-01", "expiry_date": "2029-06-30", "category": "行业资质", "person": "技术部"},
        {"id": "LIC-008", "name": "ISO27001信息安全认证", "authority": "BSI", "number": "IS-XXXXXX",
         "issue_date": "2024-04-01", "expiry_date": (today + timedelta(days=45)).isoformat(), "category": "行业资质", "person": "技术部"},
        {"id": "LIC-009", "name": "PCI DSS认证", "authority": "PCI SSC", "number": "PCI-XXXXX",
         "issue_date": "2025-01-01", "expiry_date": "2026-12-31", "category": "行业资质", "person": "技术部"},
        {"id": "LIC-010", "name": "等保三级认证", "authority": "公安部", "number": "DB-XXXXXXX",
         "issue_date": "2025-03-01", "expiry_date": "2027-02-28", "category": "行业资质", "person": "技术部"},
        {"id": "LIC-011", "name": "办公室租赁合同", "authority": "物业管理公司", "number": "RENT-2025-001",
         "issue_date": "2025-01-01", "expiry_date": "2027-12-31", "category": "基础证照", "person": "行政部"},
        {"id": "LIC-012", "name": "消防安全检查合格证", "authority": "消防局", "number": "FIRE-XXXXXX",
         "issue_date": "2025-06-01", "expiry_date": "2026-05-31", "category": "基础证照", "person": "行政部"},
    ]


def _mock_notice_templates() -> list:
    return [
        {"type": "假期通知", "title": "关于XXXX假期安排的通知", "outline": "假期日期、调休安排、值班安排、注意事项"},
        {"type": "人事通知", "title": "关于XX同事入职/晋升的通知", "outline": "人员信息、岗位、生效日期、欢迎/祝贺"},
        {"type": "政策更新", "title": "关于XX制度调整的通知", "outline": "调整背景、具体变更内容、生效日期、执行要求"},
        {"type": "会议纪要", "title": "XX会议纪要", "outline": "会议时间/地点/参会人、议题、讨论要点、决议、待办"},
        {"type": "设备催还", "title": "关于归还公司设备的提醒", "outline": "设备清单、归还截止日期、联系人"},
        {"type": "一般公告", "title": "关于XX事项的公告", "outline": "事项说明、影响范围、配合要求"},
    ]


def _mock_notice_archive() -> list:
    return [
        {"id": "NTC-001", "title": "关于2026年五一假期安排的通知", "type": "假期通知",
         "content": "# 关于2026年五一假期安排的通知\n\n各位同事：\n\n根据国务院办公厅通知，2026年劳动节放假安排如下：\n\n- **放假时间**：5月1日（周五）至5月3日（周日），共3天\n- **无需调休**\n- **值班安排**：运营部小陈负责5月1日值班\n\n请各部门提前做好工作安排。\n\n行政部\n2026年4月15日",
         "created_at": "2026-04-15", "status": "published"},
        {"id": "NTC-002", "title": "关于李明同事入职的通知", "type": "人事通知",
         "content": "# 欢迎新同事\n\n各位同事：\n\n李明将于4月21日正式加入我们的商务部，担任销售经理一职。\n\n请大家热烈欢迎！\n\n行政部\n2026年4月18日",
         "created_at": "2026-04-18", "status": "published"},
        {"id": "NTC-003", "title": "关于办公区域禁烟规定的通知", "type": "政策更新",
         "content": "# 关于办公区域禁烟规定\n\n为维护办公环境，即日起办公区域全面禁烟。吸烟请到指定区域。\n\n行政部\n2026年4月10日",
         "created_at": "2026-04-10", "status": "published"},
    ]


def _mock_it_assets() -> list:
    return [
        {"id": "IT-001", "tag": "KSH-NB-001", "type": "笔记本电脑", "model": "MacBook Pro 14 M3", "sn": "C02XX001",
         "purchase_date": "2025-06-15", "cost": 14999.0, "status": "使用中", "assigned_to": "张总", "department": "管理层"},
        {"id": "IT-002", "tag": "KSH-NB-002", "type": "笔记本电脑", "model": "MacBook Pro 14 M3", "sn": "C02XX002",
         "purchase_date": "2025-06-15", "cost": 14999.0, "status": "使用中", "assigned_to": "李明", "department": "商务部"},
        {"id": "IT-003", "tag": "KSH-NB-003", "type": "笔记本电脑", "model": "ThinkPad T14s", "sn": "PF3XX003",
         "purchase_date": "2025-07-01", "cost": 8999.0, "status": "使用中", "assigned_to": "王芳", "department": "技术部"},
        {"id": "IT-004", "tag": "KSH-NB-004", "type": "笔记本电脑", "model": "ThinkPad T14s", "sn": "PF3XX004",
         "purchase_date": "2025-07-01", "cost": 8999.0, "status": "使用中", "assigned_to": "赵伟", "department": "技术部"},
        {"id": "IT-005", "tag": "KSH-NB-005", "type": "笔记本电脑", "model": "Dell Latitude 5540", "sn": "DL5XX005",
         "purchase_date": "2025-08-10", "cost": 6999.0, "status": "闲置", "assigned_to": "", "department": ""},
        {"id": "IT-006", "tag": "KSH-NB-006", "type": "笔记本电脑", "model": "MacBook Air M2", "sn": "C02XX006",
         "purchase_date": "2025-03-01", "cost": 9999.0, "status": "维修中", "assigned_to": "陈刚", "department": "运营部"},
        {"id": "IT-007", "tag": "KSH-MN-001", "type": "显示器", "model": "Dell U2723QE 27寸", "sn": "DLMN001",
         "purchase_date": "2025-06-15", "cost": 3599.0, "status": "使用中", "assigned_to": "张总", "department": "管理层"},
        {"id": "IT-008", "tag": "KSH-MN-002", "type": "显示器", "model": "Dell U2723QE 27寸", "sn": "DLMN002",
         "purchase_date": "2025-07-01", "cost": 3599.0, "status": "使用中", "assigned_to": "赵伟", "department": "技术部"},
        {"id": "IT-009", "tag": "KSH-PR-001", "type": "打印机", "model": "HP LaserJet Pro M404dn", "sn": "HPPR001",
         "purchase_date": "2025-05-01", "cost": 2499.0, "status": "使用中", "assigned_to": "公共区域", "department": "行政部"},
        {"id": "IT-010", "tag": "KSH-PH-001", "type": "手机", "model": "iPhone 15", "sn": "IPHN001",
         "purchase_date": "2025-09-01", "cost": 5999.0, "status": "使用中", "assigned_to": "张总", "department": "管理层"},
        {"id": "IT-011", "tag": "KSH-RT-001", "type": "网络设备", "model": "华为AX3 Pro路由器", "sn": "HWRT001",
         "purchase_date": "2025-04-01", "cost": 399.0, "status": "使用中", "assigned_to": "办公室", "department": "行政部"},
        {"id": "IT-012", "tag": "KSH-NB-007", "type": "笔记本电脑", "model": "ThinkPad X1 Carbon", "sn": "PF3XX007",
         "purchase_date": "2024-12-01", "cost": 11999.0, "status": "报废", "assigned_to": "", "department": ""},
    ]


def _mock_maintenance_log() -> list:
    return [
        {"asset_id": "IT-006", "asset_name": "MacBook Air M2 (陈刚)", "date": "2026-04-10", "type": "维修", "desc": "屏幕排线故障更换", "cost": 1200.0, "vendor": "Apple授权服务"},
        {"asset_id": "IT-009", "asset_name": "HP打印机", "date": "2026-03-20", "type": "保养", "desc": "更换硒鼓+清洁", "cost": 380.0, "vendor": "HP售后"},
        {"asset_id": "IT-003", "asset_name": "ThinkPad T14s (王芳)", "date": "2026-02-15", "type": "升级", "desc": "内存16G→32G", "cost": 650.0, "vendor": "联想售后"},
        {"asset_id": "IT-012", "asset_name": "ThinkPad X1 Carbon", "date": "2026-01-05", "type": "维修", "desc": "主板损坏，维修不经济，报废处理", "cost": 0, "vendor": "—"},
    ]


# ============================================================
# 主入口
# ============================================================

def render_role_admin():
    """渲染行政助手角色页面"""
    st.title("📋 行政助手 · AI行政管理中心")
    _color = BRAND_COLORS["text_secondary"]
    st.markdown(
        f"<span style='color:{_color};font-size:{TYPE_SCALE['md']};'>"
        "入离职管理、采购管理、资质证照、公文通知、IT资产——行政事务一站式管理"
        "</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # 初始化Session State
    if "admin_onboarding_records" not in st.session_state:
        st.session_state["admin_onboarding_records"] = _mock_onboarding_records()
    if "admin_inventory" not in st.session_state:
        st.session_state["admin_inventory"] = _mock_inventory()
    if "admin_vendors" not in st.session_state:
        st.session_state["admin_vendors"] = _mock_vendors()
    if "admin_purchase_history" not in st.session_state:
        st.session_state["admin_purchase_history"] = _mock_purchase_history()
    if "admin_licenses" not in st.session_state:
        st.session_state["admin_licenses"] = _mock_licenses()
    if "admin_notice_archive" not in st.session_state:
        st.session_state["admin_notice_archive"] = _mock_notice_archive()
    if "admin_it_assets" not in st.session_state:
        st.session_state["admin_it_assets"] = _mock_it_assets()
    if "admin_maintenance_log" not in st.session_state:
        st.session_state["admin_maintenance_log"] = _mock_maintenance_log()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["入职离职", "采购管理", "资质证照", "公文通知", "IT资产管理"]
    )

    with tab1:
        _render_onboarding()
    with tab2:
        _render_procurement()
    with tab3:
        _render_license_compliance()
    with tab4:
        _render_documents_notices()
    with tab5:
        _render_it_assets()


# ============================================================
# Tab 1: 入职离职
# ============================================================

def _render_onboarding():
    """入职离职管理：AI清单生成 + 进度追踪"""
    st.markdown("**入职离职管理**")
    st.caption("AI生成岗位定制化入离职清单，交互式追踪完成进度")

    mode = st.radio(
        "操作",
        options=["新建入职", "新建离职", "查看进度"],
        horizontal=True,
        key="admin_onb_mode",
    )

    if mode == "新建入职":
        _render_new_onboarding()
    elif mode == "新建离职":
        _render_new_offboarding()
    else:
        _render_onboarding_progress()


def _render_new_onboarding():
    """新建入职流程"""
    with st.expander("📋 新建入职流程", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("员工姓名", key="admin_onb_name")
            position = st.selectbox("岗位", options=["销售", "技术", "行政", "财务", "运营"], key="admin_onb_position")
        with col2:
            department = st.text_input("部门", key="admin_onb_dept", placeholder="如：商务部")
            start_date = st.date_input("入职日期", key="admin_onb_date")

        if st.button("AI生成入职清单", type="primary", key="admin_onb_gen"):
            if not name.strip():
                st.warning("请输入员工姓名")
                return
            _generate_onboarding_checklist(name, position, department, str(start_date))


def _generate_onboarding_checklist(name: str, position: str, department: str, start_date: str):
    """生成入职清单"""
    with st.spinner("AI正在生成入职清单..."):
        if _is_mock_mode():
            templates = _mock_onboarding_templates()
            checklist = [dict(item) for item in templates.get(position, templates["销售"])]
            tips = f"提前1天确认IT设备到位，入职当天优先完成文档签署和账号开通"
        else:
            user_msg = f"新员工信息：姓名={name}，岗位={position}，部门={department}，入职日期={start_date}"
            raw = _llm_call(ONBOARDING_PROMPT, user_msg, agent_name="admin_onboarding")
            result = _parse_json(raw)
            if result:
                checklist = [{"item": c["item"], "category": c.get("category", "其他"),
                              "day_offset": c.get("day_offset", 0), "done": False}
                             for c in result.get("checklist", [])]
                tips = result.get("tips", "")
            else:
                templates = _mock_onboarding_templates()
                checklist = [dict(item) for item in templates.get(position, templates["销售"])]
                tips = ""

        record = {
            "id": f"ONB-{len(st.session_state['admin_onboarding_records']) + 1:03d}",
            "name": name, "position": position, "department": department,
            "type": "onboarding", "start_date": start_date,
            "checklist": checklist, "created_at": datetime.now().isoformat(),
        }
        st.session_state["admin_onboarding_records"].append(record)
        st.success(f"✅ 已为 {name} 生成入职清单（{len(checklist)}项）")
        if tips:
            st.info(f"💡 {tips}")


def _render_new_offboarding():
    """新建离职流程"""
    with st.expander("📋 新建离职流程", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("员工姓名", key="admin_off_name")
            position = st.selectbox("岗位", options=["销售", "技术", "行政", "财务", "运营"], key="admin_off_position")
        with col2:
            department = st.text_input("部门", key="admin_off_dept")
            last_date = st.date_input("最后工作日", key="admin_off_date")

        if st.button("AI生成离职清单", type="primary", key="admin_off_gen"):
            if not name.strip():
                st.warning("请输入员工姓名")
                return
            _generate_offboarding_checklist(name, position, department, str(last_date))


def _generate_offboarding_checklist(name: str, position: str, department: str, last_date: str):
    """生成离职清单"""
    with st.spinner("AI正在生成离职清单..."):
        if _is_mock_mode():
            checklist = [dict(item) for item in _mock_offboarding_template()]
        else:
            user_msg = f"离职员工：姓名={name}，岗位={position}，部门={department}，最后工作日={last_date}"
            raw = _llm_call(OFFBOARDING_PROMPT, user_msg, agent_name="admin_offboarding")
            result = _parse_json(raw)
            if result:
                checklist = [{"item": c["item"], "category": c.get("category", "其他"),
                              "day_offset": c.get("day_offset", 0), "done": False}
                             for c in result.get("checklist", [])]
            else:
                checklist = [dict(item) for item in _mock_offboarding_template()]

        record = {
            "id": f"OFF-{len(st.session_state['admin_onboarding_records']) + 1:03d}",
            "name": name, "position": position, "department": department,
            "type": "offboarding", "start_date": last_date,
            "checklist": checklist, "created_at": datetime.now().isoformat(),
        }
        st.session_state["admin_onboarding_records"].append(record)
        st.success(f"✅ 已为 {name} 生成离职清单（{len(checklist)}项）")


def _render_onboarding_progress():
    """查看入离职进度"""
    records = st.session_state.get("admin_onboarding_records", [])
    if not records:
        st.info("暂无入职/离职记录")
        return

    for record in records:
        checklist = record.get("checklist", [])
        done_count = sum(1 for c in checklist if c.get("done"))
        total = len(checklist)
        pct = done_count / max(total, 1) * 100

        type_label = "🟢 入职" if record["type"] == "onboarding" else "🔴 离职"
        color = BRAND_COLORS["accent"] if pct >= 80 else BRAND_COLORS["warning"] if pct >= 40 else BRAND_COLORS["primary"]

        with st.expander(
            f"{type_label} {record['name']} · {record['position']} · {record['department']} — "
            f"{done_count}/{total} ({pct:.0f}%)"
        ):
            st.progress(pct / 100)

            # 按类别分组显示
            categories = {}
            for i, item in enumerate(checklist):
                cat = item.get("category", "其他")
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append((i, item))

            for cat, items in categories.items():
                st.markdown(f"**{cat}**")
                for idx, item in items:
                    key = f"admin_onb_check_{record['id']}_{idx}"
                    new_val = st.checkbox(item["item"], value=item.get("done", False), key=key)
                    checklist[idx]["done"] = new_val

            # 导出
            md_lines = [f"# {record['name']} {'入职' if record['type'] == 'onboarding' else '离职'}清单\n"]
            md_lines.append(f"岗位：{record['position']} | 部门：{record['department']} | 日期：{record['start_date']}\n")
            for item in checklist:
                check = "✅" if item.get("done") else "⬜"
                md_lines.append(f"- {check} [{item.get('category', '')}] {item['item']}")
            st.download_button(
                "📄 下载清单",
                data="\n".join(md_lines),
                file_name=f"{record['name']}_{'入职' if record['type'] == 'onboarding' else '离职'}清单.md",
                mime="text/markdown",
                key=f"admin_onb_dl_{record['id']}",
            )


# ============================================================
# Tab 2: 采购管理
# ============================================================

def _render_procurement():
    """采购管理：库存 + 采购申请 + 供应商 + 历史"""
    st.markdown("**采购管理**")
    st.caption("办公物料库存追踪、采购申请、供应商管理")

    sub = st.radio("", options=["库存总览", "采购申请", "供应商", "采购历史"],
                   horizontal=True, key="admin_proc_sub")

    if sub == "库存总览":
        _render_inventory()
    elif sub == "采购申请":
        _render_purchase_request()
    elif sub == "供应商":
        _render_vendors()
    else:
        _render_purchase_history()


def _render_inventory():
    """库存总览"""
    inventory = st.session_state["admin_inventory"]

    # 统计
    total_value = sum(i["quantity"] * i["unit_price"] for i in inventory)
    low_stock = [i for i in inventory if i["quantity"] <= i["min_stock"]]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("物品种类", f"{len(inventory)}种")
    with col2:
        st.metric("库存总值", f"¥{total_value:,.0f}")
    with col3:
        if low_stock:
            st.metric("低库存预警", f"{len(low_stock)}项", delta="需补货", delta_color="inverse")
        else:
            st.metric("低库存预警", "0项", delta="库存充足")

    # 低库存预警
    if low_stock:
        st.warning(f"⚠️ 以下物品低于最低库存：{'、'.join(i['name'] for i in low_stock)}")

    # 表格
    df = pd.DataFrame(inventory)
    display_cols = {"name": "物品", "category": "类别", "quantity": "库存", "unit": "单位",
                    "min_stock": "最低库存", "unit_price": "单价(元)"}
    available = [c for c in display_cols if c in df.columns]
    st.dataframe(df[available].rename(columns=display_cols), use_container_width=True, height=350)

    # 添加物品
    with st.expander("➕ 添加物品"):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_name = st.text_input("物品名称", key="admin_inv_name")
            new_cat = st.selectbox("类别", ["办公耗材", "文具", "日用", "清洁", "IT耗材", "其他"], key="admin_inv_cat")
        with col2:
            new_qty = st.number_input("当前库存", value=10, min_value=0, key="admin_inv_qty")
            new_unit = st.text_input("单位", value="个", key="admin_inv_unit")
        with col3:
            new_min = st.number_input("最低库存", value=3, min_value=0, key="admin_inv_min")
            new_price = st.number_input("单价(元)", value=10.0, min_value=0.0, key="admin_inv_price")
        if st.button("添加", key="admin_inv_add"):
            if new_name.strip():
                new_id = f"INV-{len(inventory) + 1:03d}"
                inventory.append({"id": new_id, "name": new_name, "category": new_cat,
                                  "quantity": new_qty, "unit": new_unit,
                                  "min_stock": new_min, "unit_price": new_price})
                st.success(f"已添加：{new_name}")
                st.rerun()

    # 导出
    csv_data = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📄 导出库存CSV", data=csv_data, file_name="库存清单.csv", mime="text/csv", key="admin_inv_export")

    # AI采购分析
    _render_ai_procurement_analysis(inventory, total_value)


def _render_ai_procurement_analysis(inventory: list, total_value: float):
    """AI驱动的智能采购分析"""
    st.markdown("---")
    st.subheader("AI采购智能分析")

    if st.button("生成AI采购建议", type="primary", key="admin_ai_procurement_btn"):
        with st.spinner("AI正在分析采购数据..."):
            inv_summary = "\n".join(
                f"- {i['name']}（{i['category']}）：库存{i['quantity']}{i['unit']}，"
                f"最低库存{i['min_stock']}，单价¥{i['unit_price']}"
                for i in inventory
            )
            history = st.session_state.get("admin_purchase_history", [])
            hist_summary = "\n".join(
                f"- {h['date']} 采购{h['item']} ×{h['quantity']}，¥{h['cost']}，供应商：{h['vendor']}"
                for h in history[-10:]
            ) if history else "暂无采购记录"

            user_msg = PROCUREMENT_USER_TEMPLATE.format(
                inventory_data=inv_summary,
                purchase_history=hist_summary,
                budget=f"库存总值约¥{total_value:,.0f}",
            )

            if _is_mock_mode():
                result = _mock_procurement_analysis(inventory)
            else:
                raw = _llm_call(PROCUREMENT_ANALYSIS_PROMPT, user_msg, agent_name="admin_procurement")
                result = _parse_json(raw)
                if not result:
                    result = _mock_procurement_analysis(inventory)

            st.session_state["admin_ai_procurement"] = result

    result = st.session_state.get("admin_ai_procurement")
    if result:
        # 补货预警
        alerts = result.get("reorder_alerts", [])
        if alerts:
            st.markdown("**补货预警**")
            for a in alerts:
                urgency_colors = {"high": BRAND_COLORS["primary"], "medium": BRAND_COLORS["warning"],
                                  "low": BRAND_COLORS["accent"]}
                uc = urgency_colors.get(a.get("urgency", "low"), BRAND_COLORS["text_secondary"])
                render_border_item(
                    a.get("item", ""), a.get("reason", ""), uc,
                    right_text=f"剩余约{a.get('days_remaining', '?')}天",
                )

        # 成本优化
        opts = result.get("cost_optimization", [])
        if opts:
            st.markdown("**成本优化建议**")
            for o in opts:
                st.markdown(f"- **{o.get('item', '')}**：{o.get('suggestion', '')}（预计节省{o.get('estimated_saving', '')}）")

        # 预算利用
        budget = result.get("budget_utilization", {})
        if budget:
            st.markdown("**预算利用率**")
            st.progress(min(budget.get("used_pct", 0) / 100, 1.0))
            st.caption(f"已使用 {budget.get('used_pct', 0)}% · 预计月底 {budget.get('forecast', '')}")

        if result.get("summary"):
            st.info(result["summary"])


def _mock_procurement_analysis(inventory: list) -> dict:
    """Mock采购分析"""
    low_stock = [i for i in inventory if i["quantity"] <= i["min_stock"]]
    return {
        "cost_optimization": [
            {"item": "A4打印纸", "suggestion": "批量采购（50箱+）可获15%折扣",
             "current_cost": "¥35/箱", "estimated_saving": "¥262/季度", "action": "联系供应商谈批量价"},
            {"item": "碳粉", "suggestion": "考虑兼容碳粉替代原装",
             "current_cost": "¥280/支", "estimated_saving": "¥840/年", "action": "测试兼容品牌质量"},
        ],
        "reorder_alerts": [
            {"item": i["name"], "current_stock": i["quantity"], "daily_usage": 1,
             "days_remaining": max(i["quantity"] - i["min_stock"], 1),
             "urgency": "high" if i["quantity"] < i["min_stock"] else "medium",
             "reason": f"当前库存{i['quantity']}{i['unit']}，低于最低库存{i['min_stock']}{i['unit']}"}
            for i in low_stock[:3]
        ],
        "vendor_evaluation": {
            "summary": "供应商总体表现良好，建议保持2-3家备选",
            "recommendations": ["定期比价（季度）", "建立供应商评分机制"],
        },
        "budget_utilization": {"used_pct": 62, "remaining": 3800, "forecast": "预计使用85%",
                               "alert": None},
        "summary": f"库存{len(inventory)}种物品，{len(low_stock)}项需补货，建议关注批量采购优惠",
    }


def _render_purchase_request():
    """采购申请"""
    requests = st.session_state.get("admin_purchase_requests", [])

    with st.expander("➕ 新建采购申请", expanded=not requests):
        inventory = st.session_state["admin_inventory"]
        item_names = [i["name"] for i in inventory] + ["其他（自定义）"]
        vendors = st.session_state["admin_vendors"]

        col1, col2 = st.columns(2)
        with col1:
            sel_item = st.selectbox("采购物品", options=item_names, key="admin_pr_item")
            if sel_item == "其他（自定义）":
                sel_item = st.text_input("自定义物品名", key="admin_pr_custom")
            pr_qty = st.number_input("数量", value=10, min_value=1, key="admin_pr_qty")
        with col2:
            pr_vendor = st.selectbox("供应商", options=[v["name"] for v in vendors] + ["其他"], key="admin_pr_vendor")
            pr_cost = st.number_input("预估金额(元)", value=100.0, min_value=0.0, key="admin_pr_cost")

        if st.button("提交申请", type="primary", key="admin_pr_submit"):
            if sel_item:
                pr = {"id": f"PR-{len(requests) + 1:03d}", "item": sel_item, "quantity": pr_qty,
                      "cost": pr_cost, "vendor": pr_vendor, "status": "待审批",
                      "date": _today()}
                requests.append(pr)
                st.session_state["admin_purchase_requests"] = requests
                st.success(f"采购申请已提交：{sel_item} × {pr_qty}")

    if requests:
        st.markdown("**采购申请列表**")
        for i, pr in enumerate(requests):
            status_color = {"待审批": BRAND_COLORS["warning"], "已批准": BRAND_COLORS["info"],
                            "已采购": BRAND_COLORS["accent"], "已取消": BRAND_COLORS["text_secondary"]
                            }.get(pr["status"], BRAND_COLORS["text_primary"])
            render_flex_row(
                f"<b>{html.escape(pr['item'])}</b> × {pr['quantity']} · {html.escape(pr['vendor'])} · ¥{pr['cost']:.0f}",
                render_status_badge(pr["status"], status_color),
            )

        # 状态变更
        with st.expander("更新状态"):
            pr_idx = st.selectbox("选择申请", options=range(len(requests)),
                                  format_func=lambda i: f"{requests[i]['id']}: {requests[i]['item']}", key="admin_pr_sel")
            new_status = st.selectbox("新状态", options=["待审批", "已批准", "已采购", "已取消"], key="admin_pr_status")
            if st.button("更新", key="admin_pr_update"):
                requests[pr_idx]["status"] = new_status
                st.success(f"已更新 {requests[pr_idx]['item']} → {new_status}")
                st.rerun()


def _render_vendors():
    """供应商管理"""
    vendors = st.session_state["admin_vendors"]

    df = pd.DataFrame(vendors)
    col_names = {"name": "供应商", "category": "类别", "contact": "联系人", "phone": "电话", "terms": "账期"}
    st.dataframe(df.rename(columns=col_names), use_container_width=True, height=200)

    with st.expander("➕ 添加供应商"):
        col1, col2 = st.columns(2)
        with col1:
            v_name = st.text_input("供应商名称", key="admin_v_name")
            v_cat = st.text_input("类别", key="admin_v_cat", placeholder="如：办公用品")
        with col2:
            v_contact = st.text_input("联系人", key="admin_v_contact")
            v_phone = st.text_input("电话", key="admin_v_phone")
        v_terms = st.text_input("账期", key="admin_v_terms", placeholder="如：月结30天")
        if st.button("添加", key="admin_v_add"):
            if v_name.strip():
                vendors.append({"name": v_name, "category": v_cat, "contact": v_contact,
                                "phone": v_phone, "terms": v_terms})
                st.success(f"已添加供应商：{v_name}")
                st.rerun()


def _render_purchase_history():
    """采购历史"""
    history = st.session_state["admin_purchase_history"]
    if not history:
        st.info("暂无采购记录")
        return

    df = pd.DataFrame(history)
    col_names = {"date": "日期", "item": "物品", "quantity": "数量", "cost": "金额(元)", "vendor": "供应商", "status": "状态"}
    st.dataframe(df.rename(columns=col_names), use_container_width=True, height=250)

    total_cost = sum(h["cost"] for h in history)
    st.caption(f"总采购金额：¥{total_cost:,.0f}")


# ============================================================
# Tab 3: 资质证照
# ============================================================

def _render_license_compliance():
    """资质证照到期监控"""
    st.markdown("**资质证照管理**")
    st.caption("跟踪公司各类证照、牌照到期时间，提前预警确保续期")

    licenses = st.session_state["admin_licenses"]
    today_d = date.today()

    # 计算状态
    for lic in licenses:
        try:
            exp = date.fromisoformat(lic["expiry_date"])
            days_left = (exp - today_d).days
            lic["days_left"] = days_left
            if days_left < 0:
                lic["status"] = "已过期"
            elif days_left <= 30:
                lic["status"] = "紧急"
            elif days_left <= 90:
                lic["status"] = "即将到期"
            else:
                lic["status"] = "有效"
        except (ValueError, TypeError):
            lic["days_left"] = 999
            lic["status"] = "有效"

    valid = [l for l in licenses if l["status"] == "有效"]
    expiring = [l for l in licenses if l["status"] == "即将到期"]
    urgent = [l for l in licenses if l["status"] == "紧急"]
    expired = [l for l in licenses if l["status"] == "已过期"]

    # 仪表盘
    cols = st.columns(4)
    kpis = [
        ("总计", str(len(licenses)), BRAND_COLORS["text_primary"]),
        ("有效", str(len(valid)), BRAND_COLORS["accent"]),
        ("即将到期", str(len(expiring)), BRAND_COLORS["warning"]),
        ("紧急/过期", str(len(urgent) + len(expired)), BRAND_COLORS["primary"]),
    ]
    for col, (label, value, color) in zip(cols, kpis):
        with col:
            render_kpi_card(label, value, color)

    # 到期预警
    alerts = sorted(urgent + expiring + expired, key=lambda x: x.get("days_left", 999))
    if alerts:
        with st.expander(f"⚠️ 到期预警（{len(alerts)}项）", expanded=True):
            for lic in alerts:
                days = lic.get("days_left", 0)
                if days < 0:
                    badge_color = BRAND_COLORS["primary"]
                    badge_text = f"已过期{abs(days)}天"
                elif days <= 30:
                    badge_color = BRAND_COLORS["primary"]
                    badge_text = f"剩余{days}天"
                else:
                    badge_color = BRAND_COLORS["warning"]
                    badge_text = f"剩余{days}天"

                render_flex_row(
                    f"<b>{lic['name']}</b>"
                    f"<span style='font-size:{TYPE_SCALE['base']};color:{BRAND_COLORS['text_secondary']};margin-left:{SPACING['sm']};'>"
                    f"{lic.get('authority', '')} · 负责人: {lic.get('person', '')}</span>",
                    render_status_badge(badge_text, badge_color),
                    border_color=badge_color,
                )

    # 全表
    st.subheader("证照清单")
    category_filter = st.selectbox(
        "筛选类别",
        options=["全部", "基础证照", "支付牌照", "外汇许可", "行业资质"],
        key="admin_lic_filter",
    )
    filtered = licenses if category_filter == "全部" else [l for l in licenses if l.get("category") == category_filter]

    for lic in filtered:
        status = lic.get("status", "有效")
        status_colors = {"有效": BRAND_COLORS["accent"], "即将到期": BRAND_COLORS["warning"],
                         "紧急": BRAND_COLORS["primary"], "已过期": BRAND_COLORS["primary"]}
        sc = status_colors.get(status, BRAND_COLORS["text_secondary"])
        render_flex_row(
            f"<b>{lic['name']}</b>"
            f"<span style='font-size:{TYPE_SCALE['sm']};color:{BRAND_COLORS['text_secondary']};margin-left:{SPACING['sm']};'>"
            f"{lic.get('category', '')} · {lic.get('authority', '')} · 到期: {lic.get('expiry_date', '')}</span>",
            render_status_badge(status, sc),
        )

    # 添加证照
    with st.expander("➕ 添加证照"):
        col1, col2 = st.columns(2)
        with col1:
            l_name = st.text_input("证照名称", key="admin_lic_name")
            l_auth = st.text_input("发证机构", key="admin_lic_auth")
            l_num = st.text_input("证号", key="admin_lic_num")
        with col2:
            l_cat = st.selectbox("类别", ["基础证照", "支付牌照", "外汇许可", "行业资质"], key="admin_lic_cat")
            l_issue = st.date_input("发证日期", key="admin_lic_issue")
            l_expiry = st.date_input("到期日期", key="admin_lic_expiry")
        l_person = st.text_input("负责人", key="admin_lic_person")

        if st.button("添加证照", key="admin_lic_add"):
            if l_name.strip():
                licenses.append({
                    "id": f"LIC-{len(licenses) + 1:03d}", "name": l_name, "authority": l_auth,
                    "number": l_num, "issue_date": str(l_issue), "expiry_date": str(l_expiry),
                    "category": l_cat, "person": l_person,
                })
                st.success(f"已添加：{l_name}")
                st.rerun()

    # 导出
    df_export = pd.DataFrame([{
        "名称": l["name"], "类别": l.get("category", ""), "发证机构": l.get("authority", ""),
        "证号": l.get("number", ""), "发证日期": l.get("issue_date", ""),
        "到期日期": l.get("expiry_date", ""), "状态": l.get("status", ""), "负责人": l.get("person", ""),
    } for l in licenses])
    csv_data = df_export.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📄 导出证照CSV", data=csv_data, file_name="资质证照清单.csv", mime="text/csv", key="admin_lic_export")

    # AI合规分析
    _render_ai_compliance_analysis(licenses)


def _render_ai_compliance_analysis(licenses: list):
    """AI驱动的合规风险分析"""
    st.markdown("---")
    st.subheader("AI合规风险评估")

    if st.button("生成AI合规评估", type="primary", key="admin_ai_compliance_btn"):
        with st.spinner("AI正在评估合规风险..."):
            lic_summary = "\n".join(
                f"- {l['name']}（{l.get('category', '')}）：到期{l.get('expiry_date', '未知')}，"
                f"状态={l.get('status', '未知')}，发证机构={l.get('authority', '')}，负责人={l.get('person', '')}"
                for l in licenses
            )
            user_msg = COMPLIANCE_USER_TEMPLATE.format(
                license_data=lic_summary,
                current_date=str(date.today()),
            )

            if _is_mock_mode():
                result = _mock_compliance_analysis(licenses)
            else:
                raw = _llm_call(COMPLIANCE_ANALYSIS_PROMPT, user_msg, agent_name="admin_compliance")
                result = _parse_json(raw)
                if not result:
                    result = _mock_compliance_analysis(licenses)

            st.session_state["admin_ai_compliance"] = result

    result = st.session_state.get("admin_ai_compliance")
    if result:
        # 风险等级 + 合规评分
        risk = result.get("risk_level", "medium")
        score = result.get("compliance_score", 75)
        risk_colors = {"low": BRAND_COLORS["accent"], "medium": BRAND_COLORS["warning"],
                       "high": BRAND_COLORS["primary"], "critical": BRAND_COLORS["primary"]}
        rc = risk_colors.get(risk, BRAND_COLORS["text_secondary"])

        col1, col2 = st.columns(2)
        with col1:
            render_kpi_card("风险等级", risk.upper(), rc)
        with col2:
            render_kpi_card("合规评分", f"{score}/100", BRAND_COLORS["accent"])

        # 紧急行动
        actions = result.get("urgent_actions", [])
        if actions:
            st.markdown("**紧急行动项**")
            for a in actions:
                st.markdown(
                    f"- **{a.get('license', '')}**：{a.get('action', '')} "
                    f"（截止：{a.get('deadline', '')}） — {a.get('consequence', '')}"
                )

        # 续期计划
        plans = result.get("renewal_plan", [])
        if plans:
            with st.expander(f"续期计划（{len(plans)}项）"):
                for p in plans:
                    st.markdown(
                        f"- **{p.get('license', '')}** 到期{p.get('expiry_date', '')} → "
                        f"建议{p.get('renewal_start', '')}启动续期，"
                        f"预估费用：{p.get('estimated_cost', '待确认')}"
                    )

        # 合规缺口
        gaps = result.get("compliance_gaps", [])
        if gaps:
            with st.expander(f"合规缺口（{len(gaps)}项）"):
                for g in gaps:
                    st.markdown(f"- **{g.get('area', '')}**：{g.get('gap', '')} → {g.get('recommendation', '')}")

        if result.get("summary"):
            st.info(result["summary"])


def _mock_compliance_analysis(licenses: list) -> dict:
    """Mock合规分析"""
    urgent = [l for l in licenses if l.get("status") in ("紧急", "已过期")]
    expiring = [l for l in licenses if l.get("status") == "即将到期"]
    risk = "critical" if urgent else ("high" if expiring else "low")
    score = max(30, 100 - len(urgent) * 20 - len(expiring) * 10)
    return {
        "risk_level": risk,
        "compliance_score": score,
        "urgent_actions": [
            {"license": l["name"], "action": "立即启动续期流程",
             "deadline": l.get("expiry_date", ""),
             "consequence": "过期将导致业务中断",
             "responsible": l.get("person", "行政部")}
            for l in urgent[:3]
        ],
        "renewal_plan": [
            {"license": l["name"], "expiry_date": l.get("expiry_date", ""),
             "renewal_start": "提前60天", "estimated_cost": "待确认",
             "documents_needed": ["申请表", "营业执照副本", "历史经营证明"]}
            for l in (urgent + expiring)[:5]
        ],
        "compliance_gaps": [
            {"area": "数据保护", "gap": "尚未获取PDPA合规认证", "recommendation": "建议Q3前完成"},
        ],
        "regulatory_alerts": ["泰国央行2026年支付牌照新规即将生效"],
        "summary": f"共{len(licenses)}项证照，{len(urgent)}项紧急，{len(expiring)}项即将到期",
    }


# ============================================================
# Tab 4: 公文通知
# ============================================================

def _render_documents_notices():
    """公文通知：AI生成 + 模板库 + 存档"""
    st.markdown("**公文通知**")
    st.caption("AI智能生成内部通知、会议纪要，模板库一键引用")

    sub = st.radio("", options=["AI生成公文", "模板库", "通知存档"],
                   horizontal=True, key="admin_ntc_sub")

    if sub == "AI生成公文":
        _render_notice_generator()
    elif sub == "模板库":
        _render_notice_templates()
    else:
        _render_notice_archive()


def _render_notice_generator():
    """AI公文生成"""
    notice_types = ["假期通知", "人事通知", "政策更新", "会议纪要", "设备催还", "一般公告"]

    col1, col2 = st.columns(2)
    with col1:
        ntc_type = st.selectbox("通知类型", options=notice_types, key="admin_ntc_type")
    with col2:
        ntc_audience = st.selectbox("受众", options=["全体员工", "管理层", "商务部", "技术部", "运营部", "财务部"],
                                    key="admin_ntc_audience")

    ntc_points = st.text_area(
        "关键信息（输入要点，AI自动成文）",
        placeholder="如：五一放假5月1-3日，无调休，运营部小陈1号值班",
        height=100,
        key="admin_ntc_points",
    )

    col1, col2 = st.columns(2)
    with col1:
        ntc_date = st.date_input("生效日期", key="admin_ntc_date")
    with col2:
        ntc_urgency = st.selectbox("紧急程度", ["普通", "重要", "紧急"], key="admin_ntc_urgency")

    if st.button("AI生成", type="primary", key="admin_ntc_gen"):
        if not ntc_points.strip():
            st.warning("请输入关键信息")
            return
        _generate_notice(ntc_type, ntc_points, ntc_audience, str(ntc_date), ntc_urgency)

    result = st.session_state.get("admin_ntc_result")
    if result:
        st.markdown("---")
        st.subheader("生成结果")
        st.markdown(result.get("content", ""))

        if result.get("tips"):
            st.info(f"💡 {result['tips']}")

        col1, col2, col3 = st.columns(3)
        with col1:
            from ui.components.error_handlers import render_copy_button
            render_copy_button(result.get("content", ""))
        with col2:
            st.download_button(
                "📄 下载",
                data=result.get("content", ""),
                file_name=f"{result.get('title', '通知')}.md",
                mime="text/markdown",
                key="admin_ntc_dl",
            )
        with col3:
            if st.button("💾 保存到存档", key="admin_ntc_save"):
                archive = st.session_state["admin_notice_archive"]
                archive.insert(0, {
                    "id": f"NTC-{len(archive) + 1:03d}",
                    "title": result.get("title", ""),
                    "type": st.session_state.get("admin_ntc_type", "一般公告"),
                    "content": result.get("content", ""),
                    "created_at": _today(),
                    "status": "draft",
                })
                st.success("已保存到存档")


def _generate_notice(ntc_type: str, points: str, audience: str, eff_date: str, urgency: str):
    """AI生成通知"""
    with st.spinner("AI正在生成通知..."):
        user_msg = f"通知类型: {ntc_type}\n受众: {audience}\n紧急程度: {urgency}\n生效日期: {eff_date}\n关键信息: {points}"

        if ntc_type == "会议纪要":
            prompt = MEETING_MINUTES_PROMPT
            agent = "admin_notice"
        else:
            prompt = NOTICE_GENERATION_PROMPT
            agent = "admin_notice"

        if _is_mock_mode():
            result = {
                "title": f"关于{points[:15]}的通知" if ntc_type != "会议纪要" else f"{points[:15]}会议纪要",
                "content": _mock_notice_content(ntc_type, points, audience, eff_date),
                "tips": f"建议通过企业微信群发送，并@{audience}",
            }
        else:
            raw = _llm_call(prompt, user_msg, agent_name=agent)
            result = _parse_json(raw)
            if not result:
                result = {
                    "title": f"关于{points[:15]}的通知",
                    "content": _mock_notice_content(ntc_type, points, audience, eff_date),
                    "tips": "",
                }

        st.session_state["admin_ntc_result"] = result


def _mock_notice_content(ntc_type: str, points: str, audience: str, eff_date: str) -> str:
    """Mock通知内容"""
    return f"""# Ksher（酷赛）内部通知

**类型：** {ntc_type}
**发布日期：** {_today()}
**生效日期：** {eff_date}
**受众：** {audience}

---

各位同事：

{points}

请各位知悉并配合执行。如有疑问，请联系行政部。

---

**行政部**
**Ksher（酷赛）**
{_today()}

*⚠️ 本通知由AI辅助生成，请根据实际情况修改后发布。*"""


def _render_notice_templates():
    """模板库"""
    templates = _mock_notice_templates()
    for t in templates:
        with st.expander(f"📝 {t['type']}：{t['title']}"):
            st.caption(f"大纲：{t['outline']}")
            if st.button(f"使用此模板", key=f"admin_tpl_{t['type']}"):
                st.session_state["admin_ntc_type"] = t["type"]
                st.session_state["admin_ntc_points"] = t["outline"]
                st.info("已填入模板信息，请切换到「AI生成公文」Tab完成生成")


def _render_notice_archive():
    """通知存档"""
    archive = st.session_state["admin_notice_archive"]
    if not archive:
        st.info("暂无存档通知")
        return

    type_filter = st.selectbox(
        "筛选类型",
        options=["全部"] + list(set(n.get("type", "") for n in archive)),
        key="admin_ntc_filter",
    )
    filtered = archive if type_filter == "全部" else [n for n in archive if n.get("type") == type_filter]

    for ntc in filtered:
        status_label = {"draft": "📝 草稿", "published": "✅ 已发布", "archived": "📦 已归档"}.get(ntc.get("status", ""), "")
        with st.expander(f"{status_label} {ntc['title']} — {ntc.get('created_at', '')}"):
            st.markdown(ntc.get("content", ""))
            st.download_button(
                "下载",
                data=ntc.get("content", ""),
                file_name=f"{ntc['title']}.md",
                mime="text/markdown",
                key=f"admin_ntc_arch_dl_{ntc['id']}",
            )


# ============================================================
# Tab 5: IT资产管理
# ============================================================

def _render_it_assets():
    """IT资产管理：总览 + 登记 + 维修"""
    st.markdown("**IT资产管理**")
    st.caption("公司IT设备登记、分配追踪、维修记录管理")

    sub = st.radio("", options=["资产总览", "资产登记", "维修记录"],
                   horizontal=True, key="admin_it_sub")

    if sub == "资产总览":
        _render_asset_overview()
    elif sub == "资产登记":
        _render_asset_register()
    else:
        _render_maintenance_records()


def _render_asset_overview():
    """资产总览"""
    assets = st.session_state["admin_it_assets"]

    in_use = [a for a in assets if a["status"] == "使用中"]
    available = [a for a in assets if a["status"] == "闲置"]
    repair = [a for a in assets if a["status"] == "维修中"]
    retired = [a for a in assets if a["status"] == "报废"]
    total_value = sum(a["cost"] for a in assets if a["status"] != "报废")

    # KPI
    cols = st.columns(5)
    kpis = [
        ("总资产", str(len(assets)), BRAND_COLORS["text_primary"]),
        ("使用中", str(len(in_use)), BRAND_COLORS["accent"]),
        ("闲置", str(len(available)), BRAND_COLORS["info"]),
        ("维修中", str(len(repair)), BRAND_COLORS["warning"]),
        ("资产总值", f"¥{total_value:,.0f}", BRAND_COLORS["text_primary"]),
    ]
    for col, (label, value, color) in zip(cols, kpis):
        with col:
            render_kpi_card(label, value, color, size="sm")

    # 筛选
    col1, col2 = st.columns(2)
    with col1:
        type_filter = st.selectbox("筛选类型", options=["全部"] + list(set(a["type"] for a in assets)), key="admin_it_type_f")
    with col2:
        status_filter = st.selectbox("筛选状态", options=["全部", "使用中", "闲置", "维修中", "报废"], key="admin_it_status_f")

    filtered = assets
    if type_filter != "全部":
        filtered = [a for a in filtered if a["type"] == type_filter]
    if status_filter != "全部":
        filtered = [a for a in filtered if a["status"] == status_filter]

    # 表格
    df = pd.DataFrame(filtered)
    display_cols = {"tag": "资产编号", "type": "类型", "model": "品牌型号", "status": "状态",
                    "assigned_to": "使用人", "department": "部门", "cost": "购入价(元)"}
    available_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[available_cols].rename(columns=display_cols), use_container_width=True, height=350)

    # 导出
    csv_data = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📄 导出资产CSV", data=csv_data, file_name="IT资产清单.csv", mime="text/csv", key="admin_it_export")

    # AI资产分析
    _render_ai_asset_analysis(assets)


def _render_ai_asset_analysis(assets: list):
    """AI驱动的IT资产分析"""
    st.markdown("---")
    st.subheader("AI资产分析")

    if st.button("生成AI资产分析", type="primary", key="admin_ai_asset_btn"):
        with st.spinner("AI正在分析IT资产..."):
            asset_summary = "\n".join(
                f"- {a.get('tag', '')} {a['model']}（{a['type']}）：状态={a['status']}，"
                f"购入{a.get('purchase_date', '未知')}，价值¥{a['cost']}，使用人={a.get('assigned_to', '无')}"
                for a in assets
            )
            logs = st.session_state.get("admin_maintenance_log", [])
            maint_summary = "\n".join(
                f"- {l['date']} {l.get('asset_name', '')}：{l['type']} — {l.get('desc', '')}，¥{l['cost']}"
                for l in logs[-10:]
            ) if logs else "暂无维护记录"

            user_msg = ASSET_ANALYSIS_USER_TEMPLATE.format(
                asset_data=asset_summary,
                maintenance_data=maint_summary,
            )

            if _is_mock_mode():
                result = _mock_asset_analysis(assets)
            else:
                raw = _llm_call(ASSET_ANALYSIS_PROMPT, user_msg, agent_name="admin_procurement")
                result = _parse_json(raw)
                if not result:
                    result = _mock_asset_analysis(assets)

            st.session_state["admin_ai_asset"] = result

    result = st.session_state.get("admin_ai_asset")
    if result:
        # 成本概览
        cost_sum = result.get("cost_summary", {})
        if cost_sum:
            cols = st.columns(3)
            with cols[0]:
                st.metric("总资产价值", cost_sum.get("total_asset_value", "N/A"))
            with cols[1]:
                st.metric("年维护费用", cost_sum.get("annual_maintenance", "N/A"))
            with cols[2]:
                st.metric("资产利用率", cost_sum.get("utilization_rate", "N/A"))

        # 生命周期预警
        lifecycle = result.get("lifecycle_alerts", [])
        if lifecycle:
            st.markdown("**生命周期预警**")
            for item in lifecycle:
                status_colors = {"new": BRAND_COLORS["accent"], "good": BRAND_COLORS["accent"],
                                 "aging": BRAND_COLORS["warning"], "critical": BRAND_COLORS["primary"],
                                 "retired": BRAND_COLORS["text_secondary"]}
                sc = status_colors.get(item.get("status", "good"), BRAND_COLORS["text_secondary"])
                render_border_item(
                    item.get("asset", ""),
                    f"使用{item.get('age_years', '?')}年（预期寿命{item.get('expected_life', '?')}年），{item.get('recommendation', '')}",
                    sc,
                )

        # 更换计划
        replacement = result.get("replacement_plan", [])
        if replacement:
            with st.expander(f"更换计划（{len(replacement)}项）"):
                for r in replacement:
                    priority_tag = {"high": "紧急", "medium": "计划中", "low": "观察"}.get(r.get("priority", "low"), "")
                    st.markdown(
                        f"- **{r.get('asset', '')}** [{priority_tag}]：{r.get('reason', '')} → "
                        f"建议：{r.get('suggested_replacement', '')}（预算{r.get('budget', '待定')}）"
                    )

        if result.get("summary"):
            st.info(result["summary"])


def _mock_asset_analysis(assets: list) -> dict:
    """Mock资产分析"""
    total_value = sum(a["cost"] for a in assets if a["status"] != "报废")
    in_use = len([a for a in assets if a["status"] == "使用中"])
    aging = []
    for a in assets:
        pd_str = a.get("purchase_date", "")
        if pd_str:
            try:
                pd_date = date.fromisoformat(pd_str)
                age = (date.today() - pd_date).days / 365
                if age > 3:
                    aging.append({"asset": f"{a['model']} ({a.get('tag', '')})",
                                  "age_years": round(age, 1), "expected_life": 5,
                                  "status": "critical" if age > 4 else "aging",
                                  "recommendation": "建议更换" if age > 4 else "加强维护",
                                  "replacement_cost": f"¥{a['cost'] * 0.8:,.0f}"})
            except (ValueError, TypeError):
                pass
    return {
        "lifecycle_alerts": aging[:5],
        "maintenance_forecast": [],
        "cost_summary": {
            "total_asset_value": f"¥{total_value:,.0f}",
            "annual_maintenance": f"¥{total_value * 0.05:,.0f}",
            "replacement_budget": f"¥{total_value * 0.2:,.0f}",
            "utilization_rate": f"{in_use / len(assets) * 100:.0f}%" if assets else "0%",
        },
        "replacement_plan": [
            {"asset": a["asset"], "reason": "超过预期使用年限",
             "priority": "high" if a.get("status") == "critical" else "medium",
             "suggested_replacement": "同级别新款设备",
             "budget": a.get("replacement_cost", "待定")}
            for a in aging[:3]
        ],
        "summary": f"共{len(assets)}台设备，{len(aging)}台接近报废年限，资产利用率{in_use / len(assets) * 100:.0f}%",
    }


def _render_asset_register():
    """资产登记"""
    assets = st.session_state["admin_it_assets"]

    with st.expander("➕ 登记新资产", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            a_tag = st.text_input("资产编号", value=f"KSH-XX-{len(assets) + 1:03d}", key="admin_it_tag")
            a_type = st.selectbox("类型", ["笔记本电脑", "台式机", "显示器", "手机", "平板", "打印机", "网络设备", "外设", "其他"],
                                  key="admin_it_type")
            a_model = st.text_input("品牌型号", key="admin_it_model", placeholder="如：MacBook Pro 14 M3")
        with col2:
            a_sn = st.text_input("序列号", key="admin_it_sn")
            a_date = st.date_input("购入日期", key="admin_it_pdate")
            a_cost = st.number_input("购入价格(元)", value=5000.0, min_value=0.0, key="admin_it_cost")

        col1, col2 = st.columns(2)
        with col1:
            a_assign = st.text_input("分配给", key="admin_it_assign", placeholder="留空表示闲置")
        with col2:
            a_dept = st.text_input("所属部门", key="admin_it_dept")

        if st.button("登记", type="primary", key="admin_it_reg"):
            if a_model.strip():
                new_asset = {
                    "id": f"IT-{len(assets) + 1:03d}", "tag": a_tag, "type": a_type,
                    "model": a_model, "sn": a_sn, "purchase_date": str(a_date),
                    "cost": a_cost, "status": "使用中" if a_assign.strip() else "闲置",
                    "assigned_to": a_assign, "department": a_dept,
                }
                assets.append(new_asset)
                st.success(f"已登记：{a_model}（{a_tag}）")
                st.rerun()

    # 状态变更
    st.subheader("状态变更")
    if assets:
        sel_asset = st.selectbox(
            "选择资产",
            options=range(len(assets)),
            format_func=lambda i: f"{assets[i]['tag']} · {assets[i]['model']} ({assets[i]['status']})",
            key="admin_it_sel",
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 回收（设为闲置）", key="admin_it_reclaim"):
                assets[sel_asset]["status"] = "闲置"
                assets[sel_asset]["assigned_to"] = ""
                assets[sel_asset]["department"] = ""
                st.success("已回收")
                st.rerun()
        with col2:
            if st.button("🔧 送修", key="admin_it_repair"):
                assets[sel_asset]["status"] = "维修中"
                st.success("已标记为维修中")
                st.rerun()
        with col3:
            if st.button("🗑️ 报废", key="admin_it_retire"):
                assets[sel_asset]["status"] = "报废"
                assets[sel_asset]["assigned_to"] = ""
                st.success("已标记为报废")
                st.rerun()


def _render_maintenance_records():
    """维修记录"""
    logs = st.session_state["admin_maintenance_log"]

    if logs:
        df = pd.DataFrame(logs)
        col_names = {"asset_name": "资产", "date": "日期", "type": "类型", "desc": "说明",
                     "cost": "费用(元)", "vendor": "维修商"}
        available_cols = [c for c in col_names if c in df.columns]
        st.dataframe(df[available_cols].rename(columns=col_names), use_container_width=True, height=250)

        total_cost = sum(l["cost"] for l in logs)
        st.caption(f"维修费用总计：¥{total_cost:,.0f}")

    # 添加记录
    with st.expander("➕ 添加维修记录"):
        assets = st.session_state["admin_it_assets"]
        col1, col2 = st.columns(2)
        with col1:
            m_asset = st.selectbox("资产", options=range(len(assets)),
                                   format_func=lambda i: f"{assets[i]['tag']} · {assets[i]['model']}",
                                   key="admin_mt_asset")
            m_type = st.selectbox("类型", ["维修", "保养", "升级"], key="admin_mt_type")
        with col2:
            m_date = st.date_input("日期", key="admin_mt_date")
            m_cost = st.number_input("费用(元)", value=0.0, min_value=0.0, key="admin_mt_cost")
        m_desc = st.text_input("说明", key="admin_mt_desc", placeholder="如：更换电池")
        m_vendor = st.text_input("维修商", key="admin_mt_vendor")

        if st.button("记录", key="admin_mt_add"):
            asset = assets[m_asset]
            logs.append({
                "asset_id": asset["id"],
                "asset_name": f"{asset['model']} ({asset.get('assigned_to', '')})",
                "date": str(m_date), "type": m_type,
                "desc": m_desc, "cost": m_cost, "vendor": m_vendor,
            })
            st.success("已记录")
            st.rerun()
