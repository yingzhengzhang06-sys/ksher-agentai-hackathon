"""
作战包结果持久化服务

将 battle pack 保存到 data/battle_packs/YYYYMMDD/ 目录，
支持历史查询、统计分析和审计。

用法：
    from services.persistence import BattlePackPersistence
    bp = BattlePackPersistence()
    bp.save(context, battle_pack)
    history = bp.list_recent(days=7)
"""
import os
import sys
import json
import time
import glob
from typing import List, Optional, Dict
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BASE_DIR, DATA_DIR


class BattlePackPersistence:
    """
    作战包结果持久化。

    存储结构：
        data/battle_packs/20260418/
            20260418-101234_跨境通科技.json
            20260418-103045_另一公司.json
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.join(DATA_DIR, "battle_packs")
        os.makedirs(self.base_dir, exist_ok=True)

    def _today_dir(self) -> str:
        """返回今天的存储目录"""
        today = datetime.now().strftime("%Y%m%d")
        path = os.path.join(self.base_dir, today)
        os.makedirs(path, exist_ok=True)
        return path

    def _make_filename(self, context: dict) -> str:
        """基于客户上下文生成文件名"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        company = context.get("company", "未知公司")
        # 安全化文件名
        safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in company)[:30]
        return f"{timestamp}_{safe_name}.json"

    def save(self, context: dict, battle_pack: dict, metadata: Optional[dict] = None) -> str:
        """
        保存作战包。

        Args:
            context: 客户上下文
            battle_pack: 作战包结果
            metadata: 额外元数据（可选）

        Returns:
            str: 保存的文件路径
        """
        filepath = os.path.join(self._today_dir(), self._make_filename(context))

        record = {
            "saved_at": datetime.now().isoformat(),
            "context": context,
            "battle_pack": battle_pack,
        }
        if metadata:
            record["metadata"] = metadata

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        return filepath

    def list_by_date(self, date_str: str) -> List[dict]:
        """
        列出指定日期的所有作战包。

        Args:
            date_str: YYYYMMDD 格式日期
        """
        date_dir = os.path.join(self.base_dir, date_str)
        if not os.path.exists(date_dir):
            return []

        results = []
        for filepath in sorted(glob.glob(os.path.join(date_dir, "*.json"))):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    record = json.load(f)
                results.append({
                    "filename": os.path.basename(filepath),
                    "saved_at": record.get("saved_at", ""),
                    "company": record.get("context", {}).get("company", ""),
                    "industry": record.get("context", {}).get("industry", ""),
                    "battlefield": record.get("context", {}).get("battlefield", ""),
                    "filepath": filepath,
                })
            except Exception:
                continue

        return results

    def list_recent(self, days: int = 7) -> List[dict]:
        """
        列出最近 N 天的所有作战包。

        Args:
            days: 回溯天数（默认 7）
        """
        results = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")
            daily = self.list_by_date(date_str)
            for item in daily:
                item["date"] = date_str
            results.extend(daily)
        return results

    def load(self, filepath: str) -> Optional[dict]:
        """加载单个作战包"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def get_stats(self, days: int = 30) -> dict:
        """
        获取统计信息。

        Returns:
            dict: {
                "total_saved": int,
                "by_industry": dict,
                "by_battlefield": dict,
                "daily_counts": [{"date": "YYYYMMDD", "count": int}],
            }
        """
        all_records = self.list_recent(days)

        by_industry = {}
        by_battlefield = {}
        daily = {}

        for record in all_records:
            ind = record.get("industry", "unknown")
            bf = record.get("battlefield", "unknown")
            date = record.get("date", "unknown")

            by_industry[ind] = by_industry.get(ind, 0) + 1
            by_battlefield[bf] = by_battlefield.get(bf, 0) + 1
            daily[date] = daily.get(date, 0) + 1

        daily_list = [
            {"date": d, "count": c}
            for d, c in sorted(daily.items(), reverse=True)
        ]

        return {
            "total_saved": len(all_records),
            "by_industry": by_industry,
            "by_battlefield": by_battlefield,
            "daily_counts": daily_list,
        }


class FeedbackPersistence:
    """
    反馈数据持久化。

    存储结构：
        data/feedback/
            qa/         — 知识问答反馈
            battle_packs/ — 作战包反馈
            content/    — 内容工厂反馈
            visit_results/ — 拜访结果追踪
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.join(DATA_DIR, "feedback")
        os.makedirs(self.base_dir, exist_ok=True)

    def _ensure_subdir(self, module: str) -> str:
        path = os.path.join(self.base_dir, module)
        os.makedirs(path, exist_ok=True)
        return path

    def save(self, module: str, action: str, context: dict,
             output: dict, comment: str = "") -> str:
        """
        保存反馈。

        Args:
            module: 模块名 (qa / battle_packs / content / objection)
            action: 反馈动作 (helpful / needs_improvement)
            context: 用户输入上下文
            output: AI输出内容
            comment: 用户评论（可选）

        Returns:
            str: 保存的文件路径
        """
        subdir = self._ensure_subdir(module)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}_{action}.json"
        filepath = os.path.join(subdir, filename)

        record = {
            "saved_at": datetime.now().isoformat(),
            "module": module,
            "action": action,
            "context": context,
            "output": output,
            "comment": comment,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        return filepath

    def save_visit_result(self, battle_pack_id: str, result: str,
                          reason: str = "", notes: str = "",
                          helpful_agents: Optional[List[str]] = None) -> str:
        """
        保存拜访结果。

        Args:
            battle_pack_id: 关联的作战包ID/文件名
            result: 拜访结果 (signed / followup / lost)
            reason: 原因（下拉选项值）
            notes: 自由备注
            helpful_agents: 哪些Agent的输出在拜访中有用

        Returns:
            str: 保存的文件路径
        """
        subdir = self._ensure_subdir("visit_results")
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}_{result}.json"
        filepath = os.path.join(subdir, filename)

        record = {
            "saved_at": datetime.now().isoformat(),
            "battle_pack_id": battle_pack_id,
            "result": result,
            "reason": reason,
            "notes": notes,
            "helpful_agents": helpful_agents or [],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        return filepath

    def list_feedback(self, module: str, days: int = 30) -> List[dict]:
        """列出指定模块的反馈记录"""
        subdir = os.path.join(self.base_dir, module)
        if not os.path.exists(subdir):
            return []

        cutoff = datetime.now() - timedelta(days=days)
        results = []
        for filepath in sorted(glob.glob(os.path.join(subdir, "*.json")), reverse=True):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    record = json.load(f)
                saved_at = datetime.fromisoformat(record.get("saved_at", ""))
                if saved_at >= cutoff:
                    results.append(record)
            except Exception:
                continue
        return results

    def get_success_cases(self, industry: str = "", battlefield: str = "",
                          limit: int = 3) -> List[dict]:
        """
        获取成功案例（签约成功的作战包），用于飞轮注入。

        Args:
            industry: 筛选行业
            battlefield: 筛选战场类型
            limit: 最多返回条数

        Returns:
            list: 成功案例列表
        """
        visit_records = self.list_feedback("visit_results", days=90)
        signed = [r for r in visit_records if r.get("result") == "signed"]

        if not signed:
            return []

        # 尝试加载关联的作战包
        bp = BattlePackPersistence()
        cases = []
        for record in signed:
            bp_id = record.get("battle_pack_id", "")
            if not bp_id:
                continue
            # 查找对应的作战包文件
            for filepath in glob.glob(os.path.join(bp.base_dir, "**", f"*{bp_id}*"), recursive=True):
                pack_data = bp.load(filepath)
                if pack_data:
                    ctx = pack_data.get("context", {})
                    # 按条件筛选
                    if industry and ctx.get("industry") != industry:
                        continue
                    if battlefield and ctx.get("battlefield") != battlefield:
                        continue
                    cases.append({
                        "context": ctx,
                        "battle_pack": pack_data.get("battle_pack", {}),
                        "visit_result": record,
                    })
                    break
            if len(cases) >= limit:
                break
        return cases

    def get_feedback_stats(self, module: str = "", days: int = 30) -> dict:
        """获取反馈统计"""
        modules = [module] if module else ["qa", "battle_packs", "content", "objection"]
        stats = {"total": 0, "helpful": 0, "needs_improvement": 0, "by_module": {}}

        for mod in modules:
            records = self.list_feedback(mod, days)
            helpful = sum(1 for r in records if r.get("action") == "helpful")
            needs_imp = sum(1 for r in records if r.get("action") == "needs_improvement")
            stats["by_module"][mod] = {
                "total": len(records),
                "helpful": helpful,
                "needs_improvement": needs_imp,
            }
            stats["total"] += len(records)
            stats["helpful"] += helpful
            stats["needs_improvement"] += needs_imp

        return stats


if __name__ == "__main__":
    print("=" * 60)
    print("BattlePackPersistence 测试")
    print("=" * 60)

    bp = BattlePackPersistence()

    # 保存测试数据
    ctx = {
        "company": "跨境通科技",
        "industry": "b2c",
        "target_country": "thailand",
        "monthly_volume": 50000,
        "current_channel": "银行电汇",
        "battlefield": "increment",
    }
    pack = {
        "speech": {"elevator_pitch": "30秒话术..."},
        "cost": {"annual_saving": 34997.26},
        "proposal": {"solution": "方案..."},
        "objection": {"top_objections": []},
        "metadata": {"execution_time_ms": 100},
    }

    path = bp.save(ctx, pack)
    print(f"\n保存到: {path}")

    # 列出今天
    records = bp.list_by_date(datetime.now().strftime("%Y%m%d"))
    print(f"今天共 {len(records)} 条记录")
    for r in records:
        print(f"  [{r['saved_at']}] {r['company']} ({r['industry']}, {r['battlefield']})")

    # 统计
    stats = bp.get_stats(days=7)
    print(f"\n最近7天统计:")
    print(f"  总计: {stats['total_saved']}")
    print(f"  按行业: {stats['by_industry']}")
    print(f"  按战场: {stats['by_battlefield']}")
