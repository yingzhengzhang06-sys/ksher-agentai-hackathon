"""
知识注入服务 — 处理文档上传、分块、与知识库融合

核心功能：
- 文档处理：PDF / MD / TXT 文本提取
- 智能分块：按段落/语义分块，保持连贯性
- 分类标注：行业/国家/产品/规则/竞品/销售
- 自动关联 Agent：根据内容自动判断关联到哪些 Agent
- 与 KnowledgeLoader 集成：训练知识注入到 Prompt
"""
import os
import re
import uuid
import logging
from typing import Optional
from config import BASE_DIR
from services.training_service import (
    add_knowledge_chunks_batch,
    add_training_document,
    get_training_documents,
    CATEGORY_LABELS,
    CATEGORY_ICONS,
)

logger = logging.getLogger(__name__)

# 分块大小配置（仅用于旧版 fallback）
CHUNK_SIZE = 500  # 字符数
CHUNK_OVERLAP = 50  # 重叠字符数

# 优先使用知识蒸馏器（PARA 语义分块）
_DISTILLER_AVAILABLE = True

# Agent → 知识分类映射（优先级）
AGENT_CATEGORY_PRIORITY = {
    "speech":          ["sales", "industry", "country"],
    "cost":            ["product", "competitor", "rules"],
    "proposal":        ["industry", "product", "sales"],
    "objection":       ["sales", "competitor"],
    "content":         ["industry", "sales"],
    "design":          ["product", "industry"],
    "knowledge":       ["industry", "country", "product", "rules", "faq"],
    "knowledge_agent": ["industry", "country", "product", "rules", "faq"],
    "pipeline_writer":  ["industry", "sales"],
    "pipeline_editor": ["industry", "sales"],
    "pipeline_analyzer": ["industry", "product"],
    "pipeline_reporter": ["industry", "product"],
}


# ──────────────────────────────────────────────────────────────
# 文档处理
# ──────────────────────────────────────────────────────────────
def extract_text_from_file(file_path: str) -> str:
    """从文件提取文本"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    if ext in (".md", ".markdown"):
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    if ext == ".pdf":
        return _extract_pdf(file_path)

    if ext in (".docx", ".doc"):
        return _extract_docx(file_path)

    logger.warning(f"不支持的文件类型: {ext}")
    return ""


def _extract_pdf(file_path: str) -> str:
    """提取 PDF 文本"""
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        texts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                texts.append(text)
        return "\n".join(texts)
    except ImportError:
        logger.warning("pypdf 未安装，无法提取 PDF")
        return _fallback_file_read(file_path)
    except Exception as e:
        logger.warning(f"PDF 提取失败: {e}")
        return ""


def _extract_docx(file_path: str) -> str:
    """提取 DOCX 文本"""
    try:
        import docx
        doc = docx.Document(file_path)
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(texts)
    except ImportError:
        logger.warning("python-docx 未安装，无法提取 DOCX")
        return ""
    except Exception as e:
        logger.warning(f"DOCX 提取失败: {e}")
        return ""


def _fallback_file_read(file_path: str) -> str:
    """兜底读取（尝试直接读二进制文件中的可读文本）"""
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        # 尝试解码可读字符
        text = raw.decode("utf-8", errors="ignore")
        # 过滤掉控制字符
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", text)
        return text.strip()
    except Exception:
        return ""


# ──────────────────────────────────────────────────────────────
# 文本分块（优先语义分块，fallback 固定字符）
# ──────────────────────────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP,
               use_distiller: bool = True) -> list[str]:
    """
    将长文本分块，保持段落连贯

    Args:
        use_distiller: True=使用知识蒸馏器的语义分块（按"论点"分割），
                       False=使用旧版固定字符分块
    """
    if not text:
        return []

    # 优先使用知识蒸馏器的语义分块
    if use_distiller and _DISTILLER_AVAILABLE:
        try:
            from services.knowledge_distiller import _semantic_chunk
            chunks = _semantic_chunk(text)
            if chunks:
                return chunks
        except (ImportError, Exception):
            pass

    # Fallback：按段落/句子分块
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    current = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(para) > chunk_size:
            if current:
                chunks.append("\n".join(current))
                current = []
            sub_chunks = _split_long_paragraph(para, chunk_size, overlap)
            chunks.extend(sub_chunks)
        else:
            current.append(para)
            if sum(len(p) + 1 for p in current) > chunk_size:
                chunks.append("\n".join(current))
                if len(current) > 1:
                    current = [current[-1]]
                else:
                    current = []

    if current:
        chunks.append("\n".join(current))

    return [c.strip() for c in chunks if c.strip()]


def _split_long_paragraph(text: str, chunk_size: int, overlap: int) -> list[str]:
    """分割超长段落"""
    sentences = re.split(r"(?<=[。！？.!?])", text)
    chunks = []
    current = ""

    for sent in sentences:
        if len(current) + len(sent) > chunk_size and current:
            chunks.append(current.strip())
            # 从末尾取 overlap 字符作为下一块开头
            current = current[-overlap:] + sent
        else:
            current += sent

    if current.strip():
        chunks.append(current.strip())

    return chunks


# ──────────────────────────────────────────────────────────────
# 文档自动分类
# ──────────────────────────────────────────────────────────────
def auto_classify_content(text: str) -> list[str]:
    """根据文本内容自动判断知识分类"""
    text_lower = text.lower()
    categories = []

    # 关键词匹配
    keyword_map = {
        "industry":    ["行业", "市场", "电商", "跨境", "增长", "gmv", "东南亚", "趋势"],
        "country":     ["泰国", "马来", "印尼", "越南", "菲律宾", "thailand", "malaysia", "indonesia"],
        "product":      ["产品", "功能", "费率", "到账", "牌照", "ksher", "收款", "账户"],
        "rules":        ["合规", "监管", "法律", "规定", "审查", "kyc", "aml"],
        "competitor":   ["竞品", "pingpong", "万里汇", "payssion", "连连", "xtransfer", "对手"],
        "sales":        ["话术", "销售", "客户", "异议", "成交", "拜访", "跟进"],
        "faq":          ["问题", "faq", "常见", "如何", "怎么", "步骤", "流程"],
    }

    for cat, keywords in keyword_map.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                if cat not in categories:
                    categories.append(cat)
                break

    # 默认归类
    if not categories:
        categories = ["sales"]

    return categories


def auto_assign_agents(text: str) -> list[str]:
    """根据文本内容自动判断关联的 Agent"""
    text_lower = text.lower()
    agents = []

    # Agent 内容关联关键词
    agent_keywords = {
        "speech":     ["话术", "销售", "客户", "拜访", "微信", "电梯", "跟进", "pitch"],
        "cost":       ["成本", "费率", "手续费", "节省", "对比", "计算", "省钱"],
        "proposal":   ["方案", "提案", "商业", "合作", "产品推荐", "解决方案"],
        "objection":  ["异议", "顾虑", "担心", "反对", "回复策略", "安全", "切换"],
        "content":    ["朋友圈", "内容", "文案", "发布", "小红书", "抖音", "视频"],
        "design":     ["海报", "设计", "ppt", "演示", "幻灯片", "配色"],
        "knowledge":  ["知识", "问答", "产品", "功能", "合规", "监管"],
    }

    for agent, keywords in agent_keywords.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                if agent not in agents:
                    agents.append(agent)
                break

    # 默认关联到所有内容型 Agent
    if not agents:
        agents = ["knowledge", "content", "speech"]

    return agents


# ──────────────────────────────────────────────────────────────
# 主流程：知识蒸馏 + 注入
# ──────────────────────────────────────────────────────────────
def process_distilled_knowledge(
    text: str,
    title: str = "",
    agent_name: str = "",
    user_intent: str = "",
) -> dict:
    """
    蒸馏增强版知识注入（推荐使用）

    1. 调用知识蒸馏器（PARA 语义分块）
    2. 自动计算 Agent 路由
    3. 存储知识块到 training.db
    """
    if not text or len(text) < 50:
        return {"success": False, "message": "文本内容过少"}

    try:
        from services.knowledge_distiller import distill_and_inject
    except ImportError:
        # Fallback to old method
        return process_text_knowledge(text, title or "知识注入", agent_name or "knowledge", "sales")

    return distill_and_inject(text, title, agent_name, user_intent)


# ──────────────────────────────────────────────────────────────
# 主流程：处理上传文档（legacy）
# ──────────────────────────────────────────────────────────────
def process_uploaded_document(
    file_path: str,
    title: str,
    agent_name: str = "",
    category: str = "",
    primary_category: str = "",
) -> dict:
    """
    处理上传的文档：

    1. 提取文本
    2. 智能分块
    3. 自动分类 + Agent 关联
    4. 存储到 training.db
    """
    # 1. 提取文本
    text = extract_text_from_file(file_path)
    if not text or len(text) < 50:
        return {"success": False, "message": "文件内容过少或无法提取文本"}

    # 2. 分块
    chunks = chunk_text(text)
    if not chunks:
        return {"success": False, "message": "文本分块失败"}

    # 3. 自动分类
    if not primary_category:
        auto_cats = auto_classify_content(text)
        primary_category = auto_cats[0] if auto_cats else "sales"
    else:
        auto_cats = [primary_category] + auto_classify_content(text)
        auto_cats = list(dict.fromkeys(auto_cats))  # 去重保序

    # 4. 自动关联 Agent
    auto_agents = auto_assign_agents(text)
    if agent_name:
        if agent_name not in auto_agents:
            auto_agents.insert(0, agent_name)
    else:
        agent_name = auto_agents[0] if auto_agents else "knowledge"

    # 5. 存储文档记录
    doc_id = add_training_document(
        agent_name=agent_name,
        category=primary_category,
        title=title,
        content_text=text[:5000],  # 截断存储
        file_path=file_path,
        chunk_count=len(chunks),
    )

    # 6. 批量存储知识块（每个 Agent 一套）
    total_chunks = 0
    for ag in auto_agents:
        ag_chunks = []
        for i, chunk_text in enumerate(chunks):
            ag_chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "agent_name": ag,
                "doc_id": doc_id,
                "category": primary_category,
                "content": chunk_text,
                "chunk_index": i,
            })
        if ag_chunks:
            total_chunks += add_knowledge_chunks_batch(ag_chunks)

    return {
        "success": True,
        "doc_id": doc_id,
        "total_chunks": total_chunks,
        "agents": auto_agents,
        "categories": auto_cats,
        "chunk_count": len(chunks),
    }


def process_text_knowledge(
    text: str,
    title: str,
    agent_name: str,
    category: str,
) -> dict:
    """处理纯文本知识（直接输入，非文件上传）"""
    if not text or len(text) < 20:
        return {"success": False, "message": "文本内容过少"}

    chunks = chunk_text(text)
    if not chunks:
        return {"success": False, "message": "文本分块失败"}

    doc_id = add_training_document(
        agent_name=agent_name,
        category=category,
        title=title,
        content_text=text[:5000],
    )

    all_agents = [agent_name] + auto_assign_agents(text)
    all_agents = list(dict.fromkeys(all_agents))

    total_chunks = 0
    for ag in all_agents:
        ag_chunks = []
        for i, chunk_text in enumerate(chunks):
            ag_chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "agent_name": ag,
                "doc_id": doc_id,
                "category": category,
                "content": chunk_text,
                "chunk_index": i,
            })
        if ag_chunks:
            total_chunks += add_knowledge_chunks_batch(ag_chunks)

    return {
        "success": True,
        "doc_id": doc_id,
        "total_chunks": total_chunks,
        "agents": all_agents,
        "chunk_count": len(chunks),
    }


# ──────────────────────────────────────────────────────────────
# 知识融合（供 KnowledgeLoader 调用）
# ──────────────────────────────────────────────────────────────
def build_training_knowledge_section(
    agent_name: str,
    categories: list[str] = None,
    max_chars: int = 1500,
) -> str:
    """
    构建训练知识段落（供注入到 Prompt 的知识融合规则中）
    """
    from services.training_service import get_knowledge_chunks

    if not categories:
        categories = AGENT_CATEGORY_PRIORITY.get(agent_name, ["sales"])

    lines = [f"## 训练补充知识（{agent_name}专属）\n"]

    for cat in categories:
        chunks = get_knowledge_chunks(agent_name, category=cat, limit=3)
        if not chunks:
            continue

        icon = CATEGORY_ICONS.get(cat, "📋")
        lines.append(f"\n### {icon} {CATEGORY_LABELS.get(cat, cat)}\n")
        for c in chunks:
            # 截断单个块，避免超出
            content = c.content[:300] + ("..." if len(c.content) > 300 else "")
            lines.append(f"- {content}\n")

        if sum(len(l) for l in lines) > max_chars + 500:
            break

    result = "".join(lines)
    if len(result) > max_chars:
        result = result[:max_chars] + f"\n\n...（共 {len(chunks)} 个知识块）"

    return result


# ──────────────────────────────────────────────────────────────
# 知识统计
# ──────────────────────────────────────────────────────────────
def get_knowledge_stats(agent_name: str = "") -> dict:
    """获取知识统计"""
    from services.training_service import get_training_stats

    stats = get_training_stats(agent_name)
    from services.training_service import get_all_knowledge_chunks
    from collections import Counter

    chunks = get_all_knowledge_chunks(limit=1000)
    by_cat = Counter(c["category"] for c in chunks)

    return {
        "total_chunks": stats["total_chunks"],
        "by_category": dict(by_cat),
        "total_docs": stats["total_pairs"],
    }
