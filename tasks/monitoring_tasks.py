"""
监控 Celery 任务

竞品监控、行业新闻抓取、engagement 数据采集。
"""
import logging

from celery import shared_task
from services.social_crawler import SocialCrawler

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="tasks.crawl_competitor_posts")
def crawl_competitor_posts(self, platforms: list = None, limit: int = 10) -> dict:
    """
    爬取竞品社交媒体动态。

    Returns:
        {"success": bool, "count": int, "error": str}
    """
    logger.info("[Celery] 爬取竞品动态")
    try:
        if platforms is None:
            platforms = ["xiaohongshu", "weibo"]

        crawler = SocialCrawler()
        total_posts = 0

        for platform in platforms:
            try:
                # 竞品列表（可配置化）
                competitors = ["PingPong", "万里汇", "XTransfer"] if platform == "weibo" else ["PingPong", "万里汇"]
                for comp in competitors:
                    posts = crawler.crawl_platform(platform, query=comp, limit=limit)
                    total_posts += len(posts)
                    logger.debug(f"[Celery] {platform}/{comp}: {len(posts)} 条")
            except Exception as e:
                logger.warning(f"[Celery] 爬取失败 {platform}/{comp}: {e}")

        logger.info(f"[Celery] 竞品爬取完成: {total_posts} 条")
        return {"success": True, "count": total_posts, "error": ""}
    except Exception as e:
        logger.exception("[Celery] 竞品爬取异常")
        return {"success": False, "count": 0, "error": str(e)}


@shared_task(bind=True, name="tasks.fetch_industry_news")
def fetch_industry_news(self, keywords: list = None) -> dict:
    """
    抓取行业新闻（跨境电商、支付等）。

    Returns:
        {"success": bool, "count": int, "error": str}
    """
    logger.info("[Celery] 抓取行业新闻")
    try:
        if keywords is None:
            keywords = ["跨境支付", "东南亚电商", "B2B贸易"]

        from services.web_content import WebContentCrawler
        crawler = WebContentCrawler()
        total_news = 0

        for kw in keywords:
            try:
                articles = crawler.search_news(kw, limit=5)
                total_news += len(articles)
                logger.debug(f"[Celery] 新闻搜索 '{kw}': {len(articles)} 条")
            except Exception as e:
                logger.warning(f"[Celery] 新闻搜索失败 '{kw}': {e}")

        logger.info(f"[Celery] 行业新闻抓取完成: {total_news} 条")
        return {"success": True, "count": total_news, "error": ""}
    except Exception as e:
        logger.exception("[Celery] 行业新闻抓取异常")
        return {"success": False, "count": 0, "error": str(e)}


@shared_task(bind=True, name="tasks.collect_engagement_metrics")
def collect_engagement_metrics(self, material_ids: list = None) -> dict:
    """
    采集内容 engagement 数据（impressions / engagements / clicks）。

    Phase 1: 手动录入 + Excel 导入（为 API 接入预留）

    Returns:
        {"success": bool, "count": int, "error": str}
    """
    logger.info("[Celery] 采集 engagement 数据")
    try:
        # Phase 1: 当前阶段暂无真实 API，返回占位
        # 将来接入微信/企微/抖音的开放平台 API
        logger.info("[Celery] engagement 采集: Phase 1 暂无 API")
        return {"success": True, "count": 0, "error": ""}
    except Exception as e:
        logger.exception("[Celery] engagement 采集异常")
        return {"success": False, "count": 0, "error": str(e)}
