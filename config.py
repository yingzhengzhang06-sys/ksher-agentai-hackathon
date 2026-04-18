"""
Ksher AgentAI 智能工作台 — 全局配置
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ==========================================
# API 配置
# ==========================================

# Kimi API（创意型Agent）
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
KIMI_MODEL = os.getenv("MODEL_NAME_KIMI", "kimi-k2.5")

# Claude API（精准型Agent）— 通过 Cherry AI 第三方平台
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://open.cherryin.ai/v1")
ANTHROPIC_MODEL = os.getenv("MODEL_NAME_SONNET", "anthropic/claude-sonnet-4.6")

# ==========================================
# Agent → 模型映射（核心路由表）
# ==========================================
AGENT_MODEL_MAP = {
    "speech": "kimi",       # 话术 → 创意型
    "content": "kimi",      # 内容 → 创意型
    "design": "kimi",       # 设计 → 创意型
    "objection": "kimi",    # 异议 → 创意型
    "cost": "sonnet",       # 成本 → 精准型
    "proposal": "sonnet",   # 方案 → 精准型
    "knowledge": "sonnet",  # 知识 → 精准型
}

# Agent 温度参数
AGENT_TEMPERATURE = {
    "speech": 0.7,
    "content": 0.8,
    "design": 0.6,
    "objection": 0.7,
    "cost": 0.3,
    "proposal": 0.5,
    "knowledge": 0.3,
}

# ==========================================
# 项目路径
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# ==========================================
# Streamlit 配置
# ==========================================
STREAMLIT_THEME = os.getenv("STREAMLIT_THEME", "dark")
PAGE_TITLE = "Ksher AgentAI 智能工作台"
PAGE_ICON = "⚔️"

# ==========================================
# 品牌色（从 assets/brand_colors.json 加载）
# ==========================================
BRAND_COLORS = {
    "primary": "#E83E4C",
    "primary_dark": "#C52D3A",
    "primary_light": "#FF6B76",
    "secondary": "#1A1A2E",
    "accent": "#00C9A7",
    "background": "#0F0F1A",
    "surface": "#1E1E2F",
    "text_primary": "#FFFFFF",
    "text_secondary": "#B0B0C0",
    "text_muted": "#6B6B7B",
    "success": "#00C9A7",
    "warning": "#FFB800",
    "danger": "#E83E4C",
    "info": "#3B82F6",
}

# ==========================================
# 战场类型定义
# ==========================================
BATTLEFIELD_TYPES = {
    "increment": {
        "label": "增量战场（从银行抢客户）",
        "speech_focus": "帮你算一笔你没算过的账——银行隐性成本远高于你以为的",
        "cost_focus": "对比银行：突出汇损+时间成本+固定手续费3项隐性成本",
        "proposal_focus": "降维打击——费率/速度/服务全面碾压银行",
        "objection_focus": "常见：安全性质疑+嫌换渠道麻烦+没听过Ksher",
    },
    "stock": {
        "label": "存量战场（从竞品抢客户）",
        "speech_focus": "东南亚这块，我们有硬差异——本地牌照+更低费率",
        "cost_focus": "对比竞品：突出费率差+汇率差+到账速度差",
        "proposal_focus": "差异化切入——Ksher东南亚本地牌照的独特优势",
        "objection_focus": "常见：已绑定竞品+觉得差不多+懒得迁移",
    },
    "education": {
        "label": "教育战场（新客户/未选定渠道）",
        "speech_focus": "跨境收款有3个坑——手续费高、到账慢、合规风险",
        "cost_focus": "全景对比：所有主流渠道费率+Ksher优势定位",
        "proposal_focus": "帮客户建立选择标准，引导选Ksher",
        "objection_focus": "常见：不着急+再看看+量太小觉得不需要",
    },
}

# ==========================================
# 渠道 → 战场映射
# ==========================================
CHANNEL_BATTLEFIELD_MAP = {
    # 增量战场（从银行抢客户）
    "银行电汇": "increment",
    "招商银行": "increment",
    "工商银行": "increment",
    "建设银行": "increment",
    "中国银行": "increment",
    "bank": "increment",
    "银行": "increment",

    # 存量战场（从竞品抢客户）
    "PingPong": "stock",
    "pingpong": "stock",
    "万里汇": "stock",
    "WorldFirst": "stock",
    "XTransfer": "stock",
    "xtransfer": "stock",
    "连连支付": "stock",
    "光子易": "stock",
    "空中云汇": "stock",

    # 教育战场（新客户/未选定）
    "未选定": "education",
    "暂无": "education",
    "": "education",
}

# ==========================================
# 行业选项
# ==========================================
INDUSTRY_OPTIONS = {
    "b2c": "跨境电商（B2C）",
    "b2b": "跨境货贸（B2B）",
    "service": "服务贸易",
}

# 国家选项
COUNTRY_OPTIONS = {
    "thailand": "泰国（THB）",
    "malaysia": "马来西亚（MYR）",
    "philippines": "菲律宾（PHP）",
    "indonesia": "印尼（IDR）",
    "vietnam": "越南（VND）",
    "hongkong": "香港（HKD）",
    "europe": "欧洲（EUR）",
}

# 当前渠道选项
CHANNEL_OPTIONS = [
    "银行电汇",
    "PingPong",
    "万里汇",
    "XTransfer",
    "连连支付",
    "光子易",
    "空中云汇",
    "未选定",
]

# 痛点选项
PAIN_POINT_OPTIONS = [
    "手续费高",
    "到账慢",
    "汇率损失大",
    "合规担忧",
    "多平台管理麻烦",
    "客户服务差",
    "开户流程复杂",
]
