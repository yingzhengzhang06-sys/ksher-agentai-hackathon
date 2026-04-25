"""
客户互动日志持久化服务

存储结构：
    data/interactions/
        {customer_id}.json    # 每个客户一个文件，包含互动记录列表

用法：
    from services.interaction_persistence import InteractionPersistence
    ip = InteractionPersistence()
    iid = ip.add("001", {"type": "电话", "result": "推进", "summary": "..."})
    logs = ip.list_by_customer("001")
    recent = ip.list_recent(days=30)
"""

import os
import json
import uuid
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from config import DATA_DIR


class InteractionPersistence:
    """客户互动日志持久化 — JSON flat-file 存储"""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.join(DATA_DIR, "interactions")
        os.makedirs(self.base_dir, exist_ok=True)

    def _filepath(self, customer_id: str) -> str:
        return os.path.join(self.base_dir, f"{customer_id}.json")

    def _read(self, customer_id: str) -> List[dict]:
        fp = self._filepath(customer_id)
        if not os.path.exists(fp):
            return []
        try:
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write(self, customer_id: str, records: List[dict]):
        fp = self._filepath(customer_id)
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def add(self, customer_id: str, interaction: dict) -> str:
        """
        添加一条互动记录。

        Args:
            customer_id: 客户ID
            interaction: 互动数据，包含 type/result/summary 等字段

        Returns:
            str: interaction_id
        """
        interaction_id = uuid.uuid4().hex[:8]
        record = {
            "interaction_id": interaction_id,
            "customer_id": customer_id,
            "datetime": interaction.get("datetime", datetime.now().isoformat()),
            "type": interaction.get("type", "其他"),
            "result": interaction.get("result", "维持"),
            "summary": interaction.get("summary", ""),
            "next_followup": interaction.get("next_followup", ""),
            "operator": interaction.get("operator", "默认用户"),
        }

        records = self._read(customer_id)
        records.append(record)
        self._write(customer_id, records)

        return interaction_id

    def list_by_customer(self, customer_id: str) -> List[dict]:
        """获取某客户的所有互动记录（按时间倒序）"""
        records = self._read(customer_id)
        return sorted(records, key=lambda x: x.get("datetime", ""), reverse=True)

    def list_recent(self, days: int = 30) -> List[dict]:
        """获取所有客户的近期互动（按时间倒序）"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        all_records = []

        for filename in os.listdir(self.base_dir):
            if not filename.endswith(".json"):
                continue
            customer_id = filename.replace(".json", "")
            records = self._read(customer_id)
            for r in records:
                if r.get("datetime", "") >= cutoff:
                    all_records.append(r)

        return sorted(all_records, key=lambda x: x.get("datetime", ""), reverse=True)

    def get_stats(self, customer_id: str) -> dict:
        """获取某客户的互动统计"""
        records = self._read(customer_id)
        if not records:
            return {"total": 0, "last_interaction": None, "by_type": {}, "by_result": {}}

        by_type = {}
        by_result = {}
        for r in records:
            t = r.get("type", "其他")
            by_type[t] = by_type.get(t, 0) + 1
            res = r.get("result", "维持")
            by_result[res] = by_result.get(res, 0) + 1

        sorted_records = sorted(records, key=lambda x: x.get("datetime", ""), reverse=True)

        return {
            "total": len(records),
            "last_interaction": sorted_records[0] if sorted_records else None,
            "by_type": by_type,
            "by_result": by_result,
        }

    def count_recent(self, customer_id: str, days: int = 30) -> int:
        """统计某客户近N天的互动次数"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        records = self._read(customer_id)
        return sum(1 for r in records if r.get("datetime", "") >= cutoff)
