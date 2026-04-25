"""
Engagement 数据采集器

Phase 1: 手动录入 + Excel 导入
Phase 2: API 接入（微信/企微/抖音开放平台）
"""
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Optional

from integrations.base import BaseIntegrator

logger = logging.getLogger(__name__)


class AnalyticsCollector(BaseIntegrator):
    """
    Engagement 数据采集器。

    Phase 1（当前）:
        - 手动录入单条数据
        - Excel/CSV 导入

    Phase 2（将来）:
        - API 定时采集
    """

    name = "analytics_collector"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._manual_data = []

    def fetch(self) -> Any:
        """
        Phase 1: 返回手动录入的数据

        Phase 2: 调用 API 获取数据
        """
        if not self._manual_data:
            logger.info("[AnalyticsCollector] 无手动数据，返回空列表")
        return self._manual_data

    def parse(self, raw_data: Any) -> list[dict]:
        """解析为统一格式"""
        # Phase 1: 手动数据已经是统一格式
        if isinstance(raw_data, list):
            return raw_data
        return []

    def add_manual_data(self, data: dict) -> bool:
        """
        手动录入单条数据。

        Args:
            data: {
                "material_id": str,
                "platform": str,
                "impressions": int,
                "engagements": int,
                "clicks": int,
                "shares": int,
                "collected_at": str,  # ISO datetime
            }

        Returns:
            是否成功
        """
        required = ["material_id", "platform", "impressions", "engagements"]
        if not all(k in data for k in required):
            logger.error(f"[AnalyticsCollector] 缺少必填字段: {required}")
            return False

        data.setdefault("clicks", 0)
        data.setdefault("shares", 0)
        data.setdefault("collected_at", datetime.now().isoformat())

        self._manual_data.append(data)
        logger.info(f"[AnalyticsCollector] 手动录入: {data['material_id']}")
        return True

    def import_from_excel(self, file_path: str) -> dict:
        """
        从 Excel 导入数据。

        Excel 列要求:
            - material_id: 素材ID
            - platform: 平台
            - impressions: 展现数
            - engagements: 互动数
            - clicks: 点击数（可选）
            - shares: 分享数（可选）
            - collected_at: 采集时间（可选）

        Returns:
            {"success": bool, "count": int, "error": str}
        """
        try:
            df = pd.read_excel(file_path)

            required_cols = ["material_id", "platform", "impressions", "engagements"]
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                return {
                    "success": False,
                    "count": 0,
                    "error": f"Excel 缺少列: {missing}",
                }

            count = 0
            for _, row in df.iterrows():
                data = {
                    "material_id": str(row["material_id"]),
                    "platform": str(row["platform"]),
                    "impressions": int(row["impressions"]),
                    "engagements": int(row["engagements"]),
                    "clicks": int(row.get("clicks", 0)),
                    "shares": int(row.get("shares", 0)),
                    "collected_at": datetime.now().isoformat(),
                }
                if self.add_manual_data(data):
                    count += 1

            logger.info(f"[AnalyticsCollector] Excel 导入: {count} 条")
            return {"success": True, "count": count, "error": ""}
        except Exception as e:
            logger.exception(f"[AnalyticsCollector] Excel 导入失败: {e}")
            return {"success": False, "count": 0, "error": str(e)}

    def get_engagement_rate(self, data: list[dict]) -> dict[str, float]:
        """计算 engagement_rate = engagements / impressions"""
        rates = {}
        for item in data:
            mid = item["material_id"]
            imp = item.get("impressions", 0)
            eng = item.get("engagements", 0)
            rates[mid] = (eng / imp * 100) if imp > 0 else 0.0
        return rates

    def get_top_performers(self, data: list[dict], top_n: int = 5) -> list[dict]:
        """获取表现最好的内容"""
        rates = self.get_engagement_rate(data)
        sorted_items = sorted(data, key=lambda x: rates.get(x["material_id"], 0), reverse=True)
        return sorted_items[:top_n]

    def clear_manual_data(self) -> None:
        """清空手动数据"""
        self._manual_data.clear()
