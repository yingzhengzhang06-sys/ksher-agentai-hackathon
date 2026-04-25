"""
知识蒸馏器 — 知识宫殿 PARA 蒸馏管道

将原始材料转化为结构化知识卡片，同时计算最优 Agent 路由。

核心流程（6 Phase）：
1. 接收与理解：材料类型判断 + 用户意图
2. 结构化蒸馏：核心论点提取 + Actionable Insights + 可质疑处
3. 认知更新检测：与已有知识对比
4. PARA 归类：Projects/Areas/Resources/Archives + Agent路由
5. 知识卡片生成：标准化输出
6. 批量存储：training.db 知识块 + Agent关联

输出：
- 结构化知识卡片（PARA格式）
- Agent路由建议（按优先级）
- 知识分类标签
"""
import re
import uuid
import json
import logging
from typing import Optional
from dataclasses import dataclass, field

from config import BASE_DIR

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# 知识卡片数据结构
# ──────────────────────────────────────────────────────────────
@dataclass
class KnowledgeCard:
    """结构化知识卡片（知识宫殿输出格式）"""
    core_thesis: str           # 核心论点（1-2句话）
    key_concepts: list[dict]   # 关键概念 [{name, definition}]
    premises: list[str]        # 前提假设
    reasoning: list[str]       # 推理链
    conclusions: list[str]    # 结论
    actionable_insights: list[dict]  # 可执行洞察 [{insight, scenario}]
    questionable_points: list[dict]  # 可质疑处 [{point, flag}]
    cognitive_update: Optional[dict] = None  # {old, new, reason}
    para_category: str = "Resources"  # PARA 归类
    tags: list[str] = field(default_factory=list)
    suggested_agents: list[str] = field(default_factory=list)
    suggested_categories: list[str] = field(default_factory=list)
    raw_chunks: list[str] = field(default_factory=list)  # 语义分块结果


# ──────────────────────────────────────────────────────────────
# PARA 分类映射（适配 Ksher 业务）
# ──────────────────────────────────────────────────────────────
# Ksher 业务 → PARA 映射
BUSINESS_PARA_MAP = {
    # Areas — 长期关注的业务领域
    "行业研究": "Areas",
    "市场分析": "Areas",
    "客户洞察": "Areas",
    "竞品研究": "Areas",
    # Resources — 可复用方法论
    "销售方法": "Resources",
    "话术技巧": "Resources",
    "产品知识": "Resources",
    "合规规则": "Resources",
    # Projects — 特定项目相关
    "项目文档": "Projects",
    "客户方案": "Projects",
    # Archives — 历史归档
    "历史案例": "Archives",
    "旧话术": "Archives",
}

# Agent 路由关键词（语义分块后判断）
AGENT_ROUTE_KEYWORDS = {
    "speech": ["话术", "销售", "拜访", "跟进", "pitch", "电梯", "微信", "开场"],
    "cost": ["成本", "费率", "手续费", "节省", "对比", "计算", "省钱", "账期"],
    "proposal": ["方案", "提案", "商业", "合作", "解决", "推荐"],
    "objection": ["异议", "顾虑", "担心", "反对", "安全", "切换", "麻烦"],
    "content": ["内容", "朋友圈", "文案", "发布", "小红书", "抖音", "视频"],
    "design": ["海报", "设计", "PPT", "视觉", "配色"],
    "knowledge": ["知识", "问答", "FAQ", "合规", "监管", "产品"],
    "trainer_advisor": ["培训", "学习", "课程", "计划"],
    "finance_health": ["财务", "健康", "诊断", "利润率"],
    "sales_risk": ["风险", "风控", "合规", "审查", "KYC"],
}


# ──────────────────────────────────────────────────────────────
# Phase 1: 接收与理解
# ──────────────────────────────────────────────────────────────
def detect_material_type(text: str) -> str:
    """判断材料类型"""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["#", "##", "###", "标题", "##"]):
        return "文章/文档"
    if any(kw in text_lower for kw in ["对话", "聊天记录", "interview", "transcript"]):
        return "对话记录"
    if any(kw in text_lower for kw in ["想法", "灵感", "idea", "insight"]):
        return "个人想法"
    if len(text) > 3000 and "\n\n" in text:
        return "报告/书籍"
    return "笔记摘录"


def parse_intent(user_intent: str) -> str:
    """解析用户意图，返回处理模式"""
    if not user_intent:
        return "知识体系化"
    intent_lower = user_intent.lower()
    if any(kw in intent_lower for kw in ["完整", "详细", "全面"]):
        return "完整蒸馏"
    if any(kw in intent_lower for kw in ["快速", "简略", "概要"]):
        return "快速归档"
    if any(kw in intent_lower for kw in ["体系", "知识", "系统"]):
        return "知识体系化"
    return "知识体系化"


# ──────────────────────────────────────────────────────────────
# Phase 2: 结构化蒸馏（核心）
# ──────────────────────────────────────────────────────────────
def distill_structure(text: str) -> dict:
    """
    结构化蒸馏 — 从文本中提取核心成分

    返回：
        {
            "core_thesis": str,
            "key_concepts": [{"name": str, "definition": str}],
            "actionable_insights": [{"insight": str, "scenario": str}],
            "questionable_points": [{"point": str, "flag": str}],
        }
    """
    # 语义分块：按段落 + 逻辑单元分割
    raw_chunks = _semantic_chunk(text)

    # 句子级别的关键信息提取
    sentences = re.split(r"(?<=[。！？.!?])", text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s) > 10]

    # 核心论点：取第一段或第一句
    core_thesis = ""
    for chunk in raw_chunks[:2]:
        if len(chunk) > 20:
            core_thesis = chunk[:200]
            break
    if not core_thesis and sentences:
        core_thesis = sentences[0][:200]

    # 关键概念：从文本中识别带定义的概念
    key_concepts = _extract_key_concepts(text)

    # Actionable Insights：从动词句中提取
    actionable_insights = _extract_actionable_insights(sentences)

    # 可质疑处：识别假设和不确定表述
    questionable_points = _extract_questionable_points(text)

    return {
        "core_thesis": core_thesis or "（未能提取核心论点）",
        "key_concepts": key_concepts,
        "actionable_insights": actionable_insights,
        "questionable_points": questionable_points,
    }


def _semantic_chunk(text: str) -> list[str]:
    """
    语义分块 — 按"论点"分割，而非固定字符数

    分割策略：
    1. 按段落分割（保持语义连贯）
    2. 按二级标题分割（## 标记）
    3. 按数字列表分割（1. 2. 3.）
    4. 合并过小片段（<100字）与相邻块
    5. 标注每个块的核心主题
    """
    if not text:
        return []

    chunks = []

    # 策略1：按 markdown 二级标题分割
    sections = re.split(r"(?=\n##\s)", text)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # 移除标题行，只保留内容
        title_match = re.match(r"^##\s+(.+)\n", section)
        if title_match:
            section = section[len(title_match.group(0)):]

        # 如果片段超过 800 字，按段落进一步细分
        if len(section) > 800:
            sub_parts = re.split(r"\n\s*\n", section)
            current = []
            current_len = 0

            for part in sub_parts:
                part = part.strip()
                if not part:
                    continue

                # 如果单段落超过 400 字，作为独立块
                if len(part) > 400:
                    if current:
                        chunks.append("\n\n".join(current).strip())
                        current = []
                    chunks.append(part)
                    current_len = 0
                else:
                    if current_len + len(part) > 800:
                        if current:
                            chunks.append("\n\n".join(current).strip())
                        current = [part]
                        current_len = len(part)
                    else:
                        current.append(part)
                        current_len += len(part)

            if current:
                chunks.append("\n\n".join(current).strip())
        else:
            # 小于 800 字作为一个块
            chunks.append(section)

    # 策略2：检查是否有数字列表段落（独立切割）
    numbered_pattern = r"(?:^|\n)(?:\d+[.、]\s*.{20,})"
    numbered_matches = list(re.finditer(numbered_pattern, text))
    for match in numbered_matches:
        # 如果数字列表项不在已有块中，单独提取
        num_text = match.group(0).strip()
        if num_text and len(num_text) > 30 and num_text not in chunks:
            chunks.append(num_text)

    # 过滤空块和过短块
    filtered = [c.strip() for c in chunks if c.strip() and len(c.strip()) > 50]
    return filtered[:20]  # 最多20个语义块


def _extract_key_concepts(text: str) -> list[dict]:
    """提取关键概念"""
    concepts = []

    # 模式1：名词+定义模式 "X 是/指/为 Y"
    patterns = [
        r"([\u4e00-\u9fff]{2,8})\s+(?:是|指|为|称为|叫做|即)\s*([^，。,.]{10,50})",
        r"([\u4e00-\u9fff]{2,8})(?:的概念|的定义|的含义)\s*([^，。,.]{10,50})",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            name = m.group(1).strip()
            definition = m.group(2).strip()[:80]
            if name and definition and name not in [c["name"] for c in concepts]:
                concepts.append({"name": name, "definition": definition})

    # 模式2：引号中的术语
    for m in re.finditer(r"「([^」]{2,10})」|『([^』]{2,10})』", text):
        term = (m.group(1) or m.group(2)).strip()
        if term and term not in [c["name"] for c in concepts]:
            concepts.append({"name": term, "definition": "（术语，需补充定义）"})

    return concepts[:8]  # 最多8个概念


def _extract_actionable_insights(sentences: list[str]) -> list[dict]:
    """提取可执行洞察"""
    insights = []
    action_keywords = [
        "应该", "要", "必须", "建议", "可以", "要避免", "不要",
        "通过", "利用", "使用", "采用", "做好", "关注", "注意",
        "优先", "重点", "关键", "核心", "诀窍", "技巧",
    ]

    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 20 or len(sent) > 200:
            continue
        for kw in action_keywords:
            if kw in sent:
                # 简化陈述
                insight_text = sent
                # 判断适用场景
                scenario = _infer_scenario(sent)
                insights.append({
                    "insight": insight_text[:150],
                    "scenario": scenario,
                })
                break

    return insights[:6]  # 最多6条


def _infer_scenario(text: str) -> str:
    """推断适用场景"""
    scenario_map = {
        "销售拜访": ["拜访", "客户", "开场", "面谈"],
        "跟进沟通": ["微信", "跟进", "短信", "联系"],
        "异议处理": ["异议", "反对", "顾虑", "质疑"],
        "方案撰写": ["方案", "提案", "报价", "PPT"],
        "成本分析": ["成本", "费率", "对比", "省钱"],
        "竞品分析": ["竞品", "对比", "竞争", "对手"],
        "客户签约": ["签约", "合同", "成交", "付款"],
        "合规审查": ["合规", "监管", "KYC", "审查"],
    }
    for scene, keywords in scenario_map.items():
        for kw in keywords:
            if kw in text:
                return scene
    return "通用场景"


def _extract_questionable_points(text: str) -> list[dict]:
    """识别可质疑处"""
    questionable = []
    flag_keywords = {
        r"(?:可能|也许|或许|大概)" : "不确定性",
        r"(?:通常|一般|往往|多数)" : "过度概括",
        r"(?:假设|前提是|建立在)" : "前提假设",
        r"(?:待验证|需确认|不确定)" : "待验证",
        r"(?:但|然而|不过|然而)" : "转折待辨",
    }

    sentences = re.split(r"(?<=[。！？.!?])", text)
    for sent in sentences:
        for pat, flag in flag_keywords.items():
            if re.search(pat, sent):
                questionable.append({
                    "point": sent.strip()[:150],
                    "flag": flag,
                })
                break

    return questionable[:4]


# ──────────────────────────────────────────────────────────────
# Phase 3: 认知更新检测（简化版 — 与已有知识块对比）
# ──────────────────────────────────────────────────────────────
def detect_cognitive_update(text: str, agent_name: str = "") -> Optional[dict]:
    """
    检测认知更新：与已有知识库对比，判断是否有新观点

    简化实现：通过关键词冲突判断
    """
    try:
        from services.training_service import get_knowledge_chunks
    except ImportError:
        return None

    if not agent_name:
        return None

    chunks = get_knowledge_chunks(agent_name, limit=5)
    if not chunks:
        return None  # 没有已有知识，无法对比

    # 检测矛盾关键词
    contradiction_pairs = [
        ("高", "低"), ("快", "慢"), ("便宜", "贵"),
        ("安全", "风险"), ("简单", "复杂"),
    ]
    text_lower = text.lower()
    for high, low in contradiction_pairs:
        if high in text_lower and low in text_lower:
            return {
                "old": f"存在 {high}/{low} 的不同表述",
                "new": "检测到矛盾性表述",
                "reason": "文本中同时出现对立关键词，可能需要人工核实",
            }

    return None


# ──────────────────────────────────────────────────────────────
# Phase 4: PARA 归类 + Agent 路由计算
# ──────────────────────────────────────────────────────────────
def classify_para(text: str, title: str = "") -> str:
    """
    判断 PARA 分类

    归类决策树：
    - 与当前项目直接相关？ → Projects
    - 长期关注的业务领域？ → Areas
    - 可复用的方法论/资源？ → Resources
    - 已完成/归档？ → Archives
    - 跨领域主题？ → Theme
    """
    combined = (title + " " + text).lower()

    # Projects 关键词
    if any(kw in combined for kw in ["项目", "案例", "客户", "签约", "目标", "计划"]):
        return "Projects"
    # Areas 关键词
    if any(kw in combined for kw in ["市场", "行业", "趋势", "分析", "研究", "洞察"]):
        return "Areas"
    # Resources 关键词
    if any(kw in combined for kw in ["方法", "技巧", "话术", "流程", "规范", "培训", "规则"]):
        return "Resources"
    # Archives 关键词
    if any(kw in combined for kw in ["历史", "旧版", "已结束", "归档"]):
        return "Archives"

    return "Areas"  # 默认归类


def compute_agent_routing(text: str) -> tuple[list[str], list[str]]:
    """
    计算 Agent 路由 + 知识分类

    返回：(agent_list, category_list)
    """
    text_lower = text.lower()
    scored_agents: dict[str, float] = {}
    scored_cats: dict[str, float] = {}

    for agent, keywords in AGENT_ROUTE_KEYWORDS.items():
        score = sum(2 if kw in text_lower else 0 for kw in keywords)
        # 加权：多关键词命中得分更高
        if score > 0:
            scored_agents[agent] = score

    # 排序，取 top 4
    sorted_agents = sorted(scored_agents.items(), key=lambda x: x[1], reverse=True)
    top_agents = [a[0] for a in sorted_agents[:4]]

    # 知识分类
    cat_keywords = {
        "industry": ["市场", "行业", "趋势", "电商", "增长"],
        "country": ["泰国", "马来", "印尼", "越南", "菲律宾", "本地"],
        "product": ["产品", "费率", "到账", "牌照", "收款"],
        "rules": ["合规", "监管", "KYC", "AML", "法律"],
        "competitor": ["竞品", "PingPong", "万里汇", "XTransfer"],
        "sales": ["话术", "销售", "客户", "拜访", "跟进"],
        "faq": ["问题", "FAQ", "常见", "如何"],
    }
    for cat, keywords in cat_keywords.items():
        if any(kw in text_lower for kw in keywords):
            scored_cats[cat] = scored_cats.get(cat, 0) + 1

    top_cats = list(scored_cats.keys())[:4]

    return top_agents, top_cats


# ──────────────────────────────────────────────────────────────
# Phase 5 & 6: 主蒸馏管道
# ──────────────────────────────────────────────────────────────
def distill_knowledge(
    text: str,
    title: str = "",
    agent_name: str = "",
    user_intent: str = "",
) -> tuple[KnowledgeCard, list[str], list[str]]:
    """
    知识蒸馏主管道（Phase 1-6）

    Args:
        text: 原始文本内容
        title: 文档标题
        agent_name: 主要目标 Agent
        user_intent: 用户意图描述

    Returns:
        (KnowledgeCard, agent_routing, categories)
    """
    if len(text) < 50:
        raise ValueError("文本内容过少（<50字），无法蒸馏")

    # Phase 1: 接收与理解
    material_type = detect_material_type(text)
    intent = parse_intent(user_intent)

    # Phase 2: 结构化蒸馏（核心）
    structure = distill_structure(text)

    # Phase 3: 认知更新检测
    cognitive_update = detect_cognitive_update(text, agent_name)

    # Phase 4: PARA 归类 + Agent 路由
    para_category = classify_para(text, title)
    if agent_name and agent_name not in structure.get("suggested_agents", []):
        suggested_agents = [agent_name] + [
            a for a in _compute_routing_from_text(text) if a != agent_name
        ]
    else:
        suggested_agents = _compute_routing_from_text(text)
    suggested_cats = _compute_categories_from_text(text)

    # 合并 distill_structure 的结果
    if isinstance(structure, dict):
        card = KnowledgeCard(
            core_thesis=structure.get("core_thesis", ""),
            key_concepts=structure.get("key_concepts", []),
            actionable_insights=structure.get("actionable_insights", []),
            questionable_points=structure.get("questionable_points", []),
            premises=[],
            reasoning=[],
            conclusions=[],
            cognitive_update=cognitive_update,
            para_category=para_category,
            suggested_agents=suggested_agents,
            suggested_categories=suggested_cats,
            raw_chunks=_semantic_chunk(text),
        )
    else:
        card = structure

    return card, suggested_agents[:4], suggested_cats[:4]


def _compute_routing_from_text(text: str) -> list[str]:
    text_lower = text.lower()
    scores = {}
    for agent, keywords in AGENT_ROUTE_KEYWORDS.items():
        score = sum(2 if kw in text_lower else 0 for kw in keywords)
        if score > 0:
            scores[agent] = score
    return [a for a, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)][:4]


def _compute_categories_from_text(text: str) -> list[str]:
    text_lower = text.lower()
    cats = []
    cat_keywords = {
        "industry": ["市场", "行业", "趋势", "电商", "增长", "东南亚"],
        "country": ["泰国", "马来", "印尼", "越南", "菲律宾", "thailand"],
        "product": ["产品", "费率", "到账", "牌照", "收款", "账户"],
        "rules": ["合规", "监管", "KYC", "AML", "法律"],
        "competitor": ["竞品", "PingPong", "万里汇", "XTransfer"],
        "sales": ["话术", "销售", "客户", "拜访", "跟进"],
        "faq": ["问题", "FAQ", "常见"],
    }
    for cat, keywords in cat_keywords.items():
        if any(kw in text_lower for kw in keywords):
            cats.append(cat)
    return cats if cats else ["sales"]


# ──────────────────────────────────────────────────────────────
# 批量处理：知识注入到 training.db
# ──────────────────────────────────────────────────────────────
def distill_and_inject(
    text: str,
    title: str = "",
    agent_name: str = "",
    user_intent: str = "",
) -> dict:
    """
    蒸馏 + 注入一条龙

    返回：
    {
        "success": bool,
        "card": KnowledgeCard,
        "agent_routing": list[str],
        "categories": list[str],
        "total_chunks": int,
        "doc_id": str,
    }
    """
    try:
        card, agents, cats = distill_knowledge(text, title, agent_name, user_intent)
    except ValueError as e:
        return {"success": False, "message": str(e)}

    try:
        from services.training_service import add_training_document, add_knowledge_chunks_batch
    except ImportError:
        return {"success": False, "message": "training_service 未导入"}

    # 存储文档记录
    primary_agent = agent_name or (agents[0] if agents else "knowledge")
    primary_cat = cats[0] if cats else "sales"

    doc_id = add_training_document(
        agent_name=primary_agent,
        category=primary_cat,
        title=title or "知识卡片",
        content_text=text[:5000],
    )

    # 语义分块（而非固定500字）
    chunks = card.raw_chunks or _semantic_chunk(text)
    if not chunks:
        chunks = [text[:800]]

    # 批量存储知识块（每个关联 Agent 一套）
    total_chunks = 0
    for ag in agents:
        ag_chunks = []
        for i, chunk_text in enumerate(chunks):
            ag_chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "agent_name": ag,
                "doc_id": doc_id,
                "category": primary_cat,
                "content": chunk_text,
                "chunk_index": i,
            })
        if ag_chunks:
            total_chunks += add_knowledge_chunks_batch(ag_chunks)

    return {
        "success": True,
        "card": card,
        "agent_routing": agents,
        "categories": cats,
        "total_chunks": total_chunks,
        "doc_id": doc_id,
        "para_category": card.para_category,
        "core_thesis": card.core_thesis,
        "insights_count": len(card.actionable_insights),
    }


# ──────────────────────────────────────────────────────────────
# 知识卡片格式化输出（用于展示）
# ──────────────────────────────────────────────────────────────
def format_card_markdown(card: KnowledgeCard, title: str = "") -> str:
    """将知识卡片格式化为 Markdown 展示"""
    lines = [f"# {title or '知识卡片'}\n"]

    if card.core_thesis:
        lines.append(f"> **核心论点：** {card.core_thesis}\n")

    if card.key_concepts:
        lines.append("## 关键概念\n")
        for c in card.key_concepts[:5]:
            lines.append(f"- **{c['name']}**：{c['definition']}")
        lines.append("")

    if card.actionable_insights:
        lines.append("## 可执行洞察\n")
        for i, ins in enumerate(card.actionable_insights[:5], 1):
            lines.append(f"{i}. **{ins['insight']}**")
            lines.append(f"   → 适用场景：{ins['scenario']}")
        lines.append("")

    if card.cognitive_update:
        lines.append("## 认知更新\n")
        cu = card.cognitive_update
        lines.append(f"- **旧认知**：{cu.get('old', '')}")
        lines.append(f"- **新认知**：{cu.get('new', '')}")
        lines.append(f"- **变化原因**：{cu.get('reason', '')}\n")

    if card.questionable_points:
        lines.append("## 可质疑处\n")
        for q in card.questionable_points[:3]:
            lines.append(f"- {q['point']} *[{q['flag']}]*")
        lines.append("")

    lines.append(f"_PARA分类：{card.para_category}_")

    return "\n".join(lines)