"""
内容效果数据服务（Engagement Service）

负责：
- engagement 数据存储（impressions / engagements / clicks / conversions）
- 趋势分析（周度对比、内容类型分析）
- CSV 导入/导出

数据来源：目前为手动录入（Excel/CSV），后续可接入平台 API
"""
import csv
import io
import os
import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional

from config import DATA_DIR


def _get_db_path() -> str:
    return os.path.join(DATA_DIR, "engagement.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_engagement_db():
    """初始化 engagement 数据库"""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS engagement_data (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id     TEXT NOT NULL,
                platform        TEXT NOT NULL,        -- wechat_moments / wecom / douyin
                publish_date    TEXT NOT NULL,        -- YYYY-MM-DD
                week_year       INTEGER,
                week_number     INTEGER,
                impressions     INTEGER DEFAULT 0,     -- 阅读量/曝光
                engagements     INTEGER DEFAULT 0,     -- 点赞/评论/分享
                clicks          INTEGER DEFAULT 0,     -- 链接点击
                conversions     INTEGER DEFAULT 0,     -- 转化（咨询/注册）
                engagement_rate REAL DEFAULT 0.0,      -- 互动率 = engagements / impressions
                notes           TEXT DEFAULT '',
                created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at     TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(material_id, platform)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ed_date ON engagement_data(publish_date)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ed_week ON engagement_data(week_year, week_number)
        """)
        conn.commit()
    finally:
        conn.close()


def save_engagement(
    material_id: str,
    platform: str,
    publish_date: str,
    impressions: int = 0,
    engagements: int = 0,
    clicks: int = 0,
    conversions: int = 0,
    notes: str = "",
) -> dict:
    """保存/更新单条 engagement 数据"""
    init_engagement_db()
    d = date.fromisoformat(publish_date)
    week_year, week_number = d.isocalendar().year, d.isocalendar().week
    engagement_rate = (engagements / impressions * 100) if impressions > 0 else 0.0

    conn = _get_conn()
    try:
        cursor = conn.execute("""
            INSERT INTO engagement_data
              (material_id, platform, publish_date, week_year, week_number,
               impressions, engagements, clicks, conversions, engagement_rate, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(material_id, platform) DO UPDATE SET
              impressions=excluded.impressions,
              engagements=excluded.engagements,
              clicks=excluded.clicks,
              conversions=excluded.conversions,
              engagement_rate=excluded.engagement_rate,
              notes=excluded.notes,
              updated_at=excluded.updated_at
        """, (material_id, platform, publish_date, week_year, week_number,
              impressions, engagements, clicks, conversions, engagement_rate, notes,
              datetime.now().isoformat()))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid, "error": ""}
    except Exception as e:
        return {"success": False, "id": 0, "error": str(e)}
    finally:
        conn.close()


def get_engagement(material_id: str, platform: str = "wechat_moments") -> Optional[dict]:
    """获取单条 engagement 数据"""
    init_engagement_db()
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM engagement_data WHERE material_id = ? AND platform = ?",
            (material_id, platform),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_weekly_stats(year: int, week: int) -> dict:
    """获取指定周的数据统计"""
    init_engagement_db()
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT
                COUNT(*) as content_count,
                SUM(impressions) as total_impressions,
                SUM(engagements) as total_engagements,
                SUM(clicks) as total_clicks,
                SUM(conversions) as total_conversions,
                AVG(engagement_rate) as avg_engagement_rate
            FROM engagement_data
            WHERE week_year = ? AND week_number = ?
        """, (year, week)).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_all_data(limit: int = 100) -> list[dict]:
    """获取所有 engagement 数据"""
    init_engagement_db()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM engagement_data ORDER BY publish_date DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def import_from_csv(csv_path: str) -> dict:
    """
    从 CSV 文件导入 engagement 数据。

    CSV 格式要求：
    material_id, platform, publish_date, impressions, engagements, clicks, conversions, notes
    """
    init_engagement_db()
    imported = 0
    errors = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, 2):
            try:
                result = save_engagement(
                    material_id=row["material_id"].strip(),
                    platform=row.get("platform", "wechat_moments").strip(),
                    publish_date=row["publish_date"].strip(),
                    impressions=int(row.get("impressions", 0) or 0),
                    engagements=int(row.get("engagements", 0) or 0),
                    clicks=int(row.get("clicks", 0) or 0),
                    conversions=int(row.get("conversions", 0) or 0),
                    notes=row.get("notes", "").strip(),
                )
                if result["success"]:
                    imported += 1
                else:
                    errors.append(f"行{row_num}: {result['error']}")
            except Exception as e:
                errors.append(f"行{row_num}: {e}")

    return {"imported": imported, "errors": errors}


def export_to_csv(save_path: str) -> dict:
    """导出所有数据到 CSV"""
    data = get_all_data(limit=10000)
    if not data:
        return {"success": False, "error": "无数据可导出"}

    # 写入 CSV
    fieldnames = [
        "material_id", "platform", "publish_date",
        "impressions", "engagements", "clicks", "conversions",
        "engagement_rate", "notes",
    ]
    try:
        with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(data)
        return {"success": True, "count": len(data), "path": save_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_template_csv() -> str:
    """返回 CSV 模板内容（字符串）"""
    headers = [
        "material_id", "platform", "publish_date",
        "impressions", "engagements", "clicks", "conversions", "notes",
    ]
    sample = [
        "wf_abc123_0, wechat_moments, 2026-04-21, 120, 8, 3, 1, 朋友圈A",
        "wf_abc123_1, wechat_moments, 2026-04-22, 95, 6, 2, 0, 朋友圈B",
        "wf_abc123_2, wecom, 2026-04-21, 200, 15, 5, 2, 企微推送",
    ]
    lines = [",".join(headers)] + [",".join(sample)]
    return "\n".join(lines)


def get_content_performance_analysis(days: int = 30) -> dict:
    """
    分析近期内容表现，返回洞察。

    分析维度：
    - 按内容主题（theme）聚合的互动率
    - Top/Bottom 5 内容
    - 平台对比
    - 周度趋势
    """
    init_engagement_db()
    conn = _get_conn()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()

        # Top performers
        top = conn.execute("""
            SELECT e.*
            FROM engagement_data e
            WHERE e.publish_date >= ?
            ORDER BY e.engagement_rate DESC
            LIMIT 5
        """, (cutoff,)).fetchall()

        # Bottom performers
        bottom = conn.execute("""
            SELECT e.*
            FROM engagement_data e
            WHERE e.publish_date >= ? AND e.impressions > 0
            ORDER BY e.engagement_rate ASC
            LIMIT 5
        """, (cutoff,)).fetchall()

        # 平台对比
        platform_stats = conn.execute("""
            SELECT platform,
                   COUNT(*) as content_count,
                   SUM(impressions) as total_impressions,
                   SUM(engagements) as total_engagements,
                   AVG(engagement_rate) as avg_rate
            FROM engagement_data
            WHERE publish_date >= ?
            GROUP BY platform
        """, (cutoff,)).fetchall()

        # 周度趋势（最近4周）
        week_trend = conn.execute("""
            SELECT week_year, week_number,
                   SUM(impressions) as total_impressions,
                   AVG(engagement_rate) as avg_rate,
                   COUNT(*) as content_count
            FROM engagement_data
            WHERE publish_date >= ?
            GROUP BY week_year, week_number
            ORDER BY week_year, week_number DESC
            LIMIT 4
        """, (cutoff,)).fetchall()

        return {
            "top_performers": [dict(r) for r in top],
            "bottom_performers": [dict(r) for r in bottom],
            "platform_comparison": [dict(r) for r in platform_stats],
            "weekly_trend": [dict(r) for r in week_trend],
            "period_days": days,
        }
    finally:
        conn.close()
