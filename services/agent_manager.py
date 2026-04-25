"""
Agent 管理服务层 — 统一管理所有 Agent 配置
"""
import os
import sqlite3
import time
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

import streamlit as st
from config import BASE_DIR

logger = logging.getLogger(__name__)

_GATEWAY_DB = os.path.join(BASE_DIR, "data", "api_gateway.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_GATEWAY_DB), exist_ok=True)
    conn = sqlite3.connect(_GATEWAY_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_agent_registry_db():
    """初始化 Agent 注册表数据库"""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_registry (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name      TEXT NOT NULL UNIQUE,
                display_name    TEXT NOT NULL,
                module          TEXT NOT NULL,
                role            TEXT NOT NULL,
                sub_role        TEXT DEFAULT '',
                description     TEXT DEFAULT '',
                model_key       TEXT DEFAULT 'kimi',
                temperature     REAL DEFAULT 0.7,
                system_prompt   TEXT DEFAULT '',
                usage_count     INTEGER DEFAULT 0,
                success_count   INTEGER DEFAULT 0,
                error_count     INTEGER DEFAULT 0,
                last_used       TEXT,
                avg_latency_ms  REAL DEFAULT 0,
                total_tokens    INTEGER DEFAULT 0,
                status          TEXT DEFAULT 'active',
                is_virtual      INTEGER DEFAULT 0,
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_call_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name  TEXT NOT NULL,
                called_at   TEXT DEFAULT (datetime('now', 'localtime')),
                success     INTEGER DEFAULT 1,
                latency_ms  INTEGER,
                tokens      INTEGER DEFAULT 0,
                error_msg   TEXT
            )
        """)
        # 迁移：添加 is_virtual 列（已有表可能没有）
        try:
            conn.execute("ALTER TABLE agent_registry ADD COLUMN is_virtual INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE agent_registry ADD COLUMN is_active INTEGER DEFAULT 1")
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


@dataclass
class AgentEntry:
    id: int
    agent_name: str
    display_name: str
    module: str
    role: str
    sub_role: str
    description: str
    model_key: str
    temperature: float
    system_prompt: str
    usage_count: int
    success_count: int
    error_count: int
    last_used: Optional[str]
    avg_latency_ms: float
    total_tokens: int
    status: str
    is_virtual: int = 0  # 0=代码注册，1=UI创建
    is_active: int = 1   # 1=活跃，0=已禁用
    created_at: str = ""


# ──────────────────────────────────────────────────────────────
# Agent 角色定义（按员工角色分组）
# ──────────────────────────────────────────────────────────────
ROLE_GROUPS = [
    {
        "role": "市场专员",
        "icon": "📣",
        "description": "内容生成、海报设计、短视频脚本",
        "agents": [
            ("content",    "内容营销专家",    "内容生成",      "ContentAgent 生成朋友圈/小红书/短视频内容",  "kimi",  0.8),
            ("design",     "品牌设计顾问",    "物料设计",      "DesignAgent 生成海报文案和 PPT 结构",          "kimi",  0.6),
            ("video_topic",    "视频选题策划",   "短视频",        "短视频话题策划",                            "kimi",  0.7),
            ("video_script",  "视频脚本生成",   "短视频",        "短视频口播稿生成",                          "kimi",  0.7),
            ("video_analysis","视频数据分析",  "短视频",        "视频内容数据分析",                         "sonnet",0.5),
        ],
    },
    {
        "role": "销售支持",
        "icon": "💼",
        "description": "话术生成、成本分析、方案顾问、异议处理",
        "agents": [
            ("speech",     "销售话术生成",    "话术生成",      "SpeechAgent 生成电梯话术/完整讲解/微信跟进",  "kimi",  0.7),
            ("cost",       "成本分析专家",     "成本分析",      "CostAgent 计算跨境收款总成本对比",            "sonnet",0.3),
            ("proposal",   "解决方案顾问",    "方案生成",      "ProposalAgent 生成8章节专业方案",            "sonnet",0.5),
            ("objection",  "异议处理教练",    "异议处理",      "ObjectionAgent 预判异议并给出3种回复策略",    "kimi",  0.7),
            ("sales_research",    "拜访调研",     "销售调研",   "客户拜访前的情报调研",                        "sonnet",0.5),
            ("sales_product",     "产品顾问",     "销售产品",   "Ksher 产品知识问答",                          "kimi",  0.6),
            ("sales_competitor",  "竞品分析",     "销售竞品",   "竞品对比分析",                               "sonnet",0.5),
            ("sales_risk",       "风控审核",     "销售风控",   "客户风险评估",                               "sonnet",0.5),
            ("sales_docs",       "单证生成",     "销售单证",   "合同/方案文档生成",                          "kimi",  0.6),
        ],
    },
    {
        "role": "客户经理",
        "icon": "🤝",
        "description": "客户简报、客户 enrich、优先级、机会识别",
        "agents": [
            ("acctmgr_briefing",   "客户画像简报",   "客户管理",  "生成客户画像和拜访简报",                   "sonnet",0.5),
            ("acctmgr_enrichment", "客户信息补全",   "客户管理",  "企业信息自动补全",                         "sonnet",0.5),
            ("acctmgr_priority",   "客户优先级排序", "客户管理",  "客户优先级动态排序",                       "sonnet",0.5),
            ("acctmgr_opportunity","商业机会识别",   "客户管理",  "识别客户商业机会",                         "sonnet",0.5),
        ],
    },
    {
        "role": "话术培训师",
        "icon": "🎓",
        "description": "知识问答、培训建议、异议模拟、考核评估",
        "agents": [
            ("knowledge",           "知识问答专家",   "知识库",   "跨境支付知识问答，永远不会被客户问住",     "sonnet",0.5),
            ("trainer_advisor",      "培训顾问",      "培训建议",  "培训计划定制与建议",                      "sonnet",0.5),
            ("trainer_coach",        "培训教练",      "培训内容",  "培训课程内容生成",                        "sonnet",0.5),
            ("trainer_simulator",   "话术模拟对战",   "培训模拟",  "模拟客户异议进行话术训练",                "kimi",  0.7),
            ("trainer_reporter",    "培训效果评估",   "培训考核",  "培训效果报告生成",                        "sonnet",0.5),
        ],
    },
    {
        "role": "数据分析",
        "icon": "📊",
        "description": "异常检测、流失预警、趋势预测、图表生成",
        "agents": [
            ("analyst_anomaly",     "数据异常检测",   "数据监测",  "识别数据异常和异常波动",                  "sonnet",0.5),
            ("analyst_churn",       "流失预警",       "数据监测",  "客户流失风险预测",                        "sonnet",0.5),
            ("analyst_forecast",    "趋势预测",       "数据监测",  "业务趋势预测分析",                        "sonnet",0.5),
            ("analyst_risk",        "风险识别",       "数据监测",  "业务风险识别",                            "sonnet",0.5),
            ("analyst_chart",       "图表生成",       "数据可视化","自动生成业务图表",                       "kimi",  0.6),
            ("analyst_quality",    "数据质量评估",   "数据质量",  "数据质量评估",                           "sonnet",0.5),
        ],
    },
    {
        "role": "财务经理",
        "icon": "💰",
        "description": "财务健康诊断、往来核对、利润率分析、成本追踪",
        "agents": [
            ("finance_health",     "财务健康诊断",   "财务诊断",  "财务健康度评估",                         "sonnet",0.5),
            ("finance_reconcile",  "往来核对",       "财务核对",  "供应商/客户往来核对",                    "sonnet",0.5),
            ("finance_margin",     "利润率分析",     "财务分析",  "产品/客户利润率分析",                    "sonnet",0.5),
            ("finance_cost",       "成本追踪",       "财务分析",  "成本结构分析",                           "sonnet",0.5),
            ("finance_fx",         "汇率分析",       "财务分析",  "多币种汇率分析",                         "sonnet",0.5),
            ("finance_report",    "财务报表生成",    "财务报告",  "自动生成财务报表",                        "kimi",  0.6),
        ],
    },
    {
        "role": "行政助手",
        "icon": "🏢",
        "description": "入职培训、采购评估、合规检查、通知生成",
        "agents": [
            ("admin_onboarding",   "新员工入职",    "行政管理",  "新员工入职培训计划生成",                  "kimi",  0.6),
            ("admin_offboarding",  "员工离职",       "行政管理",  "离职交接清单生成",                      "kimi",  0.6),
            ("admin_procurement",   "采购评估",       "行政采购",  "采购供应商评估",                         "sonnet",0.5),
            ("admin_compliance",   "合规检查",       "合规管理",  "合规性检查",                             "sonnet",0.5),
            ("admin_notice",       "通知生成",       "行政通知",  "团队通知生成",                           "kimi",  0.6),
        ],
    },
    {
        "role": "内容精修",
        "icon": "✏️",
        "description": "去除AI味、多轮修改",
        "agents": [
            ("refiner",   "内容精修师",  "内容质量",  "去除AI味、多轮修改内容",               "kimi",  0.7),
        ],
    },
]


def register_or_update_agent(
    agent_name: str, display_name: str, module: str, role: str,
    sub_role: str = "", description: str = "", model_key: str = "kimi",
    temperature: float = 0.7, system_prompt: str = "",
    is_virtual: int = 0, is_active: int = 1,
) -> dict:
    """
    注册或更新一个 Agent 条目（支持代码注册和虚拟Agent）

    Args:
        is_virtual: 0=代码注册的真实Agent，1=UI创建的虚拟Agent
        is_active: 1=活跃，0=禁用
    """
    init_agent_registry_db()
    conn = _get_conn()
    try:
        existing = conn.execute(
            "SELECT id, is_virtual FROM agent_registry WHERE agent_name = ?", (agent_name,)
        ).fetchone()
        if existing:
            # 已存在：仅当现有为代码注册时允许覆盖（虚拟Agent不可被代码覆盖）
            if existing["is_virtual"] == 1 and is_virtual == 0:
                return {"success": False, "message": "该Agent由UI创建，禁止代码覆盖", "id": existing["id"]}
            conn.execute(
                """UPDATE agent_registry
                   SET display_name=?, module=?, role=?, sub_role=?, description=?,
                       model_key=?, temperature=?, system_prompt=?,
                       is_active=?, status=CASE WHEN ?=1 THEN 'active' ELSE 'inactive' END
                   WHERE agent_name=?""",
                (display_name, module, role, sub_role, description,
                 model_key, temperature, system_prompt,
                 is_active, is_active, agent_name),
            )
            return {"success": True, "message": "已更新", "id": existing["id"]}
        else:
            cursor = conn.execute(
                """INSERT INTO agent_registry
                   (agent_name, display_name, module, role, sub_role, description,
                    model_key, temperature, system_prompt, is_virtual, is_active)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (agent_name, display_name, module, role, sub_role, description,
                 model_key, temperature, system_prompt, is_virtual, is_active),
            )
            conn.commit()
            return {"success": True, "message": "已注册", "id": cursor.lastrowid}
    finally:
        conn.close()


def get_or_create_virtual_agent(
    agent_name: str,
    display_name: str,
    role: str,
    description: str = "",
    model_key: str = "kimi",
    temperature: float = 0.7,
    sub_role: str = "",
) -> dict:
    """通过UI创建或获取虚拟Agent"""
    return register_or_update_agent(
        agent_name=agent_name,
        display_name=display_name,
        module="virtual",
        role=role,
        sub_role=sub_role,
        description=description,
        model_key=model_key,
        temperature=temperature,
        system_prompt="",
        is_virtual=1,
        is_active=1,
    )


def unregister_agent(agent_name: str) -> dict:
    """注销一个虚拟Agent（代码注册的Agent不可注销）"""
    init_agent_registry_db()
    conn = _get_conn()
    try:
        existing = conn.execute(
            "SELECT is_virtual FROM agent_registry WHERE agent_name = ?", (agent_name,)
        ).fetchone()
        if not existing:
            return {"success": False, "message": "Agent不存在"}
        if existing["is_virtual"] == 0:
            return {"success": False, "message": "禁止注销代码注册的Agent"}
        conn.execute("DELETE FROM agent_registry WHERE agent_name = ?", (agent_name,))
        conn.commit()
        return {"success": True, "message": "已注销"}
    finally:
        conn.close()


def toggle_agent_active(agent_name: str) -> dict:
    """激活/停用一个Agent"""
    init_agent_registry_db()
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT is_active FROM agent_registry WHERE agent_name = ?", (agent_name,)
        ).fetchone()
        if not row:
            return {"success": False, "message": "Agent不存在"}
        new_state = 0 if row["is_active"] == 1 else 1
        conn.execute(
            "UPDATE agent_registry SET is_active=?, status=? WHERE agent_name=?",
            (new_state, "active" if new_state == 1 else "inactive", agent_name),
        )
        conn.commit()
        return {"success": True, "message": "已" + ("激活" if new_state == 1 else "停用")}
    finally:
        conn.close()


def get_all_agents(include_inactive: bool = True) -> list[AgentEntry]:
    """读取所有已注册的 Agent"""
    init_agent_registry_db()
    conn = _get_conn()
    try:
        query = "SELECT * FROM agent_registry"
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += " ORDER BY is_virtual ASC, role, sub_role, display_name"
        rows = conn.execute(query).fetchall()
        return [AgentEntry(**dict(r)) for r in rows]
    finally:
        conn.close()
    """读取所有已注册的 Agent"""
    init_agent_registry_db()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM agent_registry ORDER BY role, sub_role, display_name"
        ).fetchall()
        return [AgentEntry(**dict(r)) for r in rows]
    finally:
        conn.close()


def get_agents_by_role(role: str, include_inactive: bool = True) -> list[AgentEntry]:
    """根据角色筛选 Agent"""
    agents = get_all_agents(include_inactive=include_inactive)
    return [a for a in agents if a.role == role]


def record_agent_call(agent_name: str, success: bool, latency_ms: int = 0,
                      tokens: int = 0, error_msg: str = ""):
    """记录 Agent 调用"""
    try:
        conn = _get_conn()
        try:
            conn.execute(
                """INSERT INTO agent_call_log
                   (agent_name, success, latency_ms, tokens, error_msg)
                   VALUES (?,?,?,?,?)""",
                (agent_name, int(success), latency_ms, tokens, error_msg),
            )
            conn.execute(
                """UPDATE agent_registry
                   SET usage_count = usage_count + 1,
                       success_count = success_count + ?,
                       error_count = error_count + ?,
                       last_used = datetime('now', 'localtime')
                   WHERE agent_name = ?""",
                (int(success), int(not success), agent_name),
            )
            conn.execute(
                """UPDATE agent_registry
                   SET avg_latency_ms =
                       (avg_latency_ms * (usage_count - 1) + ?) / NULLIF(usage_count, 0),
                       total_tokens = total_tokens + ?
                   WHERE agent_name = ?""",
                (latency_ms, tokens, agent_name),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


def sync_agent_registry():
    """
    将所有预定义 Agent 同步到数据库

    同步规则：
    - 代码注册的Agent：允许覆盖已有条目（包括虚拟Agent的同名条目）
    - 虚拟Agent：不受代码同步影响（UI创建优先）
    - 同步时激活所有代码注册的Agent
    - 旧版死代码Agent：自动停用
    """
    init_agent_registry_db()

    # 收集当前代码定义的Agent名
    current_code_agents = set()
    for group in ROLE_GROUPS:
        for (agent_name, *_) in group["agents"]:
            current_code_agents.add(agent_name)

    conn = _get_conn()
    try:
        # 1. 注册/更新代码定义的Agent
        for group in ROLE_GROUPS:
            role = group["role"]
            for (agent_name, display_name, sub_role, description, model_key, temperature) in group["agents"]:
                existing = conn.execute(
                    "SELECT id, is_virtual FROM agent_registry WHERE agent_name = ?", (agent_name,)
                ).fetchone()
                if existing and existing["is_virtual"] == 1:
                    continue  # 虚拟Agent优先，不被覆盖
                conn.execute(
                    """INSERT OR REPLACE INTO agent_registry
                       (agent_name, display_name, module, role, sub_role, description,
                        model_key, temperature, is_virtual, is_active, status)
                       VALUES (?,?,?,?,?,?,?,?,0,1,'active')""",
                    (agent_name, display_name, module := "agents", role, sub_role, description,
                     model_key, temperature),
                )

        # 2. 停用旧版死代码Agent（代码已删除但DB仍有记录）
        db_agents = conn.execute("SELECT agent_name, is_virtual FROM agent_registry").fetchall()
        for row in db_agents:
            if row["is_virtual"] == 0 and row["agent_name"] not in current_code_agents:
                conn.execute(
                    "UPDATE agent_registry SET is_active=0, status='deprecated' WHERE agent_name=?",
                    (row["agent_name"],)
                )

        conn.commit()
    finally:
        conn.close()


def get_agent_stats() -> dict:
    """获取 Agent 统计信息"""
    agents = get_all_agents(include_inactive=True)
    total = len(agents)
    active = len([a for a in agents if a.is_active == 1])
    virtual = len([a for a in agents if a.is_virtual == 1])
    total_calls = sum(a.usage_count for a in agents)
    total_success = sum(a.success_count for a in agents)
    total_errors = sum(a.error_count for a in agents)
    by_role = {}
    for a in agents:
        by_role.setdefault(a.role, []).append(a)
    return {
        "total": total,
        "active": active,
        "virtual": virtual,
        "total_calls": total_calls,
        "total_success": total_success,
        "total_errors": total_errors,
        "avg_success_rate": round(total_success / total_calls * 100, 1) if total_calls > 0 else 0,
        "by_role": by_role,
    }
