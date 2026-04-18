"""
Agent 性能基准统计

记录各 Agent 平均耗时、缓存命中率、成功率。
数据保存到 data/performance_benchmark.json。

用法：
    from services.benchmark import BenchmarkCollector
    bc = BenchmarkCollector()
    bc.record("speech", latency_ms=5000, cached=False, success=True)
    print(bc.report())
"""
import os
import sys
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR


class BenchmarkCollector:
    """
    Agent 性能基准收集器。

    每次 Agent 调用后记录耗时和结果，
    支持实时统计和持久化保存。
    """

    DATA_FILE = os.path.join(DATA_DIR, "performance_benchmark.json")

    def __init__(self):
        self._records: List[dict] = []
        self._load_existing()

    def _load_existing(self):
        """加载已有基准数据"""
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._records = data.get("records", [])
            except Exception:
                self._records = []

    def _save(self):
        """保存到文件"""
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(self.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "updated_at": datetime.now().isoformat(),
                    "total_records": len(self._records),
                    "records": self._records[-1000:],  # 只保留最近1000条
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    def record(self, agent_name: str, latency_ms: int,
               cached: bool = False, success: bool = True,
               context_size: int = 0):
        """
        记录一次 Agent 调用。

        Args:
            agent_name: Agent 名称
            latency_ms: 耗时（毫秒）
            cached: 是否命中缓存
            success: 是否成功
            context_size: 上下文文本长度（可选）
        """
        self._records.append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "latency_ms": latency_ms,
            "cached": cached,
            "success": success,
            "context_size": context_size,
        })
        # 每20条保存一次
        if len(self._records) % 20 == 0:
            self._save()

    def report(self, recent_hours: int = 24) -> dict:
        """
        生成性能报告。

        Args:
            recent_hours: 分析最近 N 小时的数据（默认 24）

        Returns:
            dict: {
                "agents": {
                    "speech": {
                        "avg_latency_ms": float,
                        "min_latency_ms": int,
                        "max_latency_ms": int,
                        "calls": int,
                        "cache_hits": int,
                        "cache_hit_rate": float,
                        "success_rate": float,
                    },
                    ...
                },
                "overall": {
                    "total_calls": int,
                    "avg_latency_ms": float,
                    "overall_cache_hit_rate": float,
                    "overall_success_rate": float,
                }
            }
        """
        cutoff = datetime.now().timestamp() - recent_hours * 3600
        recent = [r for r in self._records
                  if datetime.fromisoformat(r["timestamp"]).timestamp() > cutoff]

        # 按 Agent 分组
        by_agent = defaultdict(list)
        for r in recent:
            by_agent[r["agent"]].append(r)

        agents_report = {}
        for name, records in sorted(by_agent.items()):
            latencies = [r["latency_ms"] for r in records]
            cached_count = sum(1 for r in records if r["cached"])
            success_count = sum(1 for r in records if r["success"])

            agents_report[name] = {
                "calls": len(records),
                "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
                "min_latency_ms": min(latencies) if latencies else 0,
                "max_latency_ms": max(latencies) if latencies else 0,
                "cache_hits": cached_count,
                "cache_hit_rate": round(cached_count / len(records) * 100, 1) if records else 0,
                "success_rate": round(success_count / len(records) * 100, 1) if records else 0,
            }

        total_calls = len(recent)
        all_latencies = [r["latency_ms"] for r in recent]
        total_cached = sum(1 for r in recent if r["cached"])
        total_success = sum(1 for r in recent if r["success"])

        return {
            "period_hours": recent_hours,
            "agents": agents_report,
            "overall": {
                "total_calls": total_calls,
                "avg_latency_ms": round(sum(all_latencies) / total_calls, 1) if total_calls else 0,
                "overall_cache_hit_rate": round(total_cached / total_calls * 100, 1) if total_calls else 0,
                "overall_success_rate": round(total_success / total_calls * 100, 1) if total_calls else 0,
            },
        }

    def report_text(self, recent_hours: int = 24) -> str:
        """生成人类可读的报告"""
        r = self.report(recent_hours)
        lines = [
            f"\n{'=' * 60}",
            f"  Agent 性能基准报告（最近 {recent_hours} 小时）",
            f"{'=' * 60}",
            f"\n  总体统计:",
            f"    总调用次数: {r['overall']['total_calls']}",
            f"    平均耗时: {r['overall']['avg_latency_ms']}ms",
            f"    缓存命中率: {r['overall']['overall_cache_hit_rate']}%",
            f"    成功率: {r['overall']['overall_success_rate']}%",
            f"\n  各 Agent 详情:",
        ]

        for name, stats in sorted(r["agents"].items()):
            lines.append(
                f"    {name:12} | "
                f"调用 {stats['calls']:3}次 | "
                f"平均 {stats['avg_latency_ms']:>6.1f}ms | "
                f"缓存 {stats['cache_hit_rate']:>5.1f}% | "
                f"成功 {stats['success_rate']:>5.1f}%"
            )

        lines.append(f"{'=' * 60}\n")
        return "\n".join(lines)

    def flush(self):
        """强制保存到文件"""
        self._save()


if __name__ == "__main__":
    print("=" * 60)
    print("BenchmarkCollector 测试")
    print("=" * 60)

    bc = BenchmarkCollector()

    # 模拟记录
    import random
    agents = ["speech", "cost", "proposal", "objection", "content", "knowledge", "design"]
    for _ in range(50):
        bc.record(
            agent_name=random.choice(agents),
            latency_ms=random.randint(1000, 80000),
            cached=random.random() < 0.3,
            success=random.random() < 0.95,
        )

    bc.flush()
    print(bc.report_text(recent_hours=24))
