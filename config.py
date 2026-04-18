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
# 外部知识库源（动态引用，无需复制到项目目录）
# 格式: [(路径, 描述), ...]
# 知识库更新后自动生效，无需手动同步
# ==========================================
EXTERNAL_KNOWLEDGE_SOURCES = [
    (os.path.expanduser("~/.qclaw/workspace-agent-cdae0ad6/"), "龙虾知识库"),
]

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
    "background": "#FFFFFF",
    "surface": "#F5F5F7",
    "surface_hover": "#EBEBF0",
    "text_primary": "#1D1D1F",
    "text_secondary": "#86868B",
    "text_muted": "#A1A1A6",
    "border": "#D2D2D7",
    "border_light": "#E8E8ED",
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

# ==========================================
# Mock 成本模型参数 —— 修改此处数字即可更新所有演示数据
# 数据来源：fee_structure.json + 行业公开数据
#
# 使用方式：修改下面数字 → 保存 → 重新生成作战包即可生效
# 无需改动任何 .py 代码文件
# ==========================================
RATES_CONFIG = {
    # Ksher 自身费率（基准）
    "ksher": {
        "b2b_fee_rate": 0.004,       # 手续费 0.4%（来自 fee_structure.json B2B标准）
        "b2c_fee_rate": 0.008,       # 手续费 0.8%（来自 fee_structure.json B2C标准）
        "fx_spread": 0.002,          # 汇率点差 0.2%（本地牌照直接清算优势）
    },
    # 各渠道费率对比
    "channels": {
        "银行电汇": {
            "fee_rate": 0.0015,      # 手续费折算率（电报费+中间行按年折算）
            "fixed_cost_annual": 1.5, # 固定年费（万元）：SWIFT电报+中间行扣费
            "fx_spread": 0.008,      # 汇率点差 0.8%（银行结汇加点，核心隐性成本）
            "time_cost_rate": 0.001,  # 资金占用成本 0.1%（3-5天到账）
            "mgmt_cost_rate": 0.0005, # 管理成本 0.05%（对账/退汇/查询人工）
            "rate_label": "约 1.0%",
            "notes": "银行核心痛点：汇率损失（占成本64%）+ 固定费用 + 到账慢",
        },
        "竞品综合": {  # PingPong/万里汇/XTransfer/连连支付/光子易/空中云汇 共用
            "fee_rate": 0.004,       # 手续费 0.4%（行业公开 0.3-0.5%）
            "fixed_cost_annual": 0.0, # 无固定费用
            "fx_spread": 0.003,      # 汇率点差 0.3%（比银行好，比Ksher差）
            "time_cost_rate": 0.0005, # 资金占用 0.05%（中转1-2天）
            "mgmt_cost_rate": 0.0,    # 无额外管理成本
            "rate_label": "约 0.7%",
            "notes": "竞品核心痛点：无东南亚本地牌照，需中转；汇率点差仍有优化空间",
        },
        "默认": {
            "fee_rate": 0.003,
            "fixed_cost_annual": 0.5,
            "fx_spread": 0.005,
            "time_cost_rate": 0.001,
            "mgmt_cost_rate": 0.0005,
            "rate_label": "约 0.9%",
            "notes": "默认/未选定渠道的中间估算值",
        },
    },
    # 成本项文案映射（用于 Summary 解读）
    "cost_labels": {
        "银行电汇": {
            "痛点标题": "当前银行电汇的核心痛点不是\"费率\"，而是隐性成本",
            "痛点1": "汇率损失最大：银行结汇汇率通常比市场中间价高 0.8-1.5%",
            "痛点2": "固定费用蚕食利润：每笔 SWIFT 电报费 ¥150-300 + 中间行扣费 $15-50",
            "痛点3": "到账慢=资金贵：3-5 个工作日到账，资金占用年化成本",
            "切换优势": "本地牌照直接清算，综合成本降至 0.6%",
        },
        "竞品综合": {
            "痛点标题": "费率已较低，但仍有优化空间",
            "痛点1": "汇率点差：结汇汇率点差约 0.3-0.5%",
            "痛点2": "中转成本：无东南亚本地牌照，资金需经第三方中转",
            "切换优势": "泰国/马来/菲律宾/印尼 本地支付牌照，直接清算",
        },
    },
}
