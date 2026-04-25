"""
素材管理服务层 — 朋友圈素材上传系统的核心数据库与文件操作

当前阶段：产品设计阶段（仅设计人员上传工具，不涉及渠道商展示）
"""
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from config import (
    MATERIALS_DB_PATH,
    MATERIALS_DIR,
    MATERIALS_THUMB_MAX_WIDTH,
    MATERIALS_THUMB_QUALITY,
)

# ============================================================
# 1. 数据库初始化
# ============================================================

def _get_connection() -> sqlite3.Connection:
    """获取数据库连接（自动创建表）"""
    conn = sqlite3.connect(MATERIALS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate_materials_db(conn: sqlite3.Connection):
    """执行素材库 schema 迁移（添加新列等）"""
    # 检查并添加 lifecycle_state 列
    cols = conn.execute("PRAGMA table_info(materials)").fetchall()
    col_names = [c["name"] for c in cols]
    if "lifecycle_state" not in col_names:
        conn.execute("ALTER TABLE materials ADD COLUMN lifecycle_state TEXT DEFAULT 'draft'")
    if "copy_short" not in col_names:
        conn.execute("ALTER TABLE materials ADD COLUMN copy_short TEXT")


def init_materials_db():
    """初始化素材数据库表（幂等，可重复调用）"""
    os.makedirs(os.path.dirname(MATERIALS_DB_PATH), exist_ok=True)
    conn = _get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS materials (
                material_id   TEXT PRIMARY KEY,
                week_year     INTEGER NOT NULL,
                week_number   INTEGER NOT NULL,
                day_of_week   INTEGER NOT NULL,
                publish_date  TEXT NOT NULL,

                theme         TEXT NOT NULL,
                title         TEXT NOT NULL,
                copy_text     TEXT NOT NULL,
                copy_short    TEXT,

                poster_path   TEXT,
                poster_name   TEXT,
                thumbnail_path TEXT,
                file_size     INTEGER,
                image_width   INTEGER,
                image_height  INTEGER,

                status        TEXT DEFAULT 'draft',
                lifecycle_state TEXT DEFAULT 'draft',
                published_at  TEXT,

                created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_materials_week ON materials(week_year, week_number)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_materials_date ON materials(publish_date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_materials_status ON materials(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_materials_lifecycle ON materials(lifecycle_state)"
        )
        # Schema 迁移
        _migrate_materials_db(conn)
        conn.commit()
    finally:
        conn.close()


# ============================================================
# 2. 缩略图生成
# ============================================================

def generate_thumbnail(image_path: str, max_width: int = MATERIALS_THUMB_MAX_WIDTH) -> Optional[str]:
    """
    生成缩略图，保持宽高比，JPEG格式。
    返回缩略图路径，失败返回 None。
    """
    try:
        from PIL import Image

        img = Image.open(image_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        ratio = max_width / img.width
        if ratio < 1:
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # 缩略图路径: xxx_original.png → xxx_thumb.jpg
        base = os.path.splitext(image_path)[0]
        thumb_path = f"{base}_thumb.jpg"
        img.save(thumb_path, "JPEG", quality=MATERIALS_THUMB_QUALITY, optimize=True)
        return thumb_path
    except Exception:
        return None


# ============================================================
# 3. 素材 CRUD
# ============================================================

def save_material(
    material_id: str,
    week_year: int,
    week_number: int,
    day_of_week: int,
    publish_date: str,
    theme: str,
    title: str,
    copy_text: str,
    poster_path: Optional[str] = None,
    poster_name: Optional[str] = None,
    thumbnail_path: Optional[str] = None,
    file_size: Optional[int] = None,
    image_width: Optional[int] = None,
    image_height: Optional[int] = None,
    status: str = "draft",
    lifecycle_state: str = "draft",
) -> dict:
    """
    保存或更新素材。
    如果 material_id 已存在则更新，否则插入。
    返回 {"success": bool, "material_id": str, "error": str}
    """
    init_materials_db()
    conn = _get_connection()
    try:
        # 检查是否存在
        existing = conn.execute(
            "SELECT material_id FROM materials WHERE material_id = ?",
            (material_id,),
        ).fetchone()

        now = datetime.now().isoformat()

        if existing:
            conn.execute(
                """
                UPDATE materials SET
                    theme = ?, title = ?, copy_text = ?,
                    poster_path = ?, poster_name = ?, thumbnail_path = ?,
                    file_size = ?, image_width = ?, image_height = ?,
                    status = ?, lifecycle_state = ?, updated_at = ?
                WHERE material_id = ?
                """,
                (
                    theme, title, copy_text,
                    poster_path, poster_name, thumbnail_path,
                    file_size, image_width, image_height,
                    status, lifecycle_state, now,
                    material_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO materials (
                    material_id, week_year, week_number, day_of_week, publish_date,
                    theme, title, copy_text,
                    poster_path, poster_name, thumbnail_path,
                    file_size, image_width, image_height,
                    status, lifecycle_state, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    material_id, week_year, week_number, day_of_week, publish_date,
                    theme, title, copy_text,
                    poster_path, poster_name, thumbnail_path,
                    file_size, image_width, image_height,
                    status, lifecycle_state, now, now,
                ),
            )

        conn.commit()
        return {"success": True, "material_id": material_id, "error": ""}
    except Exception as e:
        return {"success": False, "material_id": material_id, "error": str(e)}
    finally:
        conn.close()


def get_material(material_id: str) -> Optional[dict]:
    """根据 ID 获取单条素材"""
    init_materials_db()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM materials WHERE material_id = ?",
            (material_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_materials_by_week(week_year: int, week_number: int) -> list[dict]:
    """获取指定周的所有素材（按 day_of_week 排序）"""
    init_materials_db()
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM materials
            WHERE week_year = ? AND week_number = ?
            ORDER BY day_of_week
            """,
            (week_year, week_number),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_materials(limit: int = 100, offset: int = 0) -> list[dict]:
    """列出所有素材（按更新时间倒序）"""
    init_materials_db()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM materials ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_material(material_id: str) -> dict:
    """删除素材（同时删除关联文件）"""
    init_materials_db()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT poster_path, thumbnail_path FROM materials WHERE material_id = ?",
            (material_id,),
        ).fetchone()

        if row:
            # 删除文件
            for path in (row["poster_path"], row["thumbnail_path"]):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

            conn.execute("DELETE FROM materials WHERE material_id = ?", (material_id,))
            conn.commit()
            return {"success": True, "error": ""}
        return {"success": False, "error": "素材不存在"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def publish_material(material_id: str) -> dict:
    """将素材状态改为 published"""
    init_materials_db()
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE materials SET status = 'published', published_at = ? WHERE material_id = ?",
            (datetime.now().isoformat(), material_id),
        )
        conn.commit()
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ============================================================
# 4. 工具函数
# ============================================================

def get_week_folder(week_year: int, week_number: int) -> str:
    """获取周文件夹路径，不存在则自动创建"""
    folder = os.path.join(MATERIALS_DIR, f"{week_year}-W{week_number:02d}")
    os.makedirs(folder, exist_ok=True)
    return folder


def generate_material_id(week_year: int, week_number: int, day_of_week: int) -> str:
    """生成素材 ID: 2026-W17-1"""
    return f"{week_year}-W{week_number:02d}-{day_of_week}"


def get_current_week() -> tuple[int, int]:
    """返回当前年份和周数"""
    now = datetime.now()
    iso = now.isocalendar()
    return iso.year, iso.week


def get_week_dates(week_year: int, week_number: int) -> list[str]:
    """
    获取指定周的周一到周五的日期字符串列表 ["2026-04-27", ...]
    """
    import datetime as dt

    # 找到该年的第一周周一
    jan4 = dt.date(week_year, 1, 4)
    week1_monday = jan4 - dt.timedelta(days=jan4.weekday())
    target_monday = week1_monday + dt.timedelta(weeks=week_number - 1)

    dates = []
    for i in range(5):
        d = target_monday + dt.timedelta(days=i)
        dates.append(d.strftime("%Y-%m-%d"))
    return dates


def get_week_display(week_year: int, week_number: int) -> str:
    """返回周的显示文本: 2026年 第17周"""
    return f"{week_year}年 第{week_number}周"


def get_day_label(day_of_week: int) -> str:
    """返回周几的中文标签"""
    labels = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五"}
    return labels.get(day_of_week, f"周{day_of_week}")


# ============================================================
# 5. 海报历史 CRUD
# ============================================================

def init_poster_history_db():
    """初始化海报历史表（幂等，可重复调用）"""
    os.makedirs(os.path.dirname(MATERIALS_DB_PATH), exist_ok=True)
    conn = _get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS poster_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt          TEXT NOT NULL,
                html_code       TEXT NOT NULL,
                png_path        TEXT,
                thumbnail_path  TEXT,
                user_id         TEXT NOT NULL DEFAULT 'default_user',
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_poster_user ON poster_history(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_poster_time ON poster_history(created_at)"
        )
        conn.commit()
    finally:
        conn.close()


def save_poster(
    prompt: str,
    html_code: str,
    png_bytes: bytes,
    user_id: str = "default_user",
) -> dict:
    """
    保存生成的海报到文件系统 + DB。
    返回 {"success": bool, "id": int, "error": str}
    """
    from config import ASSETS_DIR

    init_poster_history_db()
    try:
        save_dir = os.path.join(ASSETS_DIR, "posters", "generated", user_id)
        os.makedirs(save_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        png_path = os.path.join(save_dir, f"poster_{ts}.png")
        with open(png_path, "wb") as f:
            f.write(png_bytes)

        thumb_path = generate_thumbnail(png_path)

        conn = _get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO poster_history (prompt, html_code, png_path, thumbnail_path, user_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (prompt, html_code, png_path, thumb_path, user_id),
            )
            conn.commit()
            return {"success": True, "id": cursor.lastrowid, "error": ""}
        finally:
            conn.close()
    except Exception as e:
        return {"success": False, "id": 0, "error": str(e)}


def list_posters(
    user_id: str = "default_user",
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """分页查询海报历史（按创建时间倒序）"""
    init_poster_history_db()
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM poster_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_poster(poster_id: int) -> dict:
    """删除海报记录（同时删除关联文件）"""
    init_poster_history_db()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT png_path, thumbnail_path FROM poster_history WHERE id = ?",
            (poster_id,),
        ).fetchone()

        if row:
            for path in (row["png_path"], row["thumbnail_path"]):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            conn.execute("DELETE FROM poster_history WHERE id = ?", (poster_id,))
            conn.commit()
            return {"success": True, "error": ""}
        return {"success": False, "error": "海报不存在"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ============================================================
# 6. 竞品内容收藏 CRUD
# ============================================================

def init_competitor_bookmarks_db():
    """初始化竞品收藏表（幂等，可重复调用）"""
    os.makedirs(os.path.dirname(MATERIALS_DB_PATH), exist_ok=True)
    conn = _get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS competitor_bookmarks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                content     TEXT NOT NULL,
                source      TEXT DEFAULT '',
                keywords    TEXT DEFAULT '',
                user_id     TEXT NOT NULL DEFAULT 'default_user',
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_comp_user ON competitor_bookmarks(user_id)"
        )
        conn.commit()
    finally:
        conn.close()


def save_competitor_bookmark(
    content: str,
    source: str = "",
    keywords: str = "",
    user_id: str = "default_user",
) -> dict:
    """保存竞品内容收藏。返回 {"success": bool, "error": str}"""
    init_competitor_bookmarks_db()
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO competitor_bookmarks (content, source, keywords, user_id)
            VALUES (?, ?, ?, ?)
            """,
            (content, source, keywords, user_id),
        )
        conn.commit()
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def list_competitor_bookmarks(
    user_id: str = "default_user",
    limit: int = 50,
    offset: int = 0,
    search: str = "",
) -> list[dict]:
    """分页查询竞品收藏，支持关键词模糊搜索"""
    init_competitor_bookmarks_db()
    conn = _get_connection()
    try:
        if search:
            rows = conn.execute(
                """
                SELECT * FROM competitor_bookmarks
                WHERE user_id = ?
                  AND (content LIKE ? OR source LIKE ? OR keywords LIKE ?)
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, f"%{search}%", f"%{search}%", f"%{search}%", limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM competitor_bookmarks
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_competitor_bookmark(bookmark_id: int) -> dict:
    """删除竞品收藏记录"""
    init_competitor_bookmarks_db()
    conn = _get_connection()
    try:
        conn.execute(
            "DELETE FROM competitor_bookmarks WHERE id = ?",
            (bookmark_id,),
        )
        conn.commit()
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ============================================================
# 7. 内容生命周期 & 审批队列
# ============================================================

def update_lifecycle_state(material_id: str, new_state: str, triggered_by: str = "system") -> dict:
    """更新素材生命周期状态"""
    init_materials_db()
    conn = _get_connection()
    try:
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE materials SET lifecycle_state = ?, updated_at = ? WHERE material_id = ?",
            (new_state, now, material_id),
        )
        conn.commit()
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_pending_approvals(limit: int = 50) -> list[dict]:
    """获取待审批的内容列表（lifecycle_state = 'review'）"""
    init_materials_db()
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM materials
            WHERE lifecycle_state = 'review'
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def approve_material(material_id: str, approved_by: str = "system") -> dict:
    """审批通过：review → approved"""
    init_materials_db()
    conn = _get_connection()
    try:
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE materials SET lifecycle_state = 'approved', updated_at = ? WHERE material_id = ?",
            (now, material_id),
        )
        conn.commit()
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def reject_material(material_id: str, reason: str = "", rejected_by: str = "system") -> dict:
    """审批拒绝：review → draft（退回修改）"""
    init_materials_db()
    conn = _get_connection()
    try:
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE materials SET lifecycle_state = 'draft', updated_at = ? WHERE material_id = ?",
            (now, material_id),
        )
        conn.commit()
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def schedule_material(material_id: str, platform: str, scheduled_at: str) -> dict:
    """排期发布：approved → scheduled"""
    init_materials_db()
    conn = _get_connection()
    try:
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE materials SET lifecycle_state = 'scheduled', updated_at = ? WHERE material_id = ?",
            (now, material_id),
        )
        conn.commit()
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_materials_by_lifecycle_state(state: str, limit: int = 100) -> list[dict]:
    """按生命周期状态查询素材"""
    init_materials_db()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM materials WHERE lifecycle_state = ? ORDER BY updated_at DESC LIMIT ?",
            (state, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# 8. 内容发布计划（content_schedule）
# ============================================================

def init_content_schedule_db():
    """初始化内容发布计划表（幂等）"""
    os.makedirs(os.path.dirname(MATERIALS_DB_PATH), exist_ok=True)
    conn = _get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS content_schedule (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id    TEXT NOT NULL,
                platform       TEXT NOT NULL,
                scheduled_at   TEXT NOT NULL,
                status         TEXT DEFAULT 'pending',
                published_at   TEXT,
                created_at     TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cs_material ON content_schedule(material_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cs_status ON content_schedule(status)"
        )
        conn.commit()
    finally:
        conn.close()


def create_content_schedule(material_id: str, platform: str, scheduled_at: str) -> dict:
    """创建内容发布计划"""
    init_content_schedule_db()
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO content_schedule (material_id, platform, scheduled_at, status)
            VALUES (?, ?, ?, ?)
            """,
            (material_id, platform, scheduled_at, "pending"),
        )
        conn.commit()
        return {"success": True, "id": cursor.lastrowid, "error": ""}
    except Exception as e:
        return {"success": False, "id": 0, "error": str(e)}
    finally:
        conn.close()


def update_schedule_status(schedule_id: int, status: str, published_at: str = "") -> dict:
    """更新发布计划状态"""
    init_content_schedule_db()
    conn = _get_connection()
    try:
        if published_at:
            conn.execute(
                "UPDATE content_schedule SET status = ?, published_at = ? WHERE id = ?",
                (status, published_at, schedule_id),
            )
        else:
            conn.execute(
                "UPDATE content_schedule SET status = ? WHERE id = ?",
                (status, schedule_id),
            )
        conn.commit()
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_pending_schedules(limit: int = 100) -> list[dict]:
    """获取待发布的计划列表（已到发布时间）"""
    init_content_schedule_db()
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM content_schedule
            WHERE status = 'pending' AND scheduled_at <= ?
            ORDER BY scheduled_at
            LIMIT ?
            """,
            (datetime.now().isoformat(), limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_schedules_by_material(material_id: str) -> list[dict]:
    """获取某素材的所有发布计划"""
    init_content_schedule_db()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM content_schedule WHERE material_id = ? ORDER BY scheduled_at",
            (material_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# 9. 内容性能追踪（content_performance）— Week 5
# ============================================================

def init_content_performance_db():
    """初始化内容性能表（幂等）"""
    os.makedirs(os.path.dirname(MATERIALS_DB_PATH), exist_ok=True)
    conn = _get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS content_performance (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id    TEXT NOT NULL,
                platform       TEXT NOT NULL,
                impressions    INTEGER DEFAULT 0,
                engagements    INTEGER DEFAULT 0,
                clicks         INTEGER DEFAULT 0,
                conversions    INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                click_rate     REAL DEFAULT 0.0,
                conversion_rate REAL DEFAULT 0.0,
                recorded_at    TEXT NOT NULL,
                metadata       TEXT,
                created_at     TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cp_material ON content_performance(material_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cp_platform ON content_performance(platform)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cp_recorded ON content_performance(recorded_at)"
        )
        conn.commit()
    finally:
        conn.close()


def save_content_performance(
    material_id: str,
    platform: str,
    impressions: int,
    engagements: int,
    clicks: int = 0,
    conversions: int = 0,
    recorded_at: str = "",
    metadata: dict = None,
) -> dict:
    """
    保存内容性能数据。

    Args:
        material_id: 素材 ID
        platform: 平台（wechat_moments, xiaohongshu, weibo 等）
        impressions: 曝光量
        engagements: 互动数（点赞+评论+转发）
        clicks: 点击数
        conversions: 转化数
        recorded_at: 记录时间（ISO 格式）
        metadata: 额外元数据（JSON）

    Returns:
        {"success": bool, "id": int, "error": str}
    """
    init_content_performance_db()
    conn = _get_connection()
    try:
        if not recorded_at:
            recorded_at = datetime.now().isoformat()

        # 计算各项比率
        engagement_rate = (engagements / impressions * 100) if impressions > 0 else 0.0
        click_rate = (clicks / impressions * 100) if impressions > 0 else 0.0
        conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0.0

        import json
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else "{}"

        cursor = conn.execute(
            """
            INSERT INTO content_performance (
                material_id, platform, impressions, engagements, clicks, conversions,
                engagement_rate, click_rate, conversion_rate, recorded_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                material_id, platform, impressions, engagements, clicks, conversions,
                engagement_rate, click_rate, conversion_rate, recorded_at, metadata_json
            ),
        )
        conn.commit()
        return {"success": True, "id": cursor.lastrowid, "error": ""}
    except Exception as e:
        return {"success": False, "id": 0, "error": str(e)}
    finally:
        conn.close()


def get_content_performance(material_id: str, platform: str = "") -> list[dict]:
    """
    获取指定素材的性能数据。

    Args:
        material_id: 素材 ID
        platform: 平台（可选，不指定则返回所有平台）

    Returns:
        性能数据列表
    """
    init_content_performance_db()
    conn = _get_connection()
    try:
        if platform:
            rows = conn.execute(
                """
                SELECT * FROM content_performance
                WHERE material_id = ? AND platform = ?
                ORDER BY recorded_at DESC
                """,
                (material_id, platform),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM content_performance
                WHERE material_id = ?
                ORDER BY recorded_at DESC
                """,
                (material_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_performance_by_platform(
    platform: str, days: int = 30, limit: int = 100
) -> list[dict]:
    """
    获取指定平台最近 N 天的性能数据。

    Args:
        platform: 平台
        days: 最近多少天
        limit: 最多返回多少条

    Returns:
        性能数据列表
    """
    init_content_performance_db()
    conn = _get_connection()
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """
            SELECT * FROM content_performance
            WHERE platform = ? AND recorded_at >= ?
            ORDER BY recorded_at DESC
            LIMIT ?
            """,
            (platform, cutoff_date, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_performance_summary(
    material_id: str, platform: str = ""
) -> dict:
    """
    获取性能摘要（聚合统计）。

    Args:
        material_id: 素材 ID
        platform: 平台（可选）

    Returns:
        摘要信息
    """
    init_content_performance_db()
    conn = _get_connection()
    try:
        if platform:
            rows = conn.execute(
                """
                SELECT
                    AVG(engagement_rate) as avg_engagement_rate,
                    MAX(engagement_rate) as max_engagement_rate,
                    MIN(engagement_rate) as min_engagement_rate,
                    AVG(click_rate) as avg_click_rate,
                    AVG(conversion_rate) as avg_conversion_rate,
                    SUM(impressions) as total_impressions,
                    SUM(engagements) as total_engagements,
                    COUNT(*) as record_count
                FROM content_performance
                WHERE material_id = ? AND platform = ?
                """,
                (material_id, platform),
            ).fetchone()
        else:
            rows = conn.execute(
                """
                SELECT
                    AVG(engagement_rate) as avg_engagement_rate,
                    MAX(engagement_rate) as max_engagement_rate,
                    MIN(engagement_rate) as min_engagement_rate,
                    AVG(click_rate) as avg_click_rate,
                    AVG(conversion_rate) as avg_conversion_rate,
                    SUM(impressions) as total_impressions,
                    SUM(engagements) as total_engagements,
                    COUNT(*) as record_count
                FROM content_performance
                WHERE material_id = ?
                """,
                (material_id,),
            ).fetchone()

        if rows and rows[0] is not None:
            return dict(rows)
        return {}
    finally:
        conn.close()


def get_top_performing_materials(
    platform: str = "", days: int = 30, limit: int = 10, by: str = "engagement_rate"
) -> list[dict]:
    """
    获取表现最好的素材。

    Args:
        platform: 平台（可选）
        days: 最近多少天
        limit: 返回数量
        by: 排序指标

    Returns:
        素材列表，包含性能数据
    """
    init_content_performance_db()
    conn = _get_connection()
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        if by not in ["engagement_rate", "click_rate", "conversion_rate", "engagements"]:
            by = "engagement_rate"

        if platform:
            query = f"""
                SELECT material_id, platform, AVG({by}) as avg_metric,
                       MAX(engagement_rate) as max_engagement_rate,
                       SUM(impressions) as total_impressions
                FROM content_performance
                WHERE platform = ? AND recorded_at >= ?
                GROUP BY material_id
                ORDER BY avg_metric DESC
                LIMIT ?
            """
            rows = conn.execute(query, (platform, cutoff_date, limit)).fetchall()
        else:
            query = f"""
                SELECT material_id, platform, AVG({by}) as avg_metric,
                       MAX(engagement_rate) as max_engagement_rate,
                       SUM(impressions) as total_impressions
                FROM content_performance
                WHERE recorded_at >= ?
                GROUP BY material_id
                ORDER BY avg_metric DESC
                LIMIT ?
            """
            rows = conn.execute(query, (cutoff_date, limit)).fetchall()

        return [dict(r) for r in rows]
    finally:
        conn.close()
