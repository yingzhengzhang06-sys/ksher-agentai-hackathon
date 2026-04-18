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
    COUNTRY_OPTIONS, EXTERNAL_KNOWLEDGE_SOURCES,
)


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
        "content": ["base", "strategy", "operations"],
        "knowledge": ["base", "operations", "strategy"],
        "design": ["base", "strategy"],
    }

    # 行业 → 子目录映射
    INDUSTRY_DIR_MAP = {
        "b2c": "b2c",
        "b2b": "b2b",
        "service": "service_trade",
    }

    def __init__(self, knowledge_dir: Optional[str] = None):
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self._cache: Dict[str, str] = {}  # 文件路径 → 内容缓存

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

        # 5. 加载外部动态知识库（龙虾等外部源，无需手动同步）
        external = self._load_external_knowledge(agent_name, context)
        if external:
            parts.append(external)

        result = "\n".join(parts).strip()
        return result if result else "# 知识库加载完成（暂无匹配文档）"

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
