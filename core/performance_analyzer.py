"""
性能分析器 — 分析内容性能数据，识别有效模式

核心功能：
1. Top-performer 识别：找出表现最好的内容
2. Underperformer 识别：找出表现不佳的内容
3. 趋势分析：识别 performance 变化趋势
4. 模式提取：提取高绩效内容共同特征
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from services.material_service import (
    get_materials_by_lifecycle_state,
    get_materials_by_week,
    list_materials,
)

logger = logging.getLogger(__name__)


@dataclass
class ContentPerformance:
    """内容性能数据"""
    material_id: str
    platform: str
    impressions: int
    engagements: int
    clicks: int = 0
    conversions: int = 0
    engagement_rate: float = 0.0
    click_rate: float = 0.0
    conversion_rate: float = 0.0
    recorded_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceInsight:
    """性能洞察"""
    insight_type: str  # "top_performer", "underperformer", "trend", "pattern"
    material_ids: List[str]
    description: str
    metrics: Dict[str, float]
    confidence: float  # 0-1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PerformanceAnalyzer:
    """
    内容性能分析器。

    分析内容 performance 数据，识别：
    - Top-performing 内容
    - Underperforming 内容
    - 性能趋势
    - 有效模式
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._performance_cache: Dict[str, ContentPerformance] = {}
        self._insights: List[PerformanceInsight] = []

    def load_performance_data(
        self, days: int = 30
    ) -> List[ContentPerformance]:
        """
        加载最近 N 天的性能数据。

        Args:
            days: 加载最近多少天的数据

        Returns:
            性能数据列表
        """
        # 从 materials.db 或专门的 performance 表加载
        # 这里先返回空列表，实际需要从数据库读取
        # TODO: 实现从数据库加载性能数据
        return []

    def calculate_rates(self, perf: ContentPerformance) -> ContentPerformance:
        """计算 engagement_rate, click_rate, conversion_rate"""
        if perf.impressions > 0:
            perf.engagement_rate = (perf.engagements / perf.impressions) * 100
            perf.click_rate = (perf.clicks / perf.impressions) * 100
        if perf.clicks > 0:
            perf.conversion_rate = (perf.conversions / perf.clicks) * 100
        return perf

    def identify_top_performers(
        self, performances: List[ContentPerformance], top_n: int = 5, by: str = "engagement_rate"
    ) -> List[ContentPerformance]:
        """
        识别表现最好的内容。

        Args:
            performances: 性能数据列表
            top_n: 返回前 N 个
            by: 排序指标（engagement_rate, click_rate, conversion_rate, engagements）

        Returns:
            Top performer 列表（按指标降序）
        """
        if by not in ["engagement_rate", "click_rate", "conversion_rate", "engagements"]:
            by = "engagement_rate"

        sorted_perf = sorted(
            performances, key=lambda p: getattr(p, by, 0), reverse=True
        )
        return sorted_perf[:top_n]

    def identify_underperformers(
        self, performances: List[ContentPerformance], bottom_n: int = 5, by: str = "engagement_rate", threshold: float = 2.0
    ) -> List[ContentPerformance]:
        """
        识别表现不佳的内容。

        Args:
            performances: 性能数据列表
            bottom_n: 返回后 N 个
            by: 排序指标
            threshold: 低于此阈值才认为是 underperformer

        Returns:
            Underperformer 列表（按指标升序）
        """
        if by not in ["engagement_rate", "click_rate", "conversion_rate", "engagements"]:
            by = "engagement_rate"

        # 先过滤出低于阈值的内容
        filtered = [p for p in performances if getattr(p, by, 100) < threshold]

        sorted_perf = sorted(filtered, key=lambda p: getattr(p, by, 0))
        return sorted_perf[:bottom_n]

    def analyze_trends(
        self, performances: List[ContentPerformance], period_days: int = 7
    ) -> Dict[str, Any]:
        """
        分析性能趋势。

        Args:
            performances: 性能数据列表
            period_days: 分析周期（天）

        Returns:
            趋势分析结果
        """
        if not performances:
            return {"trend": "stable", "change_rate": 0.0, "confidence": 0.0}

        # 按时间排序
        sorted_perf = sorted(
            performances, key=lambda p: p.recorded_at or ""
        )

        # 分为早期和晚期两组
        mid = len(sorted_perf) // 2
        early = sorted_perf[:mid]
        late = sorted_perf[mid:]

        if not early or not late:
            return {"trend": "stable", "change_rate": 0.0, "confidence": 0.0}

        # 计算平均 engagement_rate
        early_avg = sum(p.engagement_rate for p in early) / len(early)
        late_avg = sum(p.engagement_rate for p in late) / len(late)

        change_rate = (
            (late_avg - early_avg) / early_avg * 100 if early_avg > 0 else 0.0
        )

        # 判断趋势
        if change_rate > 10:
            trend = "improving"
        elif change_rate < -10:
            trend = "declining"
        else:
            trend = "stable"

        confidence = min(len(performances) / 20, 1.0)  # 样本越多置信度越高

        return {
            "trend": trend,
            "change_rate": change_rate,
            "early_avg": early_avg,
            "late_avg": late_avg,
            "confidence": confidence,
        }

    def extract_patterns(
        self, performers: List[ContentPerformance]
    ) -> Dict[str, Any]:
        """
        提取高绩效内容的共同模式。

        Args:
            performers: 高绩效内容列表

        Returns:
            模式提取结果
        """
        if not performers:
            return {"patterns": [], "confidence": 0.0}

        # 分析各维度
        platform_dist: Dict[str, int] = {}
        theme_dist: Dict[str, int] = {}
        day_dist: Dict[str, int] = {}

        for perf in performers:
            # 平台分布
            platform = perf.platform
            platform_dist[platform] = platform_dist.get(platform, 0) + 1

            # 从 metadata 提取其他信息
            if perf.metadata:
                theme = perf.metadata.get("theme", "unknown")
                theme_dist[theme] = theme_dist.get(theme, 0) + 1

                day = perf.metadata.get("day_of_week", "unknown")
                day_dist[day] = day_dist.get(day, 0) + 1

        # 提取最常见模式
        patterns = []

        # 平台模式
        if platform_dist:
            top_platform = max(platform_dist, key=platform_dist.get)
            patterns.append({
                "type": "platform",
                "value": top_platform,
                "frequency": platform_dist[top_platform] / len(performers),
                "description": f"高绩效内容多发布在 {top_platform}",
            })

        # 主题模式
        if theme_dist:
            top_theme = max(theme_dist, key=theme_dist.get)
            patterns.append({
                "type": "theme",
                "value": top_theme,
                "frequency": theme_dist[top_theme] / len(performers),
                "description": f"主题「{top_theme}」表现较好",
            })

        # 星期模式
        if day_dist:
            top_day = max(day_dist, key=day_dist.get)
            day_labels = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五"}
            day_label = day_labels.get(int(top_day), f"周{top_day}")
            patterns.append({
                "type": "day_of_week",
                "value": top_day,
                "frequency": day_dist[top_day] / len(performers),
                "description": f"{day_label}发布的内容表现较好",
            })

        confidence = min(len(performers) / 10, 1.0)

        return {
            "patterns": patterns,
            "total_analyzed": len(performers),
            "confidence": confidence,
        }

    def generate_insights(
        self, performances: List[ContentPerformance]
    ) -> List[PerformanceInsight]:
        """
        生成性能洞察。

        Args:
            performances: 性能数据列表

        Returns:
            洞察列表
        """
        insights = []

        # Top performer 洞察
        top_performers = self.identify_top_performers(performances)
        if top_performers:
            avg_rate = sum(p.engagement_rate for p in top_performers) / len(
                top_performers
            )
            insights.append(
                PerformanceInsight(
                    insight_type="top_performer",
                    material_ids=[p.material_id for p in top_performers],
                    description=f"发现 {len(top_performers)} 个高绩效内容，平均 engagement_rate {avg_rate:.2f}%",
                    metrics={
                        "avg_engagement_rate": avg_rate,
                        "top_material_id": top_performers[0].material_id,
                    },
                    confidence=0.8,
                )
            )

        # Underperformer 洞察
        underperformers = self.identify_underperformers(performances)
        if underperformers:
            avg_rate = sum(p.engagement_rate for p in underperformers) / len(
                underperformers
            )
            insights.append(
                PerformanceInsight(
                    insight_type="underperformer",
                    material_ids=[p.material_id for p in underperformers],
                    description=f"发现 {len(underperformers)} 个低绩效内容，平均 engagement_rate {avg_rate:.2f}%，建议优化",
                    metrics={"avg_engagement_rate": avg_rate},
                    confidence=0.8,
                )
            )

        # 趋势洞察
        trend_analysis = self.analyze_trends(performances)
        if trend_analysis["confidence"] > 0.5:
            trend_desc = {
                "improving": "内容性能呈上升趋势，继续保持",
                "declining": "内容性能呈下降趋势，需要调整策略",
                "stable": "内容性能保持稳定",
            }
            insights.append(
                PerformanceInsight(
                    insight_type="trend",
                    material_ids=[],
                    description=f"{trend_desc[trend_analysis['trend']]}，变化率 {trend_analysis['change_rate']:.1f}%",
                    metrics=trend_analysis,
                    confidence=trend_analysis["confidence"],
                )
            )

        # 模式洞察
        if top_performers:
            patterns = self.extract_patterns(top_performers)
            if patterns["patterns"]:
                pattern_desc = "；".join(
                    p["description"] for p in patterns["patterns"][:2]
                )
                insights.append(
                    PerformanceInsight(
                        insight_type="pattern",
                        material_ids=[p.material_id for p in top_performers],
                        description=f"高绩效内容模式：{pattern_desc}",
                        metrics={"patterns": patterns["patterns"]},
                        confidence=patterns["confidence"],
                    )
                )

        self._insights = insights
        return insights

    def get_learned_patterns(self) -> List[Dict[str, Any]]:
        """
        获取学习到的模式，用于注入到 ContentAgent 的 System Prompt。

        Returns:
            模式列表
        """
        patterns = []
        for insight in self._insights:
            if insight.insight_type == "pattern" and insight.metrics.get("patterns"):
                patterns.extend(insight.metrics["patterns"])

        return patterns

    def get_summary(self, performances: List[ContentPerformance]) -> Dict[str, Any]:
        """
        获取性能分析摘要。

        Args:
            performances: 性能数据列表

        Returns:
            摘要信息
        """
        if not performances:
            return {
                "total": 0,
                "avg_engagement_rate": 0,
                "max_engagement_rate": 0,
                "min_engagement_rate": 0,
            }

        engagement_rates = [p.engagement_rate for p in performances]

        return {
            "total": len(performances),
            "avg_engagement_rate": sum(engagement_rates) / len(engagement_rates),
            "max_engagement_rate": max(engagement_rates),
            "min_engagement_rate": min(engagement_rates),
            "platforms": list(set(p.platform for p in performances)),
        }


# 全局性能分析器实例
_global_analyzer: Optional[PerformanceAnalyzer] = None


def get_performance_analyzer() -> PerformanceAnalyzer:
    """获取全局性能分析器实例（单例）"""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = PerformanceAnalyzer()
    return _global_analyzer
