"""
客户CRM持久化服务

将客户画像保存到 data/customers/ 目录，
支持增删改查、搜索、关联作战包。

存储结构：
    data/customers/
        index.json              # 轻量索引
        001_深圳xxx科技.json
        002_跨境通科技.json

用法：
    from services.customer_persistence import CustomerPersistence
    cp = CustomerPersistence()
    cid = cp.save(customer_dict)
    customer = cp.load(cid)
    all_customers = cp.list_all()
"""

import os
import json
from typing import List, Optional, Dict
from datetime import datetime

from config import DATA_DIR


class CustomerPersistence:
    """客户CRM持久化 — JSON flat-file 存储"""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.join(DATA_DIR, "customers")
        os.makedirs(self.base_dir, exist_ok=True)
        self._index_path = os.path.join(self.base_dir, "index.json")
        if not os.path.exists(self._index_path):
            self._write_index([])

    # ── Index 读写 ──

    def _read_index(self) -> List[dict]:
        try:
            with open(self._index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write_index(self, index: List[dict]):
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _next_id(self) -> str:
        index = self._read_index()
        if not index:
            return "001"
        max_id = max(int(item.get("customer_id", "0")) for item in index)
        return str(max_id + 1).zfill(3)

    def _safe_name(self, company: str) -> str:
        return "".join(c if c.isalnum() or c in "_-" else "_" for c in company)[:30]

    def _filepath(self, customer_id: str, company: str) -> str:
        return os.path.join(
            self.base_dir,
            f"{customer_id}_{self._safe_name(company)}.json",
        )

    def _find_filepath(self, customer_id: str) -> Optional[str]:
        """根据 customer_id 在 index 中查找文件路径"""
        index = self._read_index()
        for item in index:
            if item.get("customer_id") == customer_id:
                fp = item.get("filepath", "")
                if fp and os.path.exists(fp):
                    return fp
        # fallback: 扫描目录
        import glob
        pattern = os.path.join(self.base_dir, f"{customer_id}_*.json")
        matches = glob.glob(pattern)
        return matches[0] if matches else None

    # ── CRUD ──

    def save(self, customer: dict) -> str:
        """
        保存客户。无 customer_id 则新建，有则更新。

        Returns:
            str: customer_id
        """
        now = datetime.now().isoformat()

        if customer.get("customer_id"):
            # 更新
            return self.update(customer["customer_id"], customer)

        # 新建
        customer_id = self._next_id()
        customer["customer_id"] = customer_id
        customer["created_at"] = now
        customer["updated_at"] = now
        customer.setdefault("battle_pack_paths", [])

        company = customer.get("company", "未命名")
        filepath = self._filepath(customer_id, company)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(customer, f, ensure_ascii=False, indent=2)

        # 更新索引
        index = self._read_index()
        index.append({
            "customer_id": customer_id,
            "company": company,
            "customer_stage": customer.get("customer_stage", "初次接触"),
            "contact_name": customer.get("contact_name", ""),
            "industry": customer.get("industry", ""),
            "updated_at": now,
            "filepath": filepath,
        })
        self._write_index(index)

        return customer_id

    def update(self, customer_id: str, updates: dict) -> str:
        """部分更新客户记录"""
        filepath = self._find_filepath(customer_id)
        if not filepath:
            # 找不到则当新建处理
            updates["customer_id"] = customer_id
            updates["created_at"] = datetime.now().isoformat()
            updates["updated_at"] = datetime.now().isoformat()
            updates.setdefault("battle_pack_paths", [])
            company = updates.get("company", "未命名")
            filepath = self._filepath(customer_id, company)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(updates, f, ensure_ascii=False, indent=2)
        else:
            existing = self.load(customer_id)
            if existing:
                existing.update(updates)
                existing["updated_at"] = datetime.now().isoformat()
                existing["customer_id"] = customer_id  # 确保 ID 不被覆盖
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)

        # 更新索引
        index = self._read_index()
        for item in index:
            if item.get("customer_id") == customer_id:
                item["company"] = updates.get("company", item.get("company", ""))
                item["customer_stage"] = updates.get("customer_stage", item.get("customer_stage", ""))
                item["contact_name"] = updates.get("contact_name", item.get("contact_name", ""))
                item["industry"] = updates.get("industry", item.get("industry", ""))
                item["updated_at"] = datetime.now().isoformat()
                break
        self._write_index(index)

        return customer_id

    def load(self, customer_id: str) -> Optional[dict]:
        """加载完整客户记录"""
        filepath = self._find_filepath(customer_id)
        if not filepath:
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def delete(self, customer_id: str) -> bool:
        """删除客户"""
        filepath = self._find_filepath(customer_id)
        if filepath and os.path.exists(filepath):
            os.remove(filepath)

        index = self._read_index()
        index = [item for item in index if item.get("customer_id") != customer_id]
        self._write_index(index)
        return True

    def list_all(self) -> List[dict]:
        """返回所有客户（轻量索引，按更新时间倒序）"""
        index = self._read_index()
        return sorted(index, key=lambda x: x.get("updated_at", ""), reverse=True)

    def search(self, keyword: str) -> List[dict]:
        """按公司名/联系人名模糊搜索"""
        keyword = keyword.lower()
        index = self._read_index()
        results = []
        for item in index:
            company = item.get("company", "").lower()
            contact = item.get("contact_name", "").lower()
            if keyword in company or keyword in contact:
                results.append(item)
        return sorted(results, key=lambda x: x.get("updated_at", ""), reverse=True)

    def link_battle_pack(self, customer_id: str, battle_pack_path: str):
        """将作战包路径关联到客户记录"""
        customer = self.load(customer_id)
        if not customer:
            return
        paths = customer.get("battle_pack_paths", [])
        # 存相对路径
        rel_path = battle_pack_path
        if rel_path not in paths:
            paths.append(rel_path)
        customer["battle_pack_paths"] = paths
        self.update(customer_id, customer)
