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
KIMI_K26_MODEL = os.getenv("MODEL_NAME_KIMI_K26", "kimi-k2.6")

# Claude API（精准型Agent）— 通过 Cherry AI 第三方平台
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://open.cherryin.ai/v1")
ANTHROPIC_MODEL = os.getenv("MODEL_NAME_SONNET", "anthropic/claude-sonnet-4.6")

# MiniMax API（通识型Agent：知识问答等通用场景）
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")
MINIMAX_MODEL = os.getenv("MODEL_NAME_MINIMAX", "MiniMax-Text-01")

# ==========================================
# Agent → 模型映射（核心路由表，与 llm_client.py 保持一致）
# ==========================================
# 注意：完整映射在 services/llm_client.py 中
# 此处仅保留核心7个Agent的映射，供兼容性使用
AGENT_MODEL_MAP = {
    "speech": "kimi",
    "content": "kimi",
    "design": "kimi",
    "objection": "kimi",
    "cost": "sonnet",
    "proposal": "sonnet",
    "knowledge": "glm",  # GLM-5.1 适合知识问答
}

# ==========================================
# Agent 温度参数（核心7个Agent）
# ==========================================
AGENT_TEMPERATURE = {
    "speech": 0.7,      # 话术 → 创意型
    "content": 0.8,     # 内容 → 创意型
    "design": 0.6,      # 设计 → 创意型
    "objection": 0.7,   # 异议 → 创意型
    "cost": 0.3,        # 成本 → 精准型
    "proposal": 0.5,    # 方案 → 精准型
    "knowledge": 0.5,   # 知识 → GLM-5.1（精准型）
    # K2.6 专属Agent
    "swarm_decomposer": 0.3,   # 任务拆解 → 精准型（需要结构化输出）
    "swarm_quality": 0.2,      # 质量检查 → 最精准
    "ppt_builder": 0.5,        # PPT生成 → 平衡型
    "data_agent": 0.3,         # 数据分析 → 精准型
    "skill_learner": 0.5,      # 技能学习 → 平衡型
    "trigger_agent": 0.3,      # 触发器 → 精准型
}

# ==========================================
# 项目路径
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MATERIALS_DIR = os.path.join(ASSETS_DIR, "materials")

# ==========================================
# 素材上传系统配置（当前阶段：产品设计）
# ==========================================
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "ksher2026")
MATERIALS_DB_PATH = os.path.join(DATA_DIR, "materials.db")
MATERIALS_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MATERIALS_ALLOWED_TYPES = ["image/png", "image/jpeg", "image/jpg"]
MATERIALS_THUMB_MAX_WIDTH = 400
MATERIALS_THUMB_QUALITY = 85

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
PAGE_ICON = ""

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
    "surface": "#f2f2f3",
    "surface_hover": "#e5e6ea",
    "text_primary": "#1d2129",
    "text_secondary": "#8a8f99",
    "text_muted": "#adb3be",
    "border": "#dadce2",
    "border_light": "#e5e6ea",
    "success": "#00C9A7",
    "warning": "#FFB800",
    "danger": "#E83E4C",
    "info": "#3B82F6",
}

# ==========================================
# 设计令牌（Design Tokens）— 统一字号/间距/圆角
# ==========================================
TYPE_SCALE = {
    "xs":      "0.7rem",    # badge、标签、辅助信息
    "sm":      "0.75rem",   # 表头、caption、时间戳
    "base":    "0.85rem",   # 正文、表格行、列表项
    "md":      "0.95rem",   # 副标题、强调文本
    "lg":      "1.1rem",    # 小节标题
    "xl":      "1.5rem",    # 页面标题数字
    "display": "2.5rem",    # 大号评分/指标
}

SPACING = {
    "xs":  "0.25rem",   # 4px
    "sm":  "0.5rem",    # 8px
    "md":  "1rem",      # 16px
    "lg":  "1.5rem",    # 24px
    "xl":  "2rem",      # 32px
}

RADIUS = {
    "sm":  "0.25rem",   # badge、小标签
    "md":  "0.5rem",    # 卡片、按钮、输入框
    "lg":  "0.75rem",   # 大容器、弹窗
}

# ==========================================
# 状态 → 颜色 映射（统一使用，避免各文件重复内联）
# ==========================================
STATUS_COLOR_MAP = {
    # 客户阶段
    "customer_stage": {
        "初次接触": BRAND_COLORS["text_secondary"],
        "已报价":    BRAND_COLORS["info"],
        "试用中":    BRAND_COLORS["warning"],
        "已签约":    BRAND_COLORS["success"],
        "已流失":    BRAND_COLORS["danger"],
    },
    # 重要性/优先级
    "priority": {
        "高": BRAND_COLORS["danger"],
        "中": BRAND_COLORS["warning"],
        "低": BRAND_COLORS["info"],
        "必需": BRAND_COLORS["primary"],
        "可选": BRAND_COLORS["text_secondary"],
    },
    # 置信度
    "confidence": {
        "高": BRAND_COLORS["success"],
        "中": BRAND_COLORS["warning"],
        "低": BRAND_COLORS["info"],
    },
    # 紧急度
    "urgency": {
        "高": BRAND_COLORS["primary"],
        "中": BRAND_COLORS["warning"],
        "低": BRAND_COLORS["info"],
    },
}

# ==========================================
# 工作流引擎配置
# ==========================================
WORKFLOW_CONFIG = {
    "content_lifecycle": {
        "initial_state": "draft",
        "auto_submit_to_review": True,  # 生成后自动进入 review
        "review_timeout_hours": 48,     # 审批超时时间
    },
    "scheduler": {
        "daily_trigger": "06:00",       # 日度工作流触发时间
        "weekly_alignment_day": "Mon",  # 周度对齐日
        "weekly_alignment_time": "09:00",
        "weekly_review_day": "Fri",     # 周末复盘日
        "weekly_review_time": "17:00",
    },
}

# ==========================================
# Celery + Redis 配置
# ==========================================
CELERY_CONFIG = {
    "broker_url": os.getenv("CELERY_BROKER", "redis://localhost:6379/1"),
    "result_backend": os.getenv("CELERY_BACKEND", "redis://localhost:6379/2"),
    "task_track_started": True,
    "task_time_limit": 600,  # 10 分钟
    "task_soft_time_limit": 540,  # 9 分钟
    "worker_prefetch_multiplier": 1,
    "worker_max_tasks_per_child": 50,
}

REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "db": int(os.getenv("REDIS_DB", "0")),
    "password": os.getenv("REDIS_PASSWORD", ""),
    "url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
}

SCHEDULER_CONFIG = {
    "timezone": "Asia/Shanghai",
    "jobs": [
        {"id": "morning_intelligence", "cron": "0 6 * * *", "name": "晨间情报扫描"},
        {"id": "content_execution", "cron": "0 10 * * *", "name": "内容执行"},
        {"id": "evening_monitor", "cron": "0 18 * * *", "name": "晚间数据监控"},
        {"id": "weekly_alignment", "cron": "0 9 * * 1", "name": "周度对齐"},
        {"id": "weekly_review", "cron": "0 17 * * 5", "name": "周末复盘"},
    ],
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

    # 存量战场（从竞品抢客户）— 第三方跨境支付平台
    "PingPong": "stock",
    "pingpong": "stock",
    "万里汇（WorldFirst）": "stock",
    "万里汇": "stock",
    "WorldFirst": "stock",
    "XTransfer": "stock",
    "xtransfer": "stock",
    "连连支付（LianLian）": "stock",
    "连连支付": "stock",
    "光子易（PhotonPay）": "stock",
    "光子易": "stock",
    "空中云汇（Airwallex）": "stock",
    "空中云汇": "stock",
    "派安盈（Payoneer）": "stock",
    "Payoneer": "stock",
    "收款易（Skyee）": "stock",
    "Skyee": "stock",
    "iPayLinks": "stock",
    "PanPay": "stock",
    "寻汇（Sunrate）": "stock",
    "Sunrate": "stock",
    "结行国际（CoGoLinks）": "stock",
    "CoGoLinks": "stock",
    "义支付（YiwuPay）": "stock",
    "Qbit（量子跨境）": "stock",
    "Qbit": "stock",
    "易宝支付（YeePay）": "stock",
    "珊瑚跨境（Coralglobal）": "stock",
    "拓拓（TikStar Pay）": "stock",
    "PayPal": "stock",
    "Stripe": "stock",
    "Wise（TransferWise）": "stock",
    "Wise": "stock",
    "dLocal": "stock",

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
    "service": "服务贸易（B2B）",
    "b2s": "1688直采（B2S）",
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

# 当前渠道选项（全量第三方跨境收款平台）
CHANNEL_OPTIONS = [
    # —— 银行渠道 ——
    "银行电汇",
    # —— 第三方跨境支付平台 ——
    "PingPong",
    "万里汇（WorldFirst）",
    "XTransfer",
    "连连支付（LianLian）",
    "光子易（PhotonPay）",
    "空中云汇（Airwallex）",
    "派安盈（Payoneer）",
    "收款易（Skyee）",
    "iPayLinks",
    "PanPay",
    "寻汇（Sunrate）",
    "结行国际（CoGoLinks）",
    "义支付（YiwuPay）",
    "Qbit（量子跨境）",
    "易宝支付（YeePay）",
    "珊瑚跨境（Coralglobal）",
    "拓拓（TikStar Pay）",
    # —— 国际支付平台 ——
    "PayPal",
    "Stripe",
    "Wise（TransferWise）",
    "dLocal",
    # —— 未选定 ——
    "未选定",
]

# 客户阶段选项
CUSTOMER_STAGE_OPTIONS = [
    "初次接触",
    "已报价",
    "试用中",
    "已签约",
    "已流失",
]

# 企业规模选项
COMPANY_SIZE_OPTIONS = [
    "1-10人",
    "11-50人",
    "51-200人",
    "200人以上",
]

# 币种选项
CURRENCY_OPTIONS = [
    "THB", "MYR", "PHP", "IDR", "VND", "HKD", "EUR", "USD", "CNY",
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
