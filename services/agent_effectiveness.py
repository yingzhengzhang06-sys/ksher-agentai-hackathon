"""
销售支持Agent效果追踪系统

记录每个Agent的使用情况、效果反馈，持续优化Agent推荐
"""

import os
import json
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 确保能导入 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR


class AgentEffectivenessTracker:
    """
    Agent效果追踪器

    功能：
    1. 记录每次Agent调用（输入、输出、耗时）
    2. 收集用户反馈（有帮助/无帮助评分）
    3. 统计分析各Agent效果
    4. 基于历史数据优化推荐
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(DATA_DIR, "agent_effectiveness.db")
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Agent调用记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                customer_id TEXT,
                session_id TEXT,
                input_summary TEXT,
                output_summary TEXT,
                duration_ms INTEGER,
                timestamp TEXT NOT NULL,
                context JSON
            )
        """)

        # 反馈记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id INTEGER,
                agent_name TEXT NOT NULL,
                customer_id TEXT,
                helpful_score INTEGER,  -- 1-5
                feedback_notes TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (call_id) REFERENCES agent_calls(id)
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_calls_agent
            ON agent_calls(agent_name, timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_feedback_agent
            ON agent_feedback(agent_name, timestamp)
        """)

        conn.commit()
        conn.close()

    # ==================== 记录调用 ====================

    def record_call(
        self,
        agent_name: str,
        input_data: Any,
        output_data: Any,
        duration_ms: int,
        customer_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> int:
        """记录Agent调用"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 输入输出摘要（限制长度）
        input_summary = str(input_data)[:500] if input_data else ""
        output_summary = str(output_data)[:500] if output_data else ""

        cursor.execute("""
            INSERT INTO agent_calls
            (agent_name, customer_id, session_id, input_summary, output_summary, duration_ms, timestamp, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_name,
            customer_id,
            session_id,
            input_summary,
            output_summary,
            duration_ms,
            datetime.now().isoformat(),
            json.dumps(context) if context else None,
        ))

        call_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return call_id

    # ==================== 记录反馈 ====================

    def record_feedback(
        self,
        agent_name: str,
        helpful_score: int,
        customer_id: Optional[str] = None,
        call_id: Optional[int] = None,
        feedback_notes: Optional[str] = None,
    ) -> bool:
        """记录用户反馈"""
        if helpful_score < 1 or helpful_score > 5:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO agent_feedback
            (call_id, agent_name, customer_id, helpful_score, feedback_notes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            call_id,
            agent_name,
            customer_id,
            helpful_score,
            feedback_notes,
            datetime.now().isoformat(),
        ))

        conn.commit()
        conn.close()

        return True

    # ==================== 统计分析 ====================

    def get_agent_stats(self, days: int = 30) -> Dict[str, dict]:
        """获取各Agent的统计数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        since = (datetime.now() - timedelta(days=days)).isoformat()

        # 获取调用次数和平均耗时
        cursor.execute("""
            SELECT
                agent_name,
                COUNT(*) as call_count,
                AVG(duration_ms) as avg_duration,
                COUNT(DISTINCT customer_id) as unique_customers
            FROM agent_calls
            WHERE timestamp >= ?
            GROUP BY agent_name
        """, (since,))

        call_stats = {
            row[0]: {
                "call_count": row[1],
                "avg_duration_ms": round(row[2], 0) if row[2] else 0,
                "unique_customers": row[3],
            }
            for row in cursor.fetchall()
        }

        # 获取反馈评分
        cursor.execute("""
            SELECT
                agent_name,
                AVG(helpful_score) as avg_score,
                COUNT(*) as feedback_count,
                SUM(CASE WHEN helpful_score >= 4 THEN 1 ELSE 0 END) as positive_count
            FROM agent_feedback
            WHERE timestamp >= ?
            GROUP BY agent_name
        """, (since,))

        feedback_stats = {
            row[0]: {
                "avg_score": round(row[1], 2) if row[1] else 0,
                "feedback_count": row[2],
                "positive_count": row[3],
                "satisfaction": round(row[3] / row[2] * 100, 1) if row[2] else 0,
            }
            for row in cursor.fetchall()
        }

        conn.close()

        # 合并统计
        result = {}
        all_agents = set(call_stats.keys()) | set(feedback_stats.keys())

        for agent in all_agents:
            result[agent] = {
                "call_count": call_stats.get(agent, {}).get("call_count", 0),
                "avg_duration_ms": call_stats.get(agent, {}).get("avg_duration_ms", 0),
                "unique_customers": call_stats.get(agent, {}).get("unique_customers", 0),
                "avg_score": feedback_stats.get(agent, {}).get("avg_score", 0),
                "feedback_count": feedback_stats.get(agent, {}).get("feedback_count", 0),
                "satisfaction": feedback_stats.get(agent, {}).get("satisfaction", 0),
            }

        return result

    def get_top_agents(self, days: int = 30, limit: int = 5) -> List[dict]:
        """获取效果最好的Agent排行"""
        stats = self.get_agent_stats(days)

        # 按综合得分排序
        agent_list = []
        for name, data in stats.items():
            # 综合得分 = 调用次数 * 0.3 + 满意度 * 0.7
            score = data["call_count"] * 0.3 + data["satisfaction"] * 0.7
            data["name"] = name
            data["score"] = round(score, 1)
            agent_list.append(data)

        agent_list.sort(key=lambda x: x["score"], reverse=True)
        return agent_list[:limit]

    def get_customer_journey(self, customer_id: str, limit: int = 10) -> List[dict]:
        """获取客户的Agent使用历程"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                ac.agent_name,
                ac.input_summary,
                ac.output_summary,
                ac.timestamp,
                af.helpful_score
            FROM agent_calls ac
            LEFT JOIN agent_feedback af ON af.call_id = ac.id
            WHERE ac.customer_id = ?
            ORDER BY ac.timestamp DESC
            LIMIT ?
        """, (customer_id, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "agent_name": row[0],
                "input_summary": row[1],
                "output_summary": row[2],
                "timestamp": row[3],
                "feedback_score": row[4],
            })

        conn.close()
        return results

    # ==================== 智能推荐 ====================

    def recommend_agents(self, context: dict) -> List[str]:
        """基于历史数据推荐Agent"""
        stats = self.get_agent_stats(days=30)
        industry = context.get("industry", "")
        stage = context.get("stage", "")

        recommendations = []

        # 基于满意度推荐
        high_satisfaction = [
            name for name, data in stats.items()
            if data.get("satisfaction", 0) >= 80
        ]
        recommendations.extend(high_satisfaction[:2])

        # 基于场景推荐
        scenario_agents = {
            "product": ["speech", "cost"],
            "compliance": ["speech", "proposal"],
            "competitor": ["objection", "speech"],
            "case": ["speech", "proposal"],
            "operation": ["knowledge"],
            "speech": ["speech", "objection"],
        }

        scenario = context.get("intent", "general")
        if scenario in scenario_agents:
            for agent in scenario_agents[scenario]:
                if agent not in recommendations:
                    recommendations.append(agent)

        # 确保至少有一些推荐
        if not recommendations:
            recommendations = ["speech", "cost", "proposal"]

        return recommendations[:3]


# 单例实例
_tracker_instance = None


def get_effectiveness_tracker() -> AgentEffectivenessTracker:
    """获取效果追踪器单例"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = AgentEffectivenessTracker()
    return _tracker_instance