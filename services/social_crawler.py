"""
社交平台内容爬虫服务

基于 Playwright 实现社交平台内容搜索。
支持平台：小红书 / 抖音 / 微博 / 知乎 / B站

降级策略：Playwright 不可用时返回 Mock 数据。
"""

import asyncio
import json
import re
from dataclasses import dataclass, asdict
from typing import Optional

# --- Playwright 可用性检测 ---
_HAS_PLAYWRIGHT = False
try:
    from playwright.async_api import async_playwright
    _HAS_PLAYWRIGHT = True
except ImportError:
    pass


@dataclass
class SocialPost:
    """社交平台帖子统一格式"""
    platform: str       # "xhs" / "douyin" / "weibo" / "zhihu" / "bilibili"
    title: str
    content: str
    author: str
    likes: int
    comments: int
    url: str
    publish_time: str

    def to_dict(self) -> dict:
        return asdict(self)


# 平台配置
PLATFORM_CONFIG = {
    "xhs": {
        "name": "小红书",
        "search_url": "https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes",
        "icon": "📕",
    },
    "douyin": {
        "name": "抖音",
        "search_url": "https://www.douyin.com/search/{keyword}?type=video",
        "icon": "🎵",
    },
    "weibo": {
        "name": "微博",
        "search_url": "https://s.weibo.com/weibo?q={keyword}",
        "icon": "🔴",
    },
    "zhihu": {
        "name": "知乎",
        "search_url": "https://www.zhihu.com/search?type=content&q={keyword}",
        "icon": "🔵",
    },
    "bilibili": {
        "name": "B站",
        "search_url": "https://search.bilibili.com/all?keyword={keyword}",
        "icon": "📺",
    },
}

PLATFORM_NAMES = {k: v["name"] for k, v in PLATFORM_CONFIG.items()}


async def _search_xhs(page, keyword: str, limit: int) -> list[SocialPost]:
    """小红书搜索"""
    posts = []
    url = PLATFORM_CONFIG["xhs"]["search_url"].format(keyword=keyword)
    try:
        await page.goto(url, wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        items = await page.query_selector_all(".note-item, .search-note-item, section.note-item")
        for item in items[:limit]:
            title_el = await item.query_selector(".title, .note-title, h3")
            author_el = await item.query_selector(".author-wrapper .name, .user-name, .nickname")
            likes_el = await item.query_selector(".like-wrapper .count, .engagement .like")
            link_el = await item.query_selector("a")

            title = await title_el.inner_text() if title_el else ""
            author = await author_el.inner_text() if author_el else ""
            likes_text = await likes_el.inner_text() if likes_el else "0"
            href = await link_el.get_attribute("href") if link_el else ""

            likes_num = _parse_count(likes_text)
            full_url = f"https://www.xiaohongshu.com{href}" if href and not href.startswith("http") else href

            posts.append(SocialPost(
                platform="xhs", title=title.strip(), content=title.strip(),
                author=author.strip(), likes=likes_num, comments=0,
                url=full_url or url, publish_time="",
            ))
    except Exception as e:
        print(f"[social_crawler] 小红书搜索异常: {e}")
    return posts


async def _search_bilibili(page, keyword: str, limit: int) -> list[SocialPost]:
    """B站搜索"""
    posts = []
    url = PLATFORM_CONFIG["bilibili"]["search_url"].format(keyword=keyword)
    try:
        await page.goto(url, wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        items = await page.query_selector_all(".video-list-item, .bili-video-card")
        for item in items[:limit]:
            title_el = await item.query_selector(".bili-video-card__info--tit a, .title")
            author_el = await item.query_selector(".bili-video-card__info--author, .up-name")
            link_el = await item.query_selector("a")

            title = await title_el.inner_text() if title_el else ""
            author = await author_el.inner_text() if author_el else ""
            href = await link_el.get_attribute("href") if link_el else ""
            full_url = f"https:{href}" if href and href.startswith("//") else href

            posts.append(SocialPost(
                platform="bilibili", title=title.strip(), content=title.strip(),
                author=author.strip(), likes=0, comments=0,
                url=full_url or url, publish_time="",
            ))
    except Exception as e:
        print(f"[social_crawler] B站搜索异常: {e}")
    return posts


async def _search_zhihu(page, keyword: str, limit: int) -> list[SocialPost]:
    """知乎搜索"""
    posts = []
    url = PLATFORM_CONFIG["zhihu"]["search_url"].format(keyword=keyword)
    try:
        await page.goto(url, wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        items = await page.query_selector_all(".SearchResult-Card, .List-item")
        for item in items[:limit]:
            title_el = await item.query_selector("h2 span, .ContentItem-title")
            content_el = await item.query_selector(".CopyrightRichText-richText, .RichContent-inner")
            author_el = await item.query_selector(".AuthorInfo-name, .UserLink-link")

            title = await title_el.inner_text() if title_el else ""
            content = await content_el.inner_text() if content_el else ""
            author = await author_el.inner_text() if author_el else ""

            posts.append(SocialPost(
                platform="zhihu", title=title.strip(), content=content.strip()[:500],
                author=author.strip(), likes=0, comments=0,
                url=url, publish_time="",
            ))
    except Exception as e:
        print(f"[social_crawler] 知乎搜索异常: {e}")
    return posts


async def _search_weibo(page, keyword: str, limit: int) -> list[SocialPost]:
    """微博搜索"""
    posts = []
    url = PLATFORM_CONFIG["weibo"]["search_url"].format(keyword=keyword)
    try:
        await page.goto(url, wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        items = await page.query_selector_all(".card-wrap, [action-type='feed_list_item']")
        for item in items[:limit]:
            content_el = await item.query_selector(".txt, .content p")
            author_el = await item.query_selector(".name, .avator .W_texta")

            content = await content_el.inner_text() if content_el else ""
            author = await author_el.inner_text() if author_el else ""

            posts.append(SocialPost(
                platform="weibo", title=content.strip()[:60], content=content.strip()[:500],
                author=author.strip(), likes=0, comments=0,
                url=url, publish_time="",
            ))
    except Exception as e:
        print(f"[social_crawler] 微博搜索异常: {e}")
    return posts


async def _search_douyin(page, keyword: str, limit: int) -> list[SocialPost]:
    """抖音搜索"""
    posts = []
    url = PLATFORM_CONFIG["douyin"]["search_url"].format(keyword=keyword)
    try:
        await page.goto(url, wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        items = await page.query_selector_all(".search-result-card, .video-card")
        for item in items[:limit]:
            title_el = await item.query_selector(".title, .video-title")
            author_el = await item.query_selector(".author-name, .nickname")

            title = await title_el.inner_text() if title_el else ""
            author = await author_el.inner_text() if author_el else ""

            posts.append(SocialPost(
                platform="douyin", title=title.strip(), content=title.strip(),
                author=author.strip(), likes=0, comments=0,
                url=url, publish_time="",
            ))
    except Exception as e:
        print(f"[social_crawler] 抖音搜索异常: {e}")
    return posts


_SEARCH_FUNCS = {
    "xhs": _search_xhs,
    "douyin": _search_douyin,
    "weibo": _search_weibo,
    "zhihu": _search_zhihu,
    "bilibili": _search_bilibili,
}


def _parse_count(text: str) -> int:
    """解析数字文本：1.2万 → 12000"""
    text = text.strip().replace(",", "")
    if not text:
        return 0
    try:
        if "万" in text:
            return int(float(text.replace("万", "")) * 10000)
        if "w" in text.lower():
            return int(float(text.lower().replace("w", "")) * 10000)
        return int(re.sub(r"[^\d]", "", text) or 0)
    except (ValueError, TypeError):
        return 0


# ============================================================
# 公开 API
# ============================================================

async def search_platform(platform: str, keyword: str, limit: int = 10) -> list[SocialPost]:
    """搜索单个平台"""
    if not _HAS_PLAYWRIGHT:
        return _mock_search(platform, keyword, limit)

    func = _SEARCH_FUNCS.get(platform)
    if not func:
        return []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            results = await func(page, keyword, limit)
            await browser.close()
            return results if results else _mock_search(platform, keyword, min(limit, 3))
    except Exception as e:
        print(f"[social_crawler] Playwright error for {platform}: {e}")
        return _mock_search(platform, keyword, min(limit, 3))


async def search_all_platforms(keyword: str, limit_per_platform: int = 5) -> dict[str, list[SocialPost]]:
    """全平台并行搜索"""
    results = {}
    for platform in PLATFORM_CONFIG:
        posts = await search_platform(platform, keyword, limit_per_platform)
        results[platform] = posts
    return results


def search_sync(platform: str, keyword: str, limit: int = 10) -> list[SocialPost]:
    """同步包装，供Streamlit调用"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, search_platform(platform, keyword, limit))
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(search_platform(platform, keyword, limit))
    except RuntimeError:
        return asyncio.run(search_platform(platform, keyword, limit))


def search_all_sync(keyword: str, limit_per_platform: int = 5) -> dict[str, list[SocialPost]]:
    """全平台同步搜索"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, search_all_platforms(keyword, limit_per_platform))
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(search_all_platforms(keyword, limit_per_platform))
    except RuntimeError:
        return asyncio.run(search_all_platforms(keyword, limit_per_platform))


def is_available() -> bool:
    return _HAS_PLAYWRIGHT


def get_status() -> str:
    if _HAS_PLAYWRIGHT:
        return "✅ Playwright 已安装，社交平台爬虫可用"
    return "⚠️ Playwright 未安装，使用示例数据"


# ============================================================
# Mock 数据（Playwright不可用时的降级方案）
# ============================================================

def _mock_search(platform: str, keyword: str, limit: int) -> list[SocialPost]:
    """生成Mock搜索结果"""
    platform_name = PLATFORM_NAMES.get(platform, platform)
    mock_posts = [
        SocialPost(
            platform=platform,
            title=f"【{keyword}】{platform_name}热门内容：跨境支付新趋势分析",
            content=f"关于「{keyword}」的深度分析：随着东南亚电商市场持续增长，跨境支付领域迎来新机遇。多家支付公司纷纷布局本地化收款...",
            author=f"{platform_name}行业分析师",
            likes=1580,
            comments=234,
            url=f"https://example.com/{platform}/1",
            publish_time="2026-04-18",
        ),
        SocialPost(
            platform=platform,
            title=f"{keyword}实操经验分享：从0到月收款百万的秘诀",
            content=f"做{keyword}这行三年了，踩过不少坑。最大的教训就是选错支付渠道，费率高、到账慢、客服响应差。后来切换到本地牌照服务商...",
            author="跨境老王",
            likes=3200,
            comments=456,
            url=f"https://example.com/{platform}/2",
            publish_time="2026-04-17",
        ),
        SocialPost(
            platform=platform,
            title=f"2026年{keyword}行业报告：市场规模突破万亿",
            content=f"据最新数据显示，2026年{keyword}相关市场规模已突破万亿大关，同比增长23%。其中东南亚市场增速最快...",
            author="行业研究院",
            likes=890,
            comments=123,
            url=f"https://example.com/{platform}/3",
            publish_time="2026-04-16",
        ),
        SocialPost(
            platform=platform,
            title=f"竞品对比：{keyword}领域Top5服务商横评",
            content=f"我们花了2周时间对比了{keyword}领域最热门的5家服务商，从费率、合规、技术、服务4个维度打分...",
            author="评测达人小李",
            likes=2100,
            comments=378,
            url=f"https://example.com/{platform}/4",
            publish_time="2026-04-15",
        ),
        SocialPost(
            platform=platform,
            title=f"小白入门{keyword}：你需要知道的10件事",
            content=f"刚入行{keyword}？别慌，这篇文章帮你理清思路。第一步选对收款工具最重要，关注费率、到账速度、牌照合规...",
            author="新手导师",
            likes=670,
            comments=89,
            url=f"https://example.com/{platform}/5",
            publish_time="2026-04-14",
        ),
    ]
    return mock_posts[:limit]


# ============================================================
# SocialCrawler 兼容类（供 tasks/monitoring_tasks.py 使用）
# ============================================================

class SocialCrawler:
    """
    社交平台爬虫兼容类。

    封装 search_sync / search_all_sync，提供面向对象 API，
    供 Celery 监控任务调用。
    """

    # 外部名称 -> 内部平台 key 的映射
    _PLATFORM_MAP = {
        "xiaohongshu": "xhs",
        "xhs": "xhs",
        "weibo": "weibo",
        "douyin": "douyin",
        "zhihu": "zhihu",
        "bilibili": "bilibili",
    }

    def crawl_platform(self, platform: str, query: str, limit: int = 10) -> list[dict]:
        """
        爬取单个平台内容。

        Args:
            platform: 平台名（"xiaohongshu" / "weibo" / "douyin" 等）
            query: 搜索关键词
            limit: 最大条数

        Returns:
            list[dict]: 帖子列表，每个帖子为 dict 格式
        """
        internal_key = self._PLATFORM_MAP.get(platform, platform)
        posts = search_sync(internal_key, query, limit)
        return [post.to_dict() for post in posts]

    def crawl_all(self, query: str, limit_per_platform: int = 5) -> dict[str, list[dict]]:
        """爬取所有平台内容"""
        results = search_all_sync(query, limit_per_platform)
        return {
            platform: [post.to_dict() for post in posts]
            for platform, posts in results.items()
        }
