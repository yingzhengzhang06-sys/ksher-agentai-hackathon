"""
推荐引擎 — 基于记忆和 performance 推荐下一批内容选题

核心功能：
1. 基于历史 performance 推荐高潜力选题
2. 基于竞品动态推荐反制内容
3. 基于行业趋势推荐热点内容
4. 基于学习模式推荐风格和结构
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.learning_loop import get_learning_loop
from services.llm_client import LLMClient
from services.material_service import (
    get_materials_by_week,
    get_week_dates,
    list_materials,
)

logger = logging.getLogger(__name__)


@dataclass
class ContentRecommendation:
    """内容推荐"""
    recommendation_id: str
    content_type: str  # "trending", "competitor_response", "pattern_based", "industry_insight"
    title: str
    description: str
    suggested_platform: str
    suggested_day: int
    confidence: float  # 0-1
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class WeeklyContentPlan:
    """周内容计划"""
    week_year: int
    week_number: int
    recommendations: List[ContentRecommendation]
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ContentRecommender:
    """
    内容推荐引擎。

    基于以下维度推荐内容：
    1. 学习到的性能模式
    2. 竞品动态
    3. 行业趋势
    4. 历史内容空缺
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.learning_loop = get_learning_loop()
        self.llm_client = LLMClient()
        self._recommendations: List[ContentRecommendation] = []

    async def recommend_weekly_content(
        self, week_year: int, week_number: int
    ) -> WeeklyContentPlan:
        """
        为指定周推荐内容。

        Args:
            week_year: 年份
            week_number: 周数

        Returns:
            周内容计划
        """
        logger.info(f"[Recommender] 开始生成 {week_year}-W{week_number:02d} 内容推荐")

        # 1. 获取本周已有内容
        existing_materials = get_materials_by_week(week_year, week_number)
        existing_days = {m["day_of_week"] for m in existing_materials}

        # 2. 获取学习模式
        learned_patterns = self.learning_loop.get_current_patterns()

        # 3. 生成推荐
        recommendations = []

        # 基于模式推荐
        pattern_recs = self._recommend_based_on_patterns(existing_days)
        recommendations.extend(pattern_recs)

        # 基于竞品动态推荐
        competitor_recs = await self._recommend_competitor_response(existing_days)
        recommendations.extend(competitor_recs)

        # 基于行业趋势推荐
        trend_recs = await self._recommend_trending_content(existing_days)
        recommendations.extend(trend_recs)

        # 基于历史内容空缺推荐
        gap_recs = self._recommend_fill_gaps(week_year, week_number, existing_days)
        recommendations.extend(gap_recs)

        # 按置信度排序并去重
        recommendations = self._deduplicate_and_rank(recommendations)

        # 限制为周一到周五（5天）
        recommendations = recommendations[:5]

        # 分配星期
        recommendations = self._assign_days(recommendations, existing_days)

        plan = WeeklyContentPlan(
            week_year=week_year,
            week_number=week_number,
            recommendations=recommendations,
        )

        logger.info(
            f"[Recommender] 生成了 {len(recommendations)} 条内容推荐"
        )

        return plan

    def _recommend_based_on_patterns(
        self, existing_days: set
    ) -> List[ContentRecommendation]:
        """
        基于学习模式推荐内容。

        Args:
            existing_days: 已有内容的星期集合

        Returns:
            推荐列表
        """
        recommendations = []
        learned_patterns = self.learning_loop.get_current_patterns()

        # 简单实现：如果学习了平台模式，推荐在该平台发布
        if "微信朋友圈" in learned_patterns and 1 not in existing_days:
            recommendations.append(
                ContentRecommendation(
                    recommendation_id=self._generate_rec_id(),
                    content_type="pattern_based",
                    title="朋友圈高绩效内容",
                    description="基于历史数据，周一在朋友圈发布效果较好",
                    suggested_platform="wechat_moments",
                    suggested_day=1,
                    confidence=0.7,
                    reason="学习模式显示周一朋友圈表现较好",
                )
            )

        return recommendations

    async def _recommend_competitor_response(
        self, existing_days: set
    ) -> List[ContentRecommendation]:
        """
        基于竞品动态推荐反制内容。

        Args:
            existing_days: 已有内容的星期集合

        Returns:
            推荐列表
        """
        recommendations = []

        # TODO: 从竞品监控获取今日动态
        # 这里先返回空列表，实际实现需要从 competitor_bookmarks 或 social_crawler 获取
        # 如果竞品今日发布某主题，我们推荐类似主题的反制内容

        return recommendations

    async def _recommend_trending_content(
        self, existing_days: set
    ) -> List[ContentRecommendation]:
        """
        基于行业趋势推荐热点内容。

        Args:
            existing_days: 已有内容的星期集合

        Returns:
            推荐列表
        """
        recommendations = []

        # 使用 LLM 生成行业热点推荐
        prompt = """
作为跨境支付行业的营销专家，请推荐 2 个当前适合在社交媒体发布的内容选题。

要求：
1. 与跨境收款、东南亚市场、电商趋势相关
2. 具有价值性（知识分享）或共鸣性（痛点描述）
3. 每个选题包括：标题、内容方向、建议平台

请按以下格式输出：
```json
[
  {
    "title": "选题标题",
    "description": "内容方向描述",
    "platform": "wechat_moments|xiaohongshu|weibo",
    "day": 1-5,
    "reason": "推荐理由"
  }
]
```
"""

        try:
            response = await self.llm_client.achat(
                messages=[{"role": "user", "content": prompt}],
                model="kimi",
                temperature=0.7,
            )

            content = response.get("choices", [{}])[0].get("message", {}).get(
                "content", ""
            )
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                topics = json.loads(content[start:end])

                for topic in topics:
                    day = topic.get("day", 2)
                    if day not in existing_days:
                        recommendations.append(
                            ContentRecommendation(
                                recommendation_id=self._generate_rec_id(),
                                content_type="industry_insight",
                                title=topic.get("title", "行业热点内容"),
                                description=topic.get("description", ""),
                                suggested_platform=topic.get("platform", "wechat_moments"),
                                suggested_day=day,
                                confidence=0.6,
                                reason=topic.get("reason", "基于行业趋势"),
                            )
                        )
        except Exception as e:
            logger.warning(f"[Recommender] 趋势推荐失败: {e}")

        return recommendations

    def _recommend_fill_gaps(
        self, week_year: int, week_number: int, existing_days: set
    ) -> List[ContentRecommendation]:
        """
        基于历史内容空缺推荐补充内容。

        Args:
            week_year: 年份
            week_number: 周数
            existing_days: 已有内容的星期集合

        Returns:
            推荐列表
        """
        recommendations = []

        # 找出空缺的日子
        all_days = {1, 2, 3, 4, 5}
        missing_days = sorted(all_days - existing_days)

        # 为每个空缺日子推荐常规内容
        for day in missing_days[:3]:  # 最多补3条
            day_labels = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五"}
            recommendations.append(
                ContentRecommendation(
                    recommendation_id=self._generate_rec_id(),
                    content_type="pattern_based",
                    title=f"{day_labels[day]}常规内容",
                    description="补充周内容空缺，建议发布行业知识或产品价值内容",
                    suggested_platform="wechat_moments",
                    suggested_day=day,
                    confidence=0.5,
                    reason=f"{day_labels[day]}内容空缺，需要补充",
                )
            )

        return recommendations

    def _deduplicate_and_rank(
        self, recommendations: List[ContentRecommendation]
    ) -> List[ContentRecommendation]:
        """
        去重并按置信度排序。

        Args:
            recommendations: 原始推荐列表

        Returns:
            去重排序后的推荐列表
        """
        # 按置信度排序
        sorted_recs = sorted(
            recommendations, key=lambda r: r.confidence, reverse=True
        )

        # 去重（同一推荐类型只保留置信度最高的）
        seen_types = set()
        unique_recs = []
        for rec in sorted_recs:
            if rec.content_type not in seen_types:
                unique_recs.append(rec)
                seen_types.add(rec.content_type)

        return unique_recs

    def _assign_days(
        self, recommendations: List[ContentRecommendation], existing_days: set
    ) -> List[ContentRecommendation]:
        """
        为推荐分配星期（考虑已有内容）。

        Args:
            recommendations: 推荐列表
            existing_days: 已有内容的星期集合

        Returns:
            分配好星期的推荐列表
        """
        all_days = {1, 2, 3, 4, 5}
        available_days = sorted(all_days - existing_days)

        for i, rec in enumerate(recommendations):
            if i < len(available_days):
                rec.suggested_day = available_days[i]
            else:
                rec.suggested_day = 5  # 默认周五

        # 按星期排序
        recommendations.sort(key=lambda r: r.suggested_day)

        return recommendations

    def _generate_rec_id(self) -> str:
        """生成推荐 ID"""
        now = datetime.now()
        return f"rec_{now.strftime('%Y%m%d%H%M%S')}"

    def get_recommendations_summary(
        self, plan: WeeklyContentPlan
    ) -> Dict[str, Any]:
        """
        获取推荐摘要。

        Args:
            plan: 周内容计划

        Returns:
            摘要信息
        """
        type_counts = {}
        for rec in plan.recommendations:
            type_counts[rec.content_type] = type_counts.get(rec.content_type, 0) + 1

        return {
            "week": f"{plan.week_year}-W{plan.week_number:02d}",
            "total_recommendations": len(plan.recommendations),
            "type_distribution": type_counts,
            "avg_confidence": (
                sum(r.confidence for r in plan.recommendations) / len(plan.recommendations)
                if plan.recommendations
                else 0.0
            ),
            "platforms": list(set(r.suggested_platform for r in plan.recommendations)),
        }


# 全局推荐引擎实例
_global_recommender: Optional[ContentRecommender] = None


def get_content_recommender() -> ContentRecommender:
    """获取全局推荐引擎实例（单例）"""
    global _global_recommender
    if _global_recommender is None:
        _global_recommender = ContentRecommender()
    return _global_recommender
