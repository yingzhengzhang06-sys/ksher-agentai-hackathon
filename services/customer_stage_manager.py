"""
客户阶段管理器 — 销售支持数字员工的核心组件

管理客户从线索到签约的全生命周期阶段流转：
潜在客户 → 初次接触 → 需求确认 → 方案沟通 → 签约中 → 已签约

功能：
1. 阶段定义与转换规则
2. 阶段停留时长追踪
3. 转化率统计分析
4. 流失风险预警
5. 推进建议生成
"""
import os
import sys
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# 确保能导入项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


class CustomerStage(Enum):
    """客户阶段枚举"""
    LEAD = "潜在客户"
    FIRST_CONTACT = "初次接触"
    NEEDS_CONFIRMED = "需求确认"
    PROPOSAL = "方案沟通"
    CONTRACTING = "签约中"
    SIGNED = "已签约"
    LOST = "已流失"


# 阶段顺序（用于计算推进进度）
STAGE_ORDER = [
    CustomerStage.LEAD,
    CustomerStage.FIRST_CONTACT,
    CustomerStage.NEEDS_CONFIRMED,
    CustomerStage.PROPOSAL,
    CustomerStage.CONTRACTING,
    CustomerStage.SIGNED,
]

# 允许的阶段转换（从 → [可转到的阶段列表]）
ALLOWED_TRANSITIONS = {
    CustomerStage.LEAD: [CustomerStage.FIRST_CONTACT, CustomerStage.LOST],
    CustomerStage.FIRST_CONTACT: [CustomerStage.NEEDS_CONFIRMED, CustomerStage.LOST, CustomerStage.LEAD],
    CustomerStage.NEEDS_CONFIRMED: [CustomerStage.PROPOSAL, CustomerStage.LOST, CustomerStage.FIRST_CONTACT],
    CustomerStage.PROPOSAL: [CustomerStage.CONTRACTING, CustomerStage.LOST, CustomerStage.NEEDS_CONFIRMED],
    CustomerStage.CONTRACTING: [CustomerStage.SIGNED, CustomerStage.LOST, CustomerStage.PROPOSAL],
    CustomerStage.SIGNED: [CustomerStage.LOST],  # 已签约客户也可能流失
    CustomerStage.LOST: [CustomerStage.LEAD],  # 流失后可重新激活
}

# 各阶段标准停留时长（天）— 用于预警
STAGE_BENCHMARK_DAYS = {
    CustomerStage.LEAD: 7,
    CustomerStage.FIRST_CONTACT: 5,
    CustomerStage.NEEDS_CONFIRMED: 10,
    CustomerStage.PROPOSAL: 14,
    CustomerStage.CONTRACTING: 7,
}


@dataclass
class CustomerProfile:
    """客户档案"""
    customer_id: str
    company_name: str
    industry: str = ""
    country: str = ""
    monthly_volume: float = 0.0
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    current_stage: str = CustomerStage.LEAD.value
    stage_entered_at: str = ""
    created_at: str = ""
    updated_at: str = ""
    assigned_sales: str = ""  # 负责销售
    tags: str = ""  # JSON list
    notes: str = ""
    risk_level: str = "低"  # 低/中/高


@dataclass
class StageTransition:
    """阶段转换记录"""
    transition_id: str
    customer_id: str
    from_stage: str
    to_stage: str
    transitioned_at: str
    reason: str = ""
    triggered_by: str = "system"  # system / manual / auto


@dataclass
class StageMetrics:
    """阶段指标"""
    stage: str
    customer_count: int
    avg_days: float
    conversion_rate: float  # 进入下一阶段的比例
    churn_rate: float  # 流失比例
    overdue_count: int  # 超期停留数量


class CustomerStageManager:
    """
    客户阶段管理器

    核心能力：
    1. 客户档案CRUD
    2. 阶段转换控制（校验转换规则）
    3. 停留时长追踪
    4. 转化率统计
    5. 流失风险预警
    """

    DB_PATH = os.path.join(_PROJECT_ROOT, "data", "customer_stages.db")

    def __init__(self):
        self._init_db()

    def _init_db(self):
        """初始化SQLite数据库"""
        os.makedirs(os.path.dirname(self.DB_PATH), exist_ok=True)
        conn = sqlite3.connect(self.DB_PATH)

        # 客户档案表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                industry TEXT,
                country TEXT,
                monthly_volume REAL DEFAULT 0,
                contact_name TEXT,
                contact_phone TEXT,
                contact_email TEXT,
                current_stage TEXT DEFAULT '潜在客户',
                stage_entered_at TEXT,
                created_at TEXT,
                updated_at TEXT,
                assigned_sales TEXT,
                tags TEXT,
                notes TEXT,
                risk_level TEXT DEFAULT '低'
            )
        """)

        # 阶段转换历史表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stage_transitions (
                transition_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                from_stage TEXT,
                to_stage TEXT NOT NULL,
                transitioned_at TEXT,
                reason TEXT,
                triggered_by TEXT DEFAULT 'system',
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
        """)

        # 创建索引
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_stage ON customers(current_stage)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transition_customer ON stage_transitions(customer_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transition_date ON stage_transitions(transitioned_at)
        """)

        conn.commit()
        conn.close()

    # ============================================================
    # 客户档案管理
    # ============================================================

    def create_customer(self, company_name: str, **kwargs) -> CustomerProfile:
        """创建新客户，初始阶段为'潜在客户'"""
        customer_id = self._generate_id(company_name)
        now = datetime.now().isoformat()

        profile = CustomerProfile(
            customer_id=customer_id,
            company_name=company_name,
            industry=kwargs.get("industry", ""),
            country=kwargs.get("country", ""),
            monthly_volume=kwargs.get("monthly_volume", 0.0),
            contact_name=kwargs.get("contact_name", ""),
            contact_phone=kwargs.get("contact_phone", ""),
            contact_email=kwargs.get("contact_email", ""),
            current_stage=CustomerStage.LEAD.value,
            stage_entered_at=now,
            created_at=now,
            updated_at=now,
            assigned_sales=kwargs.get("assigned_sales", ""),
            tags=json.dumps(kwargs.get("tags", []), ensure_ascii=False),
            notes=kwargs.get("notes", ""),
            risk_level="低",
        )

        conn = sqlite3.connect(self.DB_PATH)
        conn.execute(
            """INSERT INTO customers
               (customer_id, company_name, industry, country, monthly_volume,
                contact_name, contact_phone, contact_email, current_stage,
                stage_entered_at, created_at, updated_at, assigned_sales,
                tags, notes, risk_level)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (profile.customer_id, profile.company_name, profile.industry,
             profile.country, profile.monthly_volume, profile.contact_name,
             profile.contact_phone, profile.contact_email, profile.current_stage,
             profile.stage_entered_at, profile.created_at, profile.updated_at,
             profile.assigned_sales, profile.tags, profile.notes, profile.risk_level),
        )
        conn.commit()
        conn.close()

        # 记录初始阶段
        self._record_transition(customer_id, "", CustomerStage.LEAD.value, now, "客户创建", "system")

        return profile

    def get_customer(self, customer_id: str) -> Optional[CustomerProfile]:
        """获取客户档案"""
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
        ).fetchone()
        conn.close()

        if not row:
            return None
        return self._row_to_profile(row)

    def get_customer_by_name(self, company_name: str) -> Optional[CustomerProfile]:
        """通过公司名获取客户"""
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM customers WHERE company_name = ?", (company_name,)
        ).fetchone()
        conn.close()

        if not row:
            return None
        return self._row_to_profile(row)

    def update_customer(self, customer_id: str, **kwargs) -> bool:
        """更新客户信息（不修改阶段）"""
        allowed_fields = [
            "company_name", "industry", "country", "monthly_volume",
            "contact_name", "contact_phone", "contact_email",
            "assigned_sales", "tags", "notes",
        ]
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [customer_id]

        conn = sqlite3.connect(self.DB_PATH)
        conn.execute(f"UPDATE customers SET {set_clause} WHERE customer_id = ?", values)
        conn.commit()
        conn.close()
        return True

    def list_customers(self, stage: Optional[str] = None,
                       assigned_sales: Optional[str] = None,
                       limit: int = 100) -> List[CustomerProfile]:
        """列出客户，支持按阶段和负责人过滤"""
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row

        conditions = []
        params = []
        if stage:
            conditions.append("current_stage = ?")
            params.append(stage)
        if assigned_sales:
            conditions.append("assigned_sales = ?")
            params.append(assigned_sales)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM customers {where} ORDER BY updated_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()

        return [self._row_to_profile(r) for r in rows]

    # ============================================================
    # 阶段转换
    # ============================================================

    def transition_stage(self, customer_id: str, to_stage: str,
                         reason: str = "", triggered_by: str = "manual") -> Dict[str, Any]:
        """
        转换客户阶段

        Returns:
            {"success": bool, "message": str, "transition": StageTransition}
        """
        customer = self.get_customer(customer_id)
        if not customer:
            return {"success": False, "message": f"客户不存在: {customer_id}", "transition": None}

        from_stage = customer.current_stage

        # 校验转换是否合法
        from_enum = self._stage_to_enum(from_stage)
        to_enum = self._stage_to_enum(to_stage)

        if from_enum == to_enum:
            return {"success": False, "message": "目标阶段与当前阶段相同", "transition": None}

        allowed = ALLOWED_TRANSITIONS.get(from_enum, [])
        if to_enum not in allowed:
            allowed_names = [s.value for s in allowed]
            return {
                "success": False,
                "message": f"不允许从「{from_stage}」转到「{to_stage}」。允许的目标: {allowed_names}",
                "transition": None,
            }

        now = datetime.now().isoformat()

        # 更新客户阶段
        conn = sqlite3.connect(self.DB_PATH)
        conn.execute(
            "UPDATE customers SET current_stage = ?, stage_entered_at = ?, updated_at = ? WHERE customer_id = ?",
            (to_stage, now, now, customer_id),
        )
        conn.commit()
        conn.close()

        # 记录转换
        transition = self._record_transition(customer_id, from_stage, to_stage, now, reason, triggered_by)

        return {"success": True, "message": f"阶段转换成功: {from_stage} → {to_stage}", "transition": transition}

    def get_stage_history(self, customer_id: str) -> List[StageTransition]:
        """获取客户的阶段转换历史"""
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM stage_transitions WHERE customer_id = ? ORDER BY transitioned_at",
            (customer_id,),
        ).fetchall()
        conn.close()

        return [
            StageTransition(
                transition_id=r["transition_id"],
                customer_id=r["customer_id"],
                from_stage=r["from_stage"] or "",
                to_stage=r["to_stage"],
                transitioned_at=r["transitioned_at"],
                reason=r["reason"] or "",
                triggered_by=r["triggered_by"] or "system",
            )
            for r in rows
        ]

    # ============================================================
    # 统计与指标
    # ============================================================

    def get_stage_metrics(self) -> List[StageMetrics]:
        """获取各阶段指标统计"""
        conn = sqlite3.connect(self.DB_PATH)

        metrics = []
        for stage in STAGE_ORDER:
            stage_name = stage.value

            # 该阶段的客户数
            count = conn.execute(
                "SELECT COUNT(*) FROM customers WHERE current_stage = ?", (stage_name,)
            ).fetchone()[0]

            # 平均停留时长
            avg_days = self._calc_avg_stage_days(conn, stage_name)

            # 转化率（进入下一阶段 / 总离开数）
            conversion_rate = self._calc_conversion_rate(conn, stage_name)

            # 流失率
            churn_rate = self._calc_churn_rate(conn, stage_name)

            # 超期数量
            overdue = self._count_overdue(conn, stage_name)

            metrics.append(StageMetrics(
                stage=stage_name,
                customer_count=count,
                avg_days=avg_days,
                conversion_rate=conversion_rate,
                churn_rate=churn_rate,
                overdue_count=overdue,
            ))

        conn.close()
        return metrics

    def get_funnel_stats(self) -> Dict[str, Any]:
        """获取销售漏斗统计"""
        conn = sqlite3.connect(self.DB_PATH)

        total = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        signed = conn.execute(
            "SELECT COUNT(*) FROM customers WHERE current_stage = ?", (CustomerStage.SIGNED.value,)
        ).fetchone()[0]
        lost = conn.execute(
            "SELECT COUNT(*) FROM customers WHERE current_stage = ?", (CustomerStage.LOST.value,)
        ).fetchone()[0]
        active = total - lost

        conn.close()

        return {
            "total_customers": total,
            "active_customers": active,
            "signed_customers": signed,
            "lost_customers": lost,
            "overall_conversion_rate": round(signed / active * 100, 1) if active > 0 else 0,
            "churn_rate": round(lost / total * 100, 1) if total > 0 else 0,
        }

    # ============================================================
    # 预警
    # ============================================================

    def get_overdue_customers(self, days_override: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
        """
        获取超期停留的客户列表

        Args:
            days_override: 自定义各阶段超期天数阈值
        """
        benchmark = days_override or {k.value: v for k, v in STAGE_BENCHMARK_DAYS.items()}
        now = datetime.now()
        overdue_list = []

        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row

        for stage_name, max_days in benchmark.items():
            rows = conn.execute(
                "SELECT * FROM customers WHERE current_stage = ?", (stage_name,)
            ).fetchall()

            for row in rows:
                entered = datetime.fromisoformat(row["stage_entered_at"])
                days = (now - entered).days
                if days > max_days:
                    overdue_list.append({
                        "customer_id": row["customer_id"],
                        "company_name": row["company_name"],
                        "current_stage": stage_name,
                        "days_in_stage": days,
                        "overdue_by": days - max_days,
                        "assigned_sales": row["assigned_sales"],
                        "risk_level": row["risk_level"],
                    })

        conn.close()

        # 按超期天数降序排列
        overdue_list.sort(key=lambda x: x["overdue_by"], reverse=True)
        return overdue_list

    def get_risk_customers(self) -> List[Dict[str, Any]]:
        """获取高风险客户列表（超期严重或已标记高风险）"""
        overdue = self.get_overdue_customers()

        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row
        high_risk = conn.execute(
            "SELECT * FROM customers WHERE risk_level = '高' AND current_stage != ?",
            (CustomerStage.LOST.value,),
        ).fetchall()
        conn.close()

        risk_list = overdue[:]
        existing_ids = {r["customer_id"] for r in risk_list}

        for row in high_risk:
            if row["customer_id"] not in existing_ids:
                entered = datetime.fromisoformat(row["stage_entered_at"])
                days = (datetime.now() - entered).days
                risk_list.append({
                    "customer_id": row["customer_id"],
                    "company_name": row["company_name"],
                    "current_stage": row["current_stage"],
                    "days_in_stage": days,
                    "overdue_by": 0,
                    "assigned_sales": row["assigned_sales"],
                    "risk_level": "高",
                    "reason": "手动标记高风险",
                })

        return risk_list

    def update_risk_level(self, customer_id: str, risk_level: str) -> bool:
        """更新客户风险等级（低/中/高）"""
        if risk_level not in ("低", "中", "高"):
            return False
        conn = sqlite3.connect(self.DB_PATH)
        conn.execute(
            "UPDATE customers SET risk_level = ?, updated_at = ? WHERE customer_id = ?",
            (risk_level, datetime.now().isoformat(), customer_id),
        )
        conn.commit()
        conn.close()
        return True

    # ============================================================
    # 推进建议
    # ============================================================

    def get_next_action_suggestion(self, customer_id: str) -> Dict[str, Any]:
        """
        基于客户当前阶段和停留时长，生成下一步行动建议
        """
        customer = self.get_customer(customer_id)
        if not customer:
            return {"error": "客户不存在"}

        stage = self._stage_to_enum(customer.current_stage)
        entered = datetime.fromisoformat(customer.stage_entered_at)
        days = (datetime.now() - entered).days
        benchmark = STAGE_BENCHMARK_DAYS.get(stage, 7)
        overdue = days > benchmark

        suggestions = {
            CustomerStage.LEAD: {
                "action": "首次 outreach",
                "suggestion": "发送产品介绍邮件或 cold call，了解客户是否有跨境收款需求",
                "urgency": "高" if overdue else "中",
            },
            CustomerStage.FIRST_CONTACT: {
                "action": "需求挖掘",
                "suggestion": "安排深度沟通，了解客户当前收款方式、痛点、目标国家、月流水",
                "urgency": "高" if overdue else "中",
            },
            CustomerStage.NEEDS_CONFIRMED: {
                "action": "方案准备",
                "suggestion": "基于需求生成定制方案（费率对比 + 到账速度 + 合规优势），预约方案演示",
                "urgency": "高" if overdue else "中",
            },
            CustomerStage.PROPOSAL: {
                "action": "异议处理 + 促成签约",
                "suggestion": "处理价格/安全/流程异议，提供限时优惠或免费试用降低门槛",
                "urgency": "紧急" if overdue else "高",
            },
            CustomerStage.CONTRACTING: {
                "action": "加速开户流程",
                "suggestion": "协助准备KYC材料，协调合规团队加速审批，每日跟进进度",
                "urgency": "紧急" if overdue else "高",
            },
            CustomerStage.SIGNED: {
                "action": "客户成功",
                "suggestion": "安排首笔交易指导，定期回访，挖掘增购/转介绍机会",
                "urgency": "低",
            },
        }

        base = suggestions.get(stage, {"action": "跟进", "suggestion": "持续跟进", "urgency": "中"})
        return {
            "customer_id": customer_id,
            "company_name": customer.company_name,
            "current_stage": customer.current_stage,
            "days_in_stage": days,
            "benchmark_days": benchmark,
            "is_overdue": overdue,
            **base,
        }

    # ============================================================
    # 内部辅助方法
    # ============================================================

    def _generate_id(self, company_name: str) -> str:
        """生成客户ID"""
        hash_str = hashlib.md5(f"{company_name}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        return f"CUST_{hash_str.upper()}"

    def _stage_to_enum(self, stage_name: str) -> CustomerStage:
        """阶段名称转枚举"""
        for s in CustomerStage:
            if s.value == stage_name:
                return s
        return CustomerStage.LEAD

    def _record_transition(self, customer_id: str, from_stage: str, to_stage: str,
                           transitioned_at: str, reason: str, triggered_by: str) -> StageTransition:
        """记录阶段转换"""
        transition_id = f"TR_{hashlib.md5(f'{customer_id}_{transitioned_at}'.encode()).hexdigest()[:8].upper()}"
        transition = StageTransition(
            transition_id=transition_id,
            customer_id=customer_id,
            from_stage=from_stage,
            to_stage=to_stage,
            transitioned_at=transitioned_at,
            reason=reason,
            triggered_by=triggered_by,
        )

        conn = sqlite3.connect(self.DB_PATH)
        conn.execute(
            """INSERT INTO stage_transitions
               (transition_id, customer_id, from_stage, to_stage, transitioned_at, reason, triggered_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (transition_id, customer_id, from_stage, to_stage, transitioned_at, reason, triggered_by),
        )
        conn.commit()
        conn.close()

        return transition

    def _row_to_profile(self, row) -> CustomerProfile:
        """数据库行转 CustomerProfile"""
        return CustomerProfile(
            customer_id=row["customer_id"],
            company_name=row["company_name"],
            industry=row["industry"] or "",
            country=row["country"] or "",
            monthly_volume=row["monthly_volume"] or 0.0,
            contact_name=row["contact_name"] or "",
            contact_phone=row["contact_phone"] or "",
            contact_email=row["contact_email"] or "",
            current_stage=row["current_stage"] or CustomerStage.LEAD.value,
            stage_entered_at=row["stage_entered_at"] or "",
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
            assigned_sales=row["assigned_sales"] or "",
            tags=row["tags"] or "[]",
            notes=row["notes"] or "",
            risk_level=row["risk_level"] or "低",
        )

    def _calc_avg_stage_days(self, conn: sqlite3.Connection, stage_name: str) -> float:
        """计算某阶段的平均停留时长"""
        rows = conn.execute(
            """SELECT t1.customer_id, t1.transitioned_at as entered,
                      COALESCE(MIN(t2.transitioned_at), datetime('now')) as left
               FROM stage_transitions t1
               LEFT JOIN stage_transitions t2 ON t1.customer_id = t2.customer_id
                   AND t2.transitioned_at > t1.transitioned_at
               WHERE t1.to_stage = ?
               GROUP BY t1.customer_id, t1.transitioned_at""",
            (stage_name,),
        ).fetchall()

        if not rows:
            # 使用当前停留的客户计算
            rows = conn.execute(
                "SELECT stage_entered_at FROM customers WHERE current_stage = ?", (stage_name,)
            ).fetchall()
            if not rows:
                return 0.0
            total = sum(
                (datetime.now() - datetime.fromisoformat(r[0])).days
                for r in rows if r[0]
            )
            return round(total / len(rows), 1)

        total_days = 0
        count = 0
        for row in rows:
            entered = datetime.fromisoformat(row[1])
            left = datetime.fromisoformat(row[2]) if row[2] else datetime.now()
            total_days += (left - entered).days
            count += 1

        return round(total_days / count, 1) if count > 0 else 0.0

    def _calc_conversion_rate(self, conn: sqlite3.Connection, stage_name: str) -> float:
        """计算某阶段到下一阶段的转化率"""
        total_exits = conn.execute(
            "SELECT COUNT(*) FROM stage_transitions WHERE from_stage = ?",
            (stage_name,),
        ).fetchone()[0]

        if total_exits == 0:
            return 0.0

        # 找到下一阶段名称
        stage_enum = self._stage_to_enum(stage_name)
        stage_idx = STAGE_ORDER.index(stage_enum) if stage_enum in STAGE_ORDER else -1
        if stage_idx < 0 or stage_idx + 1 >= len(STAGE_ORDER):
            return 0.0

        next_stage = STAGE_ORDER[stage_idx + 1].value
        next_count = conn.execute(
            "SELECT COUNT(*) FROM stage_transitions WHERE from_stage = ? AND to_stage = ?",
            (stage_name, next_stage),
        ).fetchone()[0]

        return round(next_count / total_exits * 100, 1)

    def _calc_churn_rate(self, conn: sqlite3.Connection, stage_name: str) -> float:
        """计算某阶段的流失率"""
        total_exits = conn.execute(
            "SELECT COUNT(*) FROM stage_transitions WHERE from_stage = ?",
            (stage_name,),
        ).fetchone()[0]

        if total_exits == 0:
            return 0.0

        churn = conn.execute(
            "SELECT COUNT(*) FROM stage_transitions WHERE from_stage = ? AND to_stage = ?",
            (stage_name, CustomerStage.LOST.value),
        ).fetchone()[0]

        return round(churn / total_exits * 100, 1)

    def _count_overdue(self, conn: sqlite3.Connection, stage_name: str) -> int:
        """计算超期停留数量"""
        benchmark = STAGE_BENCHMARK_DAYS.get(self._stage_to_enum(stage_name), 7)
        cutoff = (datetime.now() - timedelta(days=benchmark)).isoformat()

        return conn.execute(
            "SELECT COUNT(*) FROM customers WHERE current_stage = ? AND stage_entered_at < ?",
            (stage_name, cutoff),
        ).fetchone()[0]


# ============================================================
# 全局单例
# ============================================================
_manager: Optional[CustomerStageManager] = None


def get_customer_stage_manager() -> CustomerStageManager:
    """获取全局客户阶段管理器实例"""
    global _manager
    if _manager is None:
        _manager = CustomerStageManager()
    return _manager


# ──────────────────────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mgr = CustomerStageManager()

    # 创建测试客户
    c1 = mgr.create_customer(
        company_name="深圳市测试贸易公司",
        industry="一般贸易",
        country="泰国",
        monthly_volume=20.0,
        contact_name="张三",
        assigned_sales="销售A",
        tags=["B2B", "高意向"],
    )
    print(f"创建客户: {c1.company_name} ({c1.customer_id})")

    # 阶段推进
    result = mgr.transition_stage(c1.customer_id, "初次接触", reason="客户回复了 outreach 邮件")
    print(f"阶段转换: {result['message']}")

    result = mgr.transition_stage(c1.customer_id, "需求确认", reason="电话沟通确认了需求")
    print(f"阶段转换: {result['message']}")

    # 查看历史
    history = mgr.get_stage_history(c1.customer_id)
    print(f"\n阶段历史 ({len(history)} 条):")
    for h in history:
        print(f"  {h.from_stage or '(创建)'} → {h.to_stage} @ {h.transitioned_at[:19]}")

    # 查看建议
    suggestion = mgr.get_next_action_suggestion(c1.customer_id)
    print(f"\n下一步建议: {suggestion['action']} — {suggestion['suggestion']}")

    # 漏斗统计
    funnel = mgr.get_funnel_stats()
    print(f"\n漏斗统计: {funnel}")
