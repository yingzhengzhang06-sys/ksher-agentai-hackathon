"""
上传数据持久化服务

存储结构：
    data/uploads/
        index.json                          # 总索引
        gpv/                                # 按数据类型分目录
            2026-04-W15_batch_a1b2c3.csv
        customer/
        chargeback/
        rate_comparison/
        finance/

用法：
    from services.upload_persistence import UploadPersistence
    up = UploadPersistence()
    batch_id = up.save_batch("gpv", df, "GPV报表.xlsx", "2026年4月")
    df = up.load_all("gpv")
    summary = up.get_summary()
"""

import os
import json
import uuid
from typing import List, Optional, Dict
from datetime import datetime

import pandas as pd

from config import DATA_DIR


SUPPORTED_TYPES = ["gpv", "customer", "chargeback", "rate_comparison", "finance",
                    "expense", "settlement", "budget"]


class UploadPersistence:
    """上传数据持久化 — CSV flat-file + JSON索引"""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.join(DATA_DIR, "uploads")
        os.makedirs(self.base_dir, exist_ok=True)
        for dtype in SUPPORTED_TYPES:
            os.makedirs(os.path.join(self.base_dir, dtype), exist_ok=True)
        self._index_path = os.path.join(self.base_dir, "index.json")

    # ---- 索引读写 ----

    def _read_index(self) -> dict:
        if not os.path.exists(self._index_path):
            return {"batches": [], "summary": {}}
        try:
            with open(self._index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"batches": [], "summary": {}}

    def _write_index(self, index: dict):
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _rebuild_summary(self, index: dict):
        """重建各数据类型汇总"""
        summary = {}
        for dtype in SUPPORTED_TYPES:
            type_batches = [b for b in index["batches"] if b["data_type"] == dtype]
            if type_batches:
                summary[dtype] = {
                    "batch_count": len(type_batches),
                    "total_rows": sum(b.get("row_count", 0) for b in type_batches),
                    "latest": max(b["uploaded_at"] for b in type_batches),
                    "earliest": min(b["uploaded_at"] for b in type_batches),
                }
            else:
                summary[dtype] = {"batch_count": 0, "total_rows": 0}
        index["summary"] = summary

    # ---- 导入 ----

    def save_batch(self, data_type: str, df: pd.DataFrame,
                   filename: str, period_label: str = "") -> str:
        """
        保存一个导入批次。

        Args:
            data_type: 数据类型（gpv/customer/chargeback/rate_comparison/finance）
            df: pandas DataFrame
            filename: 原始文件名
            period_label: 数据期间标注（如"2026年4月第3周"）

        Returns:
            str: batch_id
        """
        if data_type not in SUPPORTED_TYPES:
            raise ValueError(f"不支持的数据类型: {data_type}")

        batch_id = uuid.uuid4().hex[:8]
        now = datetime.now()
        week_num = now.isocalendar()[1]
        stored_name = f"{now.strftime('%Y-%m')}-W{week_num:02d}_batch_{batch_id}.csv"
        stored_path = os.path.join(data_type, stored_name)
        full_path = os.path.join(self.base_dir, stored_path)

        # 保存为CSV
        df.to_csv(full_path, index=False, encoding="utf-8-sig")

        # 更新索引
        index = self._read_index()
        batch_record = {
            "batch_id": batch_id,
            "data_type": data_type,
            "filename": filename,
            "stored_as": stored_path,
            "uploaded_at": now.isoformat(),
            "period_label": period_label or f"{now.strftime('%Y年%m月')}",
            "row_count": len(df),
            "col_count": len(df.columns),
            "columns": df.columns.tolist(),
        }
        index["batches"].append(batch_record)
        self._rebuild_summary(index)
        self._write_index(index)

        return batch_id

    # ---- 查询 ----

    def list_batches(self, data_type: Optional[str] = None) -> List[dict]:
        """列出导入批次（可按类型过滤），按时间倒序"""
        index = self._read_index()
        batches = index.get("batches", [])
        if data_type:
            batches = [b for b in batches if b["data_type"] == data_type]
        return sorted(batches, key=lambda x: x.get("uploaded_at", ""), reverse=True)

    def get_summary(self) -> dict:
        """获取各数据类型的汇总信息"""
        index = self._read_index()
        return index.get("summary", {})

    def load_batch(self, batch_id: str) -> Optional[pd.DataFrame]:
        """加载某个批次的数据"""
        index = self._read_index()
        for b in index.get("batches", []):
            if b["batch_id"] == batch_id:
                full_path = os.path.join(self.base_dir, b["stored_as"])
                if os.path.exists(full_path):
                    try:
                        return pd.read_csv(full_path, encoding="utf-8-sig")
                    except Exception:
                        return pd.read_csv(full_path, encoding="utf-8")
                return None
        return None

    def load_all(self, data_type: str) -> Optional[pd.DataFrame]:
        """加载某类型的所有批次，合并为一个DataFrame"""
        batches = self.list_batches(data_type)
        if not batches:
            return None

        dfs = []
        for b in batches:
            full_path = os.path.join(self.base_dir, b["stored_as"])
            if os.path.exists(full_path):
                try:
                    df = pd.read_csv(full_path, encoding="utf-8-sig")
                except Exception:
                    try:
                        df = pd.read_csv(full_path, encoding="utf-8")
                    except Exception:
                        continue
                df["_batch_id"] = b["batch_id"]
                df["_period"] = b.get("period_label", "")
                dfs.append(df)

        if not dfs:
            return None
        return pd.concat(dfs, ignore_index=True)

    def has_data(self, data_type: str) -> bool:
        """检查某类型是否有已导入数据"""
        summary = self.get_summary()
        type_info = summary.get(data_type, {})
        return type_info.get("batch_count", 0) > 0

    # ---- 管理 ----

    def delete_batch(self, batch_id: str) -> bool:
        """删除某个批次"""
        index = self._read_index()
        target = None
        for b in index.get("batches", []):
            if b["batch_id"] == batch_id:
                target = b
                break

        if not target:
            return False

        # 删除文件
        full_path = os.path.join(self.base_dir, target["stored_as"])
        if os.path.exists(full_path):
            os.remove(full_path)

        # 更新索引
        index["batches"] = [b for b in index["batches"] if b["batch_id"] != batch_id]
        self._rebuild_summary(index)
        self._write_index(index)

        return True
