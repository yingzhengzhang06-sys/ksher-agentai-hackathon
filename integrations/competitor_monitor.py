"""
竞品监控集成器 — 定时抓取竞品社交媒体动态

支持平台：小红书 / 微博 / 抖音（通过 social_crawler 封装）
"""
import logging
from typing import Any

from integrations.base import BaseIntegrator
from services.social_crawler import search_sync, search_all_sync, is_available

logger = logging.getLogger(__name__)


class CompetitorMonitor(BaseIntegrator):
    """
    竞品监控器。

    配置示例:
        {
            "platforms": ["xiaohongshu", "weibo"],
            "competitors": ["PingPong", "万里汇", "XTransfer"],
            "limit_per_platform": 10,
            "auto_save": True  # 自动保存到竞品收藏
        }
    """

    name = "competitor_monitor"

    def __init__(self, config: dict = None):
        super().__init__(config)

    def fetch(self) -> dict:
        """抓取竞品动态，返回按平台分组的数据"""
        if not is_available():
            logger.warning("[CompetitorMonitor] 爬虫不可用，返回空数据")
            return {}

        platforms = self.config.get("platforms", ["xiaohongshu", "weibo"])
        competitors = self.config.get("competitors", ["PingPong", "万里汇", "XTransfer"])
        limit = self.config.get("limit_per_platform", 10)

        results = {}
        for platform in platforms:
            platform_data = []
            for comp in competitors:
                try:
                    posts = search_sync(platform, comp, limit)
                    platform_data.extend(posts)
                    logger.debug(f"[CompetitorMonitor] {platform}/{comp}: {len(posts)} 条")
                except Exception as e:
                    logger.warning(f"[CompetitorMonitor] 爬取失败 {platform}/{comp}: {e}")
            results[platform] = platform_data

        return results

    def parse(self, raw_data: dict) -> list[dict]:
        """解析爬取结果为统一格式"""
        parsed = []
        for platform, posts in raw_data.items():
            for post in posts:
                parsed.append({
                    "platform": platform,
                    "competitor": post.author if hasattr(post, 'author') else "",
                    "content": post.content if hasattr(post, 'content') else "",
                    "url": post.url if hasattr(post, 'url') else "",
                    "publish_date": post.publish_date if hasattr(post, 'publish_date') else "",
                    "likes": post.likes if hasattr(post, 'likes') else 0,
                    "comments": post.comments if hasattr(post, 'comments') else 0,
                    "shares": post.shares if hasattr(post, 'shares') else 0,
                    "raw": post,  # 保留原始数据
                })

        return parsed

    def run(self) -> dict:
        """执行监控并可选自动保存"""
        result = super().run()

        if result["success"] and self.config.get("auto_save", False):
            self._auto_save(result["data"])

        return result

    def _auto_save(self, data: list[dict]) -> None:
        """自动保存到竞品收藏"""
        count = 0
        for item in data:
            try:
                from services.material_service import save_competitor_bookmark
                keywords = f"{item['competitor']}, {item['platform']}"
                save_competitor_bookmark(
                    content=item["content"],
                    source=item["url"],
                    keywords=keywords,
                )
                count += 1
            except Exception as e:
                logger.warning(f"[CompetitorMonitor] 保存失败: {e}")

        if count > 0:
            logger.info(f"[CompetitorMonitor] 自动保存 {count} 条到竞品收藏")


def run_competitor_monitor(config: dict = None) -> dict:
    """
    便捷函数：运行竞品监控。

    Args:
        config: 竞品监控配置

    Returns:
        {"success": bool, "count": int, "data": list, "error": str}
    """
    monitor = CompetitorMonitor(config)
    return monitor.run()
