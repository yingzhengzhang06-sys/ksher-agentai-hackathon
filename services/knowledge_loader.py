"""
知识库加载器 — 按Agent名+客户上下文选择性加载知识库
"""
import os
import json
import glob
from typing import Dict, List, Optional
import sys

# 确保能导入 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    KNOWLEDGE_DIR, BATTLEFIELD_TYPES, INDUSTRY_OPTIONS,
    COUNTRY_OPTIONS,
)

# 兼容旧版 config.py（Streamlit Cloud 缓存问题）
try:
    from config import EXTERNAL_KNOWLEDGE_SOURCES
except ImportError:
    EXTERNAL_KNOWLEDGE_SOURCES = []


class KnowledgeLoader:
    """
    按Agent名 + 客户上下文，选择性加载知识库文件，拼接为文本。

    知识库目录结构：
        knowledge/
        ├── index.json          # 索引文件
        ├── base/               # 基础知识
        ├── b2c/                # B2C各国
        ├── b2b/                # B2B各国
        ├── service_trade/      # 服务贸易
        ├── products/           # 特色产品
        ├── competitors/        # 竞品分析
        ├── operations/         # 操作+FAQ
        ├── strategy/           # 行业方案+优势策略
        └── fee_structure.json  # 费率参数
    """

    # Agent → 知识库文件映射（相对 knowledge/ 目录）
    AGENT_KNOWLEDGE_MAP = {
        "speech": ["base", "strategy", "fee_structure.json"],
        "cost": ["fee_structure.json", "competitors"],
        "proposal": ["base", "strategy", "products", "fee_structure.json"],
        "objection": ["base", "operations", "competitors"],
        "content": ["base", "strategy", "operations", "products", "competitors"],
        "knowledge": ["base", "operations", "strategy"],
        "design": ["base", "strategy"],
    }

    # 行业 → 子目录映射
    INDUSTRY_DIR_MAP = {
        "b2c": "b2c",
        "b2b": "b2b",
        "service": "service_trade",
        "b2s": "b2b",  # 1688直采复用B2B知识库
    }

    def __init__(self, knowledge_dir: Optional[str] = None, memory_manager=None, use_vector_store: bool = True):
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self._cache: Dict[str, str] = {}  # 文件路径 → 内容缓存
        self.memory_manager = memory_manager  # 可选的向量记忆系统
        self._vector_store = None
        if use_vector_store:
            try:
                from services.vector_store import get_vector_store
                self._vector_store = get_vector_store()
            except Exception:
                self._vector_store = None

    def load(self, agent_name: str, context: dict) -> str:
        """
        按Agent名+客户上下文，选择性加载知识库文件，拼接为文本。

        Args:
            agent_name: Agent名称（speech/cost/proposal/objection/content/knowledge/design）
            context: {
                "industry": str,           # "b2c" | "b2b" | "service"
                "target_country": str,     # "thailand" | "malaysia" | ...
                "current_channel": str,    # 客户当前收款渠道
                ...
            }

        Returns:
            str: 拼接后的知识库文本
        """
        parts: List[str] = []
        industry = context.get("industry", "")
        target_country = context.get("target_country", "")
        current_channel = context.get("current_channel", "")

        # 1. 加载通用基础文档
        base_dirs = self.AGENT_KNOWLEDGE_MAP.get(agent_name, ["base"])
        for item in base_dirs:
            if item == "fee_structure.json":
                content = self._load_fee_structure(context)
                if content:
                    parts.append(content)
            else:
                content = self._load_dir(item)
                if content:
                    parts.append(content)

        # 2. 加载行业专属文档
        industry_dir = self.INDUSTRY_DIR_MAP.get(industry)
        if industry_dir:
            industry_content = self._load_dir(industry_dir, target_country)
            if industry_content:
                parts.append(f"\n\n---\n\n# 行业专属知识（{INDUSTRY_OPTIONS.get(industry, industry)}）\n\n")
                parts.append(industry_content)

        # 3. 加载竞品/渠道对比知识（针对 cost/proposal/objection）
        if agent_name in ("cost", "proposal", "objection") and current_channel:
            competitor_content = self._load_competitor_knowledge(current_channel)
            if competitor_content:
                parts.append(f"\n\n---\n\n# 竞品/渠道对比知识（当前渠道：{current_channel}）\n\n")
                parts.append(competitor_content)

        # 4. 加载战场类型策略指引
        battlefield = self._detect_battlefield(current_channel)
        if battlefield and battlefield in BATTLEFIELD_TYPES:
            bf_info = BATTLEFIELD_TYPES[battlefield]
            parts.append(f"\n\n---\n\n# 战场策略指引\n")
            parts.append(f"战场类型：{bf_info['label']}\n")
            focus_key = f"{agent_name}_focus"
            if focus_key in bf_info:
                parts.append(f"策略重点：{bf_info[focus_key]}\n")

        # 5. 加载训练知识库（用户注入的知识块）
        training_knowledge = self._load_training_knowledge(agent_name, context)
        if training_knowledge:
            parts.append(f"\n\n---\n\n# 训练补充知识\n\n{training_knowledge}")

        # 6. 向量知识检索（如果 memory_manager 可用）
        vector_knowledge = self._query_vector_knowledge(agent_name, context)
        if vector_knowledge:
            parts.append(f"\n\n---\n\n# 向量检索知识\n\n{vector_knowledge}")

        # 7. 加载外部动态知识库（龙虾等外部源，无需手动同步）
        external = self._load_external_knowledge(agent_name, context)
        if external:
            parts.append(external)

        result = "\n".join(parts).strip()
        return result if result else "# 知识库加载完成（暂无匹配文档）"

    def _query_vector_knowledge(self, agent_name: str, context: dict) -> Optional[str]:
        """
        从向量数据库检索相关知识（RAG检索）。
        优先使用 ChromaDB VectorStore，回退到 memory_manager。
        """
        # 1. 尝试使用 VectorStore（ChromaDB）
        if self._vector_store is not None:
            try:
                # 构建查询文本
                query_parts = []
                industry = context.get("industry", "")
                target_country = context.get("target_country", "")
                pain_points = context.get("pain_points", "")

                if pain_points:
                    query_parts.append(str(pain_points))
                if industry:
                    query_parts.append(industry)
                if target_country:
                    query_parts.append(target_country)
                query_parts.append(agent_name)

                query_text = " ".join(query_parts)

                # 构建过滤条件
                filters = None
                if industry in ("b2c", "b2b", "service"):
                    # 可以根据类别过滤，但先不做严格过滤以保留召回率
                    pass

                results = self._vector_store.search(
                    query=query_text,
                    top_k=5,
                    filters=filters,
                )

                if not results:
                    return None

                # 格式化结果，按相关性排序
                lines = ["### 相关知识（RAG检索）\n"]
                for i, r in enumerate(results, 1):
                    score = r.get("score", 0)
                    text = r.get("text", "")
                    meta = r.get("metadata", {})
                    source = meta.get("filename", "未知来源")
                    # 只取前300字，避免过长
                    snippet = text[:300] + "..." if len(text) > 300 else text
                    lines.append(f"[{i}] [{source}] (相关度:{score:.2f})\n{snippet}\n")

                return "\n".join(lines)
            except Exception:
                # VectorStore 失败，回退到 memory_manager
                pass

        # 2. 回退：使用 memory_manager（如果存在）
        if self.memory_manager:
            try:
                query_parts = []
                industry = context.get("industry", "")
                target_country = context.get("target_country", "")
                if industry:
                    query_parts.append(industry)
                if target_country:
                    query_parts.append(target_country)
                if not query_parts:
                    return None

                query_text = f"{' '.join(query_parts)} {agent_name}"
                results = self.memory_manager.query(
                    query_text=query_text,
                    memory_types=["semantic"],
                    top_k=3,
                    agent_name=agent_name,
                )
                if not results:
                    return None

                lines = []
                for r in results:
                    lines.append(f"- {r['content']}")
                return "\n".join(lines)
            except Exception:
                return None

        return None

    def _match_external_file(self, filename: str, agent_name: str, context: dict) -> bool:
        """判断外部文件是否匹配当前 Agent 和上下文。"""
        fname = filename.lower()
        industry = context.get("industry", "")
        target_country = context.get("target_country", "")

        # B2C 文件 → B2C 场景
        if "b2c" in fname and industry == "b2c":
            return True
        # B2B 货贸（不含 service）→ B2B 场景
        if "b2b" in fname and "service" not in fname and industry == "b2b":
            return True
        # 服务贸易 → service 场景
        if "service" in fname and industry == "service":
            return True
        # 越南相关 → 越南目标国家
        if "vietnam" in fname and target_country == "vietnam":
            return True
        # 通用知识（不含 b2b/b2c 细分）→ 所有 Agent
        if "knowledge" in fname and "b2b" not in fname and "b2c" not in fname:
            return True
        # POBO 产品 → proposal / knowledge
        if "pobo" in fname and agent_name in ("proposal", "knowledge"):
            return True
        return False

    def _load_external_knowledge(self, agent_name: str, context: dict) -> Optional[str]:
        """加载外部动态知识库（如龙虾知识库）。文件更新后自动生效。"""
        if not EXTERNAL_KNOWLEDGE_SOURCES:
            return None

        all_parts = []
        for source_path, source_label in EXTERNAL_KNOWLEDGE_SOURCES:
            if not os.path.exists(source_path):
                continue

            md_files = glob.glob(os.path.join(source_path, "*.md"))
            matched_parts = []
            for filepath in sorted(md_files):
                fname = os.path.basename(filepath)
                if not self._match_external_file(fname, agent_name, context):
                    continue
                content = self._load_file(filepath)
                if content:
                    matched_parts.append(
                        f"\n\n## [{source_label}] {fname}\n\n{content}"
                    )

            if matched_parts:
                all_parts.append(
                    f"\n\n---\n\n# 外部补充知识（{source_label}）\n"
                    + "".join(matched_parts)
                )

        return "\n".join(all_parts) if all_parts else None

    def _load_file(self, filepath: str) -> Optional[str]:
        """加载单个文件内容（带缓存）"""
        if filepath in self._cache:
            return self._cache[filepath]

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self._cache[filepath] = content
            return content
        except Exception:
            return None

    def _load_dir(self, dirname: str, filter_keyword: str = "") -> Optional[str]:
        """
        加载目录下所有 .md 文件内容。
        如果提供了 filter_keyword，只加载文件名包含该关键字的文件。
        """
        dir_path = os.path.join(self.knowledge_dir, dirname)
        if not os.path.exists(dir_path):
            return None

        pattern = os.path.join(dir_path, "*.md")
        files = glob.glob(pattern)

        if filter_keyword:
            files = [f for f in files if filter_keyword.lower() in os.path.basename(f).lower()]

        if not files:
            return None

        parts = []
        for filepath in sorted(files):
            content = self._load_file(filepath)
            if content:
                parts.append(f"\n\n## {os.path.basename(filepath)}\n\n{content}")

        return "\n".join(parts) if parts else None

    def _load_fee_structure(self, context: dict) -> Optional[str]:
        """加载费率结构数据，格式化为文本。"""
        json_path = os.path.join(self.knowledge_dir, "fee_structure.json")
        md_path = os.path.join(self.knowledge_dir, "fee_structure.md")

        parts = []

        # 优先加载 JSON（结构化数据）
        data = None
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        if data:
            parts.append(self._format_fee_structure(data, context))

        # 同时加载 MD 说明文档
        md_content = self._load_file(md_path)
        if md_content:
            parts.append(f"\n\n## 费率说明文档\n\n{md_content}")

        return "\n".join(parts) if parts else None

    def _format_fee_structure(self, data: dict, context: dict) -> str:
        """将 fee_structure.json 格式化为易读文本。"""
        industry = context.get("industry", "")
        target_country = context.get("target_country", "")
        monthly_volume = context.get("monthly_volume", 0)

        lines = ["## Ksher 费率结构\n"]

        # Ksher 费率
        ksher = data.get("ksher", {})
        if industry in ksher:
            ind_data = ksher[industry]
            lines.append(f"### {ind_data.get('name', industry)}\n")
            countries = ind_data.get("countries", {})
            if target_country in countries:
                c = countries[target_country]
                lines.append(f"- 目标国家：{target_country}（{c.get('currency', '')}）")
                lines.append(f"- 费率：{c.get('fee_rate', 0) * 100:.2f}%")
                lines.append(f"- 汇率基准：{c.get('fx_benchmark', '')}")
                lines.append(f"- 结算周期：T+{c.get('settlement_days', 1)}")
                if c.get("min_fee_local"):
                    lines.append(f"- 最低手续费：{c['min_fee_local']} {c.get('currency', '')}")
            else:
                lines.append("- 支持国家：" + ", ".join(countries.keys()))

        # 银行费率
        bank = data.get("bank", {})
        if bank:
            lines.append(f"\n### {bank.get('name', '银行电汇')}\n")
            wire = bank.get("wire_transfer", {})
            lines.append(f"- 固定手续费：{wire.get('fee_fixed_per_transaction', 0)} 元/笔")
            lines.append(f"- 费率：{wire.get('fee_rate', 0) * 100:.2f}%")
            lines.append(f"- 汇差：{wire.get('fx_spread', 0) * 100:.2f}%")
            lines.append(f"- 结算周期：T+{wire.get('settlement_days', 3)}")

        # 竞品费率
        competitors = data.get("competitors", {})
        if competitors:
            lines.append("\n### 竞品费率对比\n")
            for key, comp in competitors.items():
                fee_key = f"{industry}_fee_rate" if industry else "b2c_fee_rate"
                fee = comp.get(fee_key, comp.get("b2c_fee_rate", 0))
                lines.append(f"- **{comp.get('name', key)}**：费率 {fee * 100:.2f}%，汇差 {comp.get('fx_spread', 0) * 100:.2f}%，T+{comp.get('settlement_days', 2)} — {comp.get('notes', '')}")

        # 客户等级
        tiers = data.get("customer_tiers", {})
        if monthly_volume and tiers:
            tier = self._detect_customer_tier(monthly_volume, tiers)
            lines.append(f"\n### 客户等级判断\n")
            lines.append(f"- 月交易量：{monthly_volume:,.0f} USD")
            lines.append(f"- 对应等级：{tier}")

        return "\n".join(lines)

    def _detect_customer_tier(self, monthly_volume: float, tiers: dict) -> str:
        """根据月交易量判断客户等级。"""
        sorted_tiers = sorted(tiers.items(), key=lambda x: x[1].get("min_monthly_usd", 0), reverse=True)
        for tier_key, tier_info in sorted_tiers:
            if monthly_volume >= tier_info.get("min_monthly_usd", 0):
                return f"{tier_info.get('label', tier_key)}（{tier_key}级）"
        return "F级"

    def _load_competitor_knowledge(self, current_channel: str) -> Optional[str]:
        """加载竞品对比知识。"""
        # 从 competitors 目录加载
        content = self._load_dir("competitors")
        if content:
            return content

        # 如果没有目录，尝试从 fee_structure.json 中提取
        json_path = os.path.join(self.knowledge_dir, "fee_structure.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                competitors = data.get("competitors", {})
                channel_lower = current_channel.lower()
                for key, comp in competitors.items():
                    if key.lower() in channel_lower or comp.get("name", "").lower() in channel_lower:
                        lines = [f"### {comp.get('name', key)} 详细信息\n"]
                        for k, v in comp.items():
                            if k != "name":
                                lines.append(f"- {k}: {v}")
                        return "\n".join(lines)
            except Exception:
                pass

        return None

    def _detect_battlefield(self, current_channel: str) -> Optional[str]:
        """根据当前渠道判断战场类型。"""
        from config import CHANNEL_BATTLEFIELD_MAP
        return CHANNEL_BATTLEFIELD_MAP.get(current_channel)

    def _load_training_knowledge(self, agent_name: str, context: dict) -> Optional[str]:
        """从 training.db 加载用户注入的训练知识块（按 Agent + 上下文过滤）。"""
        try:
            from services.training_service import (
                get_knowledge_chunks,
                AGENT_KNOWLEDGE_CATEGORIES,
                increment_chunk_retrieval,
                CATEGORY_LABELS,
            )
        except ImportError:
            return None

        categories = AGENT_KNOWLEDGE_CATEGORIES.get(agent_name, ["sales"])
        industry = context.get("industry", "")
        target_country = context.get("target_country", "")

        lines = []
        chunk_ids = []

        for cat in categories:
            chunks = get_knowledge_chunks(agent_name, category=cat, limit=3)
            if not chunks:
                continue

            # 按行业/国家过滤
            filtered = []
            for c in chunks:
                content_lower = c.content.lower()
                if industry and industry.lower() in content_lower:
                    filtered.append(c)
                elif target_country and target_country.lower() in content_lower:
                    filtered.append(c)
                elif not industry and not target_country:
                    filtered.append(c)

            effective = filtered[:2] if filtered else chunks[:1]
            icon = CATEGORY_LABELS.get(cat, cat)
            lines.append(f"### {icon} {cat}\n")
            for c in effective:
                content = c.content[:300] + ("..." if len(c.content) > 300 else "")
                lines.append(f"- {content}\n")
                chunk_ids.append(c.chunk_id)

        if not lines:
            return None

        result = "".join(lines)
        # 截断防止超出
        if len(result) > 2000:
            result = result[:2000] + f"\n\n...（共 {len(chunk_ids)} 个知识块）"

        # 增加检索次数
        for chunk_id in chunk_ids:
            try:
                increment_chunk_retrieval(chunk_id)
            except Exception:
                pass

        return result

    def clear_cache(self):
        """清空文件缓存。"""
        self._cache.clear()


# 便捷函数：快速获取知识库文本
def get_knowledge(agent_name: str, context: dict, knowledge_dir: Optional[str] = None) -> str:
    """便捷函数：快速获取知识库文本。"""
    loader = KnowledgeLoader(knowledge_dir)
    return loader.load(agent_name, context)


if __name__ == "__main__":
    loader = KnowledgeLoader()
    ctx = {
        "industry": "b2c",
        "target_country": "thailand",
        "current_channel": "银行电汇",
        "monthly_volume": 50000,
    }
    print("=" * 60)
    print("KnowledgeLoader 测试")
    print("=" * 60)
    for agent in ["speech", "cost", "proposal", "objection"]:
        print(f"\n--- {agent.upper()} Agent 知识库 ---")
        knowledge = loader.load(agent, ctx)
        print(knowledge[:800] + "..." if len(knowledge) > 800 else knowledge)
