"""
中文关键词提取服务

基于 jieba 的 TF-IDF 和 TextRank 算法提取中文关键词。
jieba 未安装时降级为简单的高频词统计。

用法：
    from services.keyword_extractor import extract_keywords, render_keyword_tags
    kws = extract_keywords("跨境支付行业的最新趋势...", topk=5)
    tags_html = render_keyword_tags(kws)
"""

import re
from typing import List, Tuple

# ---- 动态导入 ----
_HAS_JIEBA = False

try:
    import jieba
    import jieba.analyse
    _HAS_JIEBA = True
except Exception:
    pass


# 跨境支付行业停用词（补充通用停用词）
_STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那",
    "但", "可以", "没", "能", "还", "因为", "所以", "如果", "什么",
    "而", "或", "与", "及", "等", "把", "被", "从", "之", "为", "中",
    "个", "月", "年", "日", "时", "分", "更", "让", "做", "使",
}


def extract_keywords(text: str, topk: int = 10,
                     method: str = "tfidf") -> List[Tuple[str, float]]:
    """
    提取中文关键词。

    Args:
        text: 输入文本
        topk: 返回关键词数量
        method: "tfidf" 或 "textrank"

    Returns:
        [(关键词, 权重), ...]  权重归一化到0-1
    """
    if not text or not text.strip():
        return []

    if _HAS_JIEBA:
        if method == "textrank":
            kws = jieba.analyse.textrank(
                text, topK=topk, withWeight=True
            )
        else:
            kws = jieba.analyse.extract_tags(
                text, topK=topk, withWeight=True
            )
        # 过滤停用词和单字
        return [(w, round(s, 4)) for w, s in kws
                if w not in _STOP_WORDS and len(w) >= 2][:topk]
    else:
        return _fallback_keywords(text, topk)


def _fallback_keywords(text: str, topk: int) -> List[Tuple[str, float]]:
    """jieba不可用时的降级方案：简单高频词统计"""
    # 按标点和空白切分
    words = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
    if not words:
        return []

    freq = {}
    for w in words:
        if w not in _STOP_WORDS:
            freq[w] = freq.get(w, 0) + 1

    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    if not sorted_words:
        return []

    max_freq = sorted_words[0][1]
    return [(w, round(c / max_freq, 4)) for w, c in sorted_words[:topk]]


def render_keyword_tags(keywords: List[Tuple[str, float]],
                        max_display: int = 8) -> str:
    """
    将关键词列表渲染为HTML标签字符串。

    Returns:
        HTML string，可直接用 st.markdown(..., unsafe_allow_html=True) 展示
    """
    if not keywords:
        return ""

    tags = []
    for word, weight in keywords[:max_display]:
        # 根据权重调整颜色深浅
        opacity = max(0.4, min(1.0, weight))
        tags.append(
            f"<span style='display:inline-block;padding:0.15rem 0.5rem;"
            f"margin:0.1rem;border-radius:4px;font-size:0.8rem;"
            f"background:rgba(232,62,76,{opacity * 0.15});"
            f"color:rgba(232,62,76,{opacity});'>{word}</span>"
        )

    return f"🏷 {''.join(tags)}"


def is_available() -> bool:
    """jieba是否可用"""
    return _HAS_JIEBA
