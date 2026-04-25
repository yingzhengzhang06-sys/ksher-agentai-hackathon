"""
网页内容获取服务

优先用 Newspaper4k（轻量、快速），失败降级到 Crawl4AI（处理JS渲染页面）。
两个都没安装时返回错误提示，不影响系统运行。

用法：
    from services.web_content import fetch_url_sync
    result = fetch_url_sync("https://example.com/article")
    if result["success"]:
        print(result["title"], result["text"])
"""

import asyncio
from typing import Optional

# ---- 动态导入，优雅降级 ----
_HAS_NEWSPAPER = False
_HAS_CRAWL4AI = False

try:
    from newspaper import Article as _Article
    _HAS_NEWSPAPER = True
except Exception:
    pass

try:
    from crawl4ai import AsyncWebCrawler as _AsyncWebCrawler
    _HAS_CRAWL4AI = True
except Exception:
    pass


MAX_TEXT_LENGTH = 5000  # 正文截断长度


def _empty_result(url: str, error: str = "") -> dict:
    return {
        "title": "",
        "text": "",
        "summary": "",
        "keywords": [],
        "top_image": "",
        "source_url": url,
        "publish_date": "",
        "success": False,
        "error": error,
    }


def _fetch_with_newspaper(url: str) -> dict:
    """用 Newspaper4k 提取文章内容"""
    try:
        article = _Article(url, language="zh")
        article.download()
        article.parse()

        text = (article.text or "").strip()
        if not text:
            return _empty_result(url, "Newspaper4k: 未提取到正文")

        # 尝试NLP（可能没装nltk，忽略错误）
        keywords = []
        summary = ""
        try:
            article.nlp()
            keywords = list(article.keywords or [])
            summary = article.summary or ""
        except Exception:
            summary = text[:200] + "..." if len(text) > 200 else text

        return {
            "title": article.title or "",
            "text": text[:MAX_TEXT_LENGTH],
            "summary": summary[:500],
            "keywords": keywords[:10],
            "top_image": article.top_image or "",
            "source_url": url,
            "publish_date": str(article.publish_date or ""),
            "success": True,
            "error": "",
        }
    except Exception as e:
        return _empty_result(url, f"Newspaper4k 失败: {str(e)[:100]}")


async def _fetch_with_crawl4ai(url: str) -> dict:
    """用 Crawl4AI 提取网页内容（支持JS渲染）"""
    try:
        async with _AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)

            if not result.success:
                return _empty_result(url, f"Crawl4AI 失败: {result.error_message or '未知错误'}")

            text = (result.markdown or "").strip()
            if not text:
                return _empty_result(url, "Crawl4AI: 未提取到内容")

            # 从markdown中提取标题（第一个#行）
            title = ""
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("#"):
                    title = line.lstrip("#").strip()
                    break

            return {
                "title": title,
                "text": text[:MAX_TEXT_LENGTH],
                "summary": text[:300] + "..." if len(text) > 300 else text,
                "keywords": [],
                "top_image": "",
                "source_url": url,
                "publish_date": "",
                "success": True,
                "error": "",
            }
    except Exception as e:
        return _empty_result(url, f"Crawl4AI 失败: {str(e)[:100]}")


async def fetch_url(url: str) -> dict:
    """
    抓取单个URL，返回结构化内容。

    降级策略：Newspaper4k → Crawl4AI → 错误返回
    """
    if not url or not url.startswith(("http://", "https://")):
        return _empty_result(url, "无效的URL")

    # 策略1: 先用 Newspaper4k（轻量快速）
    if _HAS_NEWSPAPER:
        result = _fetch_with_newspaper(url)
        if result["success"]:
            return result

    # 策略2: 降级到 Crawl4AI
    if _HAS_CRAWL4AI:
        result = await _fetch_with_crawl4ai(url)
        if result["success"]:
            return result

    # 都不可用
    if not _HAS_NEWSPAPER and not _HAS_CRAWL4AI:
        return _empty_result(url, "未安装内容抓取库（newspaper4k 或 crawl4ai），请运行 pip install newspaper4k crawl4ai")

    return _empty_result(url, "内容提取失败，请检查URL是否可访问")


async def fetch_urls(urls: list) -> list:
    """批量抓取多个URL"""
    results = []
    for url in urls:
        r = await fetch_url(url)
        results.append(r)
    return results


def fetch_url_sync(url: str) -> dict:
    """同步版本（Streamlit友好）"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Streamlit 环境中可能已有event loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, fetch_url(url))
                return future.result(timeout=30)
        else:
            return asyncio.run(fetch_url(url))
    except Exception as e:
        return _empty_result(url, f"执行失败: {str(e)[:100]}")


def fetch_urls_sync(urls: list) -> list:
    """批量同步版本"""
    return [fetch_url_sync(url) for url in urls]


def is_available() -> bool:
    """检查是否有可用的抓取库"""
    return _HAS_NEWSPAPER or _HAS_CRAWL4AI


def get_status() -> str:
    """返回当前可用的抓取库状态"""
    parts = []
    if _HAS_NEWSPAPER:
        parts.append("Newspaper4k ✓")
    if _HAS_CRAWL4AI:
        parts.append("Crawl4AI ✓")
    return " | ".join(parts) if parts else "未安装抓取库"
