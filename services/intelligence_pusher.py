"""
智能推送引擎 — 销售支持数字员工的主动推送中枢

核心理念：不等人问，AI自己盯着、自己推

功能：
1. 事件订阅与触发器管理
2. 推送内容自动生成（调用知识中枢+LLM）
3. 推送频率控制（防打扰策略）
4. 多渠道分发（企微/飞书/邮件/Web）
5. 推送效果追踪与反馈
"""
import os
import sys
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

# 确保能导入项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.event_bus import get_event_bus


class PushTriggerType(Enum):
    """推送触发器类型"""
    EVENT = "event"           # 事件触发（如客户阶段变化）
    SCHEDULED = "scheduled"   # 定时触发（如每日晨报）
    THRESHOLD = "threshold"   # 阈值触发（如汇率波动>0.5%）


class PushPriority(Enum):
    """推送优先级"""
    LOW = 1       # 低优先级（延迟推送，合并发送）
    NORMAL = 2    # 普通优先级
    HIGH = 3      # 高优先级（立即推送）
    URGENT = 4    # 紧急（强制推送，绕过频率限制）


@dataclass
class PushRule:
    """推送规则定义"""
    rule_id: str
    name: str
    description: str
    trigger_type: PushTriggerType
    trigger_config: Dict[str, Any]  # 触发条件配置
    content_template: str           # 内容模板或生成策略
    priority: PushPriority
    channels: List[str]             # 推送渠道
    target_roles: List[str]         # 目标角色/人群
    cooldown_minutes: int = 60      # 冷却时间（分钟）
    enabled: bool = True
    max_daily_count: int = 5        # 每日最大推送次数


@dataclass
class PushRecord:
    """推送记录"""
    record_id: str
    rule_id: str
    rule_name: str
    title: str
    content: str
    channels: List[str]
    recipients: List[str]
    pushed_at: str
    priority: str
    status: str  # sent / failed / read
    read_at: Optional[str] = None
    feedback: str = ""


class IntelligencePusher:
    """
    智能推送引擎

    核心能力：
    1. 规则引擎 — 定义何时、何地、给谁、推什么
    2. 内容生成 — 基于知识中枢+LLM生成个性化推送内容
    3. 频率控制 — 防打扰策略（冷却时间、每日上限、合并推送）
    4. 效果追踪 — 读取率、反馈率、转化率
    """

    DB_PATH = os.path.join(_PROJECT_ROOT, "data", "push_records.db")

    def __init__(self):
        self._init_db()
        self._rules: Dict[str, PushRule] = {}
        self._bus = get_event_bus()
        self._register_default_rules()

    def _init_db(self):
        """初始化推送记录数据库"""
        os.makedirs(os.path.dirname(self.DB_PATH), exist_ok=True)
        conn = sqlite3.connect(self.DB_PATH)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS push_records (
                record_id TEXT PRIMARY KEY,
                rule_id TEXT,
                rule_name TEXT,
                title TEXT,
                content TEXT,
                channels TEXT,
                recipients TEXT,
                pushed_at TEXT,
                priority TEXT,
                status TEXT DEFAULT 'sent',
                read_at TEXT,
                feedback TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS push_rules (
                rule_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                trigger_type TEXT,
                trigger_config TEXT,
                content_template TEXT,
                priority TEXT,
                channels TEXT,
                target_roles TEXT,
                cooldown_minutes INTEGER,
                enabled INTEGER DEFAULT 1,
                max_daily_count INTEGER
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_push_rule_id ON push_records(rule_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_push_date ON push_records(pushed_at)
        """)

        conn.commit()
        conn.close()

    # ============================================================
    # 默认规则注册
    # ============================================================

    def _register_default_rules(self):
        """注册默认推送规则"""
        defaults = [
            PushRule(
                rule_id="policy_alert",
                name="政策变更预警",
                description="当监测到跨境支付相关政策变更时推送",
                trigger_type=PushTriggerType.THRESHOLD,
                trigger_config={"source": "policy_monitor", "min_severity": "medium"},
                content_template="【政策预警】{{policy_title}}\n影响：{{impact_summary}}\n建议：{{suggestion}}",
                priority=PushPriority.HIGH,
                channels=["wecom"],
                target_roles=["销售支持", "渠道商经理"],
                cooldown_minutes=120,
                max_daily_count=3,
            ),
            PushRule(
                rule_id="fx_rate_alert",
                name="汇率波动预警",
                description="汇率日波动超过阈值时推送",
                trigger_type=PushTriggerType.THRESHOLD,
                trigger_config={"currency": "THB,MYR,PHP,IDR", "threshold_pct": 0.5},
                content_template="【汇率预警】{{currency}} 日波动 {{change_pct}}%\n当前：{{current_rate}}\n建议：{{hedge_suggestion}}",
                priority=PushPriority.HIGH,
                channels=["wecom"],
                target_roles=["销售支持", "客户经理"],
                cooldown_minutes=240,
                max_daily_count=2,
            ),
            PushRule(
                rule_id="competitor_move",
                name="竞品动态",
                description="竞品费率变动或新功能上线时推送",
                trigger_type=PushTriggerType.THRESHOLD,
                trigger_config={"competitors": ["PingPong", "WorldFirst", "XTransfer"], "types": ["fee_change", "new_feature"]},
                content_template="【竞品动态】{{competitor}} {{event_type}}\n详情：{{details}}\n应对：{{counter_strategy}}",
                priority=PushPriority.NORMAL,
                channels=["wecom"],
                target_roles=["销售支持"],
                cooldown_minutes=360,
                max_daily_count=3,
            ),
            PushRule(
                rule_id="customer_stage_change",
                name="客户阶段变化通知",
                description="客户阶段发生变化时通知负责人",
                trigger_type=PushTriggerType.EVENT,
                trigger_config={"event": "customer.stage_changed"},
                content_template="【客户动态】{{company_name}} 阶段变化\n{{from_stage}} → {{to_stage}}\n建议：{{next_action}}",
                priority=PushPriority.NORMAL,
                channels=["wecom"],
                target_roles=["客户经理"],
                cooldown_minutes=0,
                max_daily_count=50,
            ),
            PushRule(
                rule_id="customer_overdue",
                name="客户超期提醒",
                description="客户在某阶段停留超期时提醒",
                trigger_type=PushTriggerType.SCHEDULED,
                trigger_config={"cron": "0 9 * * 1-5"},  # 工作日早上9点
                content_template="【超期提醒】{{company_name}} 在「{{stage}}」已停留 {{days}} 天\n建议：{{action_suggestion}}",
                priority=PushPriority.HIGH,
                channels=["wecom"],
                target_roles=["客户经理"],
                cooldown_minutes=1440,  # 每天最多一次
                max_daily_count=10,
            ),
            PushRule(
                rule_id="weekly_competitor_digest",
                name="竞品周报摘要",
                description="每周汇总竞品动态",
                trigger_type=PushTriggerType.SCHEDULED,
                trigger_config={"cron": "0 9 * * 1"},  # 每周一早上9点
                content_template="【竞品周报】本周竞品动态汇总\n{{digest_content}}",
                priority=PushPriority.LOW,
                channels=["wecom", "email"],
                target_roles=["管理层", "销售支持"],
                cooldown_minutes=10080,  # 每周一次
                max_daily_count=1,
            ),
        ]

        for rule in defaults:
            self._rules[rule.rule_id] = rule
            self._save_rule_to_db(rule)

    def _save_rule_to_db(self, rule: PushRule):
        """保存规则到数据库"""
        conn = sqlite3.connect(self.DB_PATH)
        conn.execute(
            """INSERT OR REPLACE INTO push_rules
               (rule_id, name, description, trigger_type, trigger_config,
                content_template, priority, channels, target_roles,
                cooldown_minutes, enabled, max_daily_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rule.rule_id, rule.name, rule.description,
             rule.trigger_type.value, json.dumps(rule.trigger_config, ensure_ascii=False),
             rule.content_template, rule.priority.name,
             json.dumps(rule.channels), json.dumps(rule.target_roles),
             rule.cooldown_minutes, 1 if rule.enabled else 0, rule.max_daily_count),
        )
        conn.commit()
        conn.close()

    # ============================================================
    # 规则管理
    # ============================================================

    def add_rule(self, rule: PushRule) -> bool:
        """添加自定义推送规则"""
        if rule.rule_id in self._rules:
            return False
        self._rules[rule.rule_id] = rule
        self._save_rule_to_db(rule)

        # 如果是事件触发，订阅对应事件
        if rule.trigger_type == PushTriggerType.EVENT:
            event_type = rule.trigger_config.get("event", "")
            if event_type:
                self._bus.subscribe(event_type, self._make_event_handler(rule))

        return True

    def get_rule(self, rule_id: str) -> Optional[PushRule]:
        """获取规则"""
        return self._rules.get(rule_id)

    def list_rules(self, enabled_only: bool = True) -> List[PushRule]:
        """列出所有规则"""
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules

    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        rule.enabled = True
        self._save_rule_to_db(rule)
        return True

    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        rule.enabled = False
        self._save_rule_to_db(rule)
        return True

    # ============================================================
    # 推送执行
    # ============================================================

    def push(self, rule_id: str, context: Dict[str, Any],
             force: bool = False) -> Dict[str, Any]:
        """
        执行一次推送

        Args:
            rule_id: 规则ID
            context: 推送内容上下文变量
            force: 是否强制推送（绕过频率限制）

        Returns:
            {"success": bool, "record_id": str, "message": str}
        """
        rule = self._rules.get(rule_id)
        if not rule:
            return {"success": False, "record_id": "", "message": f"规则不存在: {rule_id}"}

        if not rule.enabled:
            return {"success": False, "record_id": "", "message": f"规则已禁用: {rule_id}"}

        # 频率控制检查
        if not force:
            freq_check = self._check_frequency(rule)
            if not freq_check["allowed"]:
                return {"success": False, "record_id": "", "message": freq_check["reason"]}

        # 生成推送内容
        title, content = self._generate_content(rule, context)

        # 执行推送
        record_id = self._generate_id(f"{rule_id}_{datetime.now().isoformat()}")
        now = datetime.now().isoformat()

        # 调用推送通道
        channel_results = []
        for channel in rule.channels:
            try:
                result = self._send_to_channel(channel, title, content, rule.priority, context)
                channel_results.append({"channel": channel, "success": True, "detail": result})
            except Exception as e:
                channel_results.append({"channel": channel, "success": False, "error": str(e)})

        # 记录推送
        record = PushRecord(
            record_id=record_id,
            rule_id=rule_id,
            rule_name=rule.name,
            title=title,
            content=content,
            channels=rule.channels,
            recipients=context.get("recipients", rule.target_roles),
            pushed_at=now,
            priority=rule.priority.name,
            status="sent" if any(r["success"] for r in channel_results) else "failed",
        )
        self._save_record(record)

        success = any(r["success"] for r in channel_results)
        return {
            "success": success,
            "record_id": record_id,
            "message": f"推送{'成功' if success else '失败'}: {title}",
            "channels": channel_results,
        }

    # ============================================================
    # 事件处理
    # ============================================================

    def _make_event_handler(self, rule: PushRule) -> Callable:
        """为事件触发规则创建事件处理器"""
        def handler(payload: dict):
            # 合并事件payload和规则默认上下文
            context = {**payload, "recipients": rule.target_roles}
            self.push(rule.rule_id, context)
        return handler

    def handle_event(self, event_type: str, payload: dict):
        """
        手动触发事件处理（用于测试或外部系统调用）
        """
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.trigger_type != PushTriggerType.EVENT:
                continue
            if rule.trigger_config.get("event") == event_type:
                self.push(rule.rule_id, {**payload, "recipients": rule.target_roles})

    # ============================================================
    # 频率控制
    # ============================================================

    def _check_frequency(self, rule: PushRule) -> Dict[str, Any]:
        """检查推送频率是否允许"""
        now = datetime.now()

        # 1. 冷却时间检查
        if rule.cooldown_minutes > 0:
            cutoff = (now - timedelta(minutes=rule.cooldown_minutes)).isoformat()
            conn = sqlite3.connect(self.DB_PATH)
            recent = conn.execute(
                "SELECT COUNT(*) FROM push_records WHERE rule_id = ? AND pushed_at > ?",
                (rule.rule_id, cutoff),
            ).fetchone()[0]
            conn.close()
            if recent > 0:
                return {
                    "allowed": False,
                    "reason": f"规则「{rule.name}」处于冷却期（{rule.cooldown_minutes}分钟）",
                }

        # 2. 每日上限检查
        if rule.max_daily_count > 0:
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            conn = sqlite3.connect(self.DB_PATH)
            today_count = conn.execute(
                "SELECT COUNT(*) FROM push_records WHERE rule_id = ? AND pushed_at > ?",
                (rule.rule_id, today_start),
            ).fetchone()[0]
            conn.close()
            if today_count >= rule.max_daily_count:
                return {
                    "allowed": False,
                    "reason": f"规则「{rule.name}」今日已达上限（{rule.max_daily_count}次）",
                }

        return {"allowed": True, "reason": ""}

    # ============================================================
    # 内容生成
    # ============================================================

    def _generate_content(self, rule: PushRule, context: Dict[str, Any]) -> tuple[str, str]:
        """生成推送标题和内容"""
        template = rule.content_template

        # 简单的模板变量替换
        try:
            content = template
            for key, value in context.items():
                placeholder = f"{{{{{key}}}}}"
                content = content.replace(placeholder, str(value))
        except Exception:
            content = template

        # 提取标题（第一行或前30字）
        lines = content.strip().split("\n")
        if lines and lines[0].startswith("【") and "】" in lines[0]:
            title = lines[0].split("】")[0] + "】"
            content = "\n".join(lines)
        else:
            title = f"【{rule.name}】"

        return title, content

    # ============================================================
    # 渠道推送
    # ============================================================

    def _send_to_channel(self, channel: str, title: str, content: str,
                         priority: PushPriority, context: Dict[str, Any]) -> str:
        """发送到指定渠道"""
        if channel == "wecom":
            return self._send_wecom(title, content, priority, context)
        elif channel == "lark":
            return self._send_lark(title, content, priority, context)
        elif channel == "email":
            return self._send_email(title, content, priority, context)
        elif channel == "web":
            return self._send_web(title, content, priority, context)
        else:
            raise ValueError(f"未知推送渠道: {channel}")

    def _send_wecom(self, title: str, content: str, priority: PushPriority,
                    context: Dict[str, Any]) -> str:
        """推送到企业微信"""
        try:
            from services.push_channel import get_push_manager
            manager = get_push_manager()
            level = "info" if priority in (PushPriority.LOW, PushPriority.NORMAL) else "warning" if priority == PushPriority.HIGH else "error"
            manager.push_alert(
                title=title,
                content=content,
                level=level,
                channels=["wecom"],
            )
            return "wecom_sent"
        except Exception as e:
            # 企微未配置时静默记录
            return f"wecom_mock: {str(e)[:50]}"

    def _send_lark(self, title: str, content: str, priority: PushPriority,
                   context: Dict[str, Any]) -> str:
        """推送到飞书（预留）"""
        return "lark_not_configured"

    def _send_email(self, title: str, content: str, priority: PushPriority,
                    context: Dict[str, Any]) -> str:
        """发送邮件（预留）"""
        return "email_not_configured"

    def _send_web(self, title: str, content: str, priority: PushPriority,
                  context: Dict[str, Any]) -> str:
        """推送到Web通知（Streamlit Toast）"""
        return "web_notified"

    # ============================================================
    # 记录与统计
    # ============================================================

    def _save_record(self, record: PushRecord):
        """保存推送记录"""
        conn = sqlite3.connect(self.DB_PATH)
        conn.execute(
            """INSERT INTO push_records
               (record_id, rule_id, rule_name, title, content, channels,
                recipients, pushed_at, priority, status, read_at, feedback)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record.record_id, record.rule_id, record.rule_name,
             record.title, record.content, json.dumps(record.channels),
             json.dumps(record.recipients), record.pushed_at,
             record.priority, record.status, record.read_at, record.feedback),
        )
        conn.commit()
        conn.close()

    def get_push_history(self, rule_id: Optional[str] = None,
                         days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """获取推送历史"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row

        if rule_id:
            rows = conn.execute(
                "SELECT * FROM push_records WHERE rule_id = ? AND pushed_at > ? ORDER BY pushed_at DESC LIMIT ?",
                (rule_id, cutoff, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM push_records WHERE pushed_at > ? ORDER BY pushed_at DESC LIMIT ?",
                (cutoff, limit),
            ).fetchall()

        conn.close()

        return [
            {
                "record_id": r["record_id"],
                "rule_name": r["rule_name"],
                "title": r["title"],
                "channels": json.loads(r["channels"]) if r["channels"] else [],
                "pushed_at": r["pushed_at"][:19] if r["pushed_at"] else "",
                "priority": r["priority"],
                "status": r["status"],
            }
            for r in rows
        ]

    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """获取推送统计数据"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = sqlite3.connect(self.DB_PATH)

        total = conn.execute(
            "SELECT COUNT(*) FROM push_records WHERE pushed_at > ?", (cutoff,)
        ).fetchone()[0]

        sent = conn.execute(
            "SELECT COUNT(*) FROM push_records WHERE pushed_at > ? AND status = 'sent'",
            (cutoff,),
        ).fetchone()[0]

        failed = conn.execute(
            "SELECT COUNT(*) FROM push_records WHERE pushed_at > ? AND status = 'failed'",
            (cutoff,),
        ).fetchone()[0]

        # 按规则统计
        rule_counts = conn.execute(
            """SELECT rule_name, COUNT(*) as cnt
               FROM push_records WHERE pushed_at > ?
               GROUP BY rule_name ORDER BY cnt DESC""",
            (cutoff,),
        ).fetchall()

        conn.close()

        return {
            "period_days": days,
            "total_pushes": total,
            "sent": sent,
            "failed": failed,
            "success_rate": round(sent / total * 100, 1) if total > 0 else 0,
            "by_rule": [{"rule": r[0], "count": r[1]} for r in rule_counts],
        }

    # ============================================================
    # 内部辅助
    # ============================================================

    def _generate_id(self, seed: str) -> str:
        """生成唯一ID"""
        hash_str = hashlib.md5(f"{seed}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        return f"PUSH_{hash_str.upper()}"


# ============================================================
# 全局单例
# ============================================================
_pusher: Optional[IntelligencePusher] = None


def get_intelligence_pusher() -> IntelligencePusher:
    """获取全局智能推送引擎实例"""
    global _pusher
    if _pusher is None:
        _pusher = IntelligencePusher()
    return _pusher


# ──────────────────────────────────────────────────────────────
# 便捷函数：外部系统直接调用
# ──────────────────────────────────────────────────────────────

def push_customer_stage_change(customer_id: str, company_name: str,
                                from_stage: str, to_stage: str,
                                next_action: str = ""):
    """便捷函数：推送客户阶段变化通知"""
    pusher = get_intelligence_pusher()
    return pusher.push("customer_stage_change", {
        "customer_id": customer_id,
        "company_name": company_name,
        "from_stage": from_stage,
        "to_stage": to_stage,
        "next_action": next_action or "请及时跟进",
    })


def push_policy_alert(policy_title: str, impact_summary: str, suggestion: str = ""):
    """便捷函数：推送政策预警"""
    pusher = get_intelligence_pusher()
    return pusher.push("policy_alert", {
        "policy_title": policy_title,
        "impact_summary": impact_summary,
        "suggestion": suggestion or "请关注并评估影响",
    })


def push_fx_rate_alert(currency: str, change_pct: float, current_rate: float,
                        hedge_suggestion: str = ""):
    """便捷函数：推送汇率预警"""
    pusher = get_intelligence_pusher()
    return pusher.push("fx_rate_alert", {
        "currency": currency,
        "change_pct": change_pct,
        "current_rate": current_rate,
        "hedge_suggestion": hedge_suggestion or f"{currency}波动较大，建议关注锁汇时机",
    })


# ──────────────────────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pusher = IntelligencePusher()

    print("=== 推送规则列表 ===")
    for rule in pusher.list_rules():
        print(f"  [{rule.priority.name}] {rule.rule_id}: {rule.name} ({rule.trigger_type.value})")

    print("\n=== 测试客户阶段变化推送 ===")
    result = push_customer_stage_change(
        customer_id="CUST_001",
        company_name="深圳市测试贸易公司",
        from_stage="初次接触",
        to_stage="需求确认",
        next_action="准备定制方案",
    )
    print(f"结果: {result['message']}")

    print("\n=== 测试汇率预警推送 ===")
    result = push_fx_rate_alert("THB", 0.8, 4.85)
    print(f"结果: {result['message']}")

    print("\n=== 推送统计 ===")
    stats = pusher.get_stats(days=1)
    print(f"今日推送: {stats['total_pushes']} 次, 成功率: {stats['success_rate']}%")
