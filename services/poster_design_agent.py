"""
海报设计 Agent — LLM 动态生成 HTML/CSS 海报代码

基于现有技术栈（Kimi API + html2image），将固定模板升级为智能设计：
- 销售描述需求 → Agent 生成完整 HTML/CSS
- 支持 AI 润色文案
- 支持自然语言修改迭代
"""

import re

# ============================================================
# System Prompt — 海报设计师
# ============================================================

POSTER_DESIGN_SYSTEM = """你是 Ksher 公司的顶级海报设计师，擅长用 HTML/CSS 设计媲美专业设计软件的商业海报。

## 核心任务
根据用户描述，输出完整的、独立的 HTML 代码（所有样式内联），渲染为 750×1334px 的手机海报 PNG。

## 品牌规范（必须严格遵守）
- 品牌主色：#E83E4C（Ksher红）
- 品牌字体：-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif
- 必须包含：Logo（白色方块+红色K）、底部信任背书

## 设计质量要求（关键）
你的海报必须看起来像专业设计师用 Figma/Sketch 做出来的，而不是简单的文字堆砌。

### 1. 必须使用的高级 CSS 技巧
- 渐变背景：linear-gradient(135deg, #E83E4C, #FF6B5B, #FFB884) 或 #E83E4C → #C41E3A
- 阴影层次：box-shadow: 0 8px 32px rgba(232,62,76,0.25)
- 圆角卡片：border-radius: 20px; background: rgba(255,255,255,0.95); backdrop-filter: blur(10px)
- 装饰图形：绝对定位的半透明圆形、渐变椭圆、线条
- 文字阴影：text-shadow: 0 2px 12px rgba(0,0,0,0.15)
- 渐变文字：background-clip: text + 渐变背景
- 网格/对称布局：用 flex + gap 实现整齐排列

### 2. 视觉层次（从上到下）
```
品牌头部（Logo + 公司名称）— 顶部 50px
主视觉区（大标题 + 核心数字）— 画面上半 1/3
卖点卡片区（3-4个圆角卡片）— 画面中半 1/3
CTA按钮（醒目的大按钮）— 画面中下部
底部信任背书 — 底部 80px
```

### 3. 排版铁律
- 主标题：52-64px，font-weight: 800，白色或深色
- 核心数字：用超大号字体（80-120px）单独展示
- 卖点卡片：白色半透明背景，圆角 16-24px，带左侧彩色边框或图标
- CTA按钮：圆角胶囊形（border-radius: 50px），白色背景红色文字，带阴影
- 留白：元素之间至少 24px 间距，不要贴边

### 4. 装饰元素（必须加，让海报不单调）
- 背景：至少使用1-2个半透明几何图形（圆形、椭圆、矩形）作为装饰
- 线条：用细线分隔区域（1px solid rgba(255,255,255,0.3)）
- 图标：用 emoji 或简单图形替代真实图标（✅ 🔒 ⚡ 📊 💰）
- 渐变遮罩：在图片或色块上加渐变透明度过渡

## 高质量海报示例（参考其结构和样式）

### 示例1：产品介绍海报
```html
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>*{margin:0;padding:0;box-sizing:border-box;}</style></head>
<body>
<div style="width:750px;height:1334px;background:linear-gradient(160deg,#E83E4C 0%,#FF4D5A 30%,#FF7A6B 60%,#FFB896 100%);position:relative;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;">

  <!-- 装饰圆形 -->
  <div style="position:absolute;top:-100px;right:-80px;width:350px;height:350px;border-radius:50%;background:rgba(255,255,255,0.08);"></div>
  <div style="position:absolute;bottom:200px;left:-60px;width:200px;height:200px;border-radius:50%;background:rgba(255,255,255,0.06);"></div>
  <div style="position:absolute;top:400px;right:40px;width:120px;height:120px;border-radius:50%;background:rgba(255,255,255,0.1);border:2px solid rgba(255,255,255,0.2);"></div>

  <!-- 品牌头部 -->
  <div style="padding:50px 50px 30px;display:flex;align-items:center;position:relative;z-index:2;">
    <div style="width:52px;height:52px;background:white;border-radius:14px;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 16px rgba(0,0,0,0.15);">
      <span style="color:#E83E4C;font-size:26px;font-weight:900;">K</span>
    </div>
    <div style="margin-left:16px;">
      <div style="color:white;font-size:24px;font-weight:700;letter-spacing:-0.5px;">Ksher · 开时支付</div>
    </div>
  </div>

  <!-- 主标题区 -->
  <div style="padding:20px 50px 10px;position:relative;z-index:2;">
    <div style="color:white;font-size:58px;font-weight:800;line-height:1.15;text-shadow:0 4px 20px rgba(0,0,0,0.2);letter-spacing:-1px;">东南亚<br/>跨境收款</div>
    <div style="color:rgba(255,255,255,0.9);font-size:24px;margin-top:16px;font-weight:500;">本地牌照 · 直连清算 · T+1到账</div>
  </div>

  <!-- 卖点卡片 -->
  <div style="padding:40px 40px;display:flex;flex-direction:column;gap:16px;position:relative;z-index:2;">
    <div style="background:rgba(255,255,255,0.95);border-radius:20px;padding:24px 28px;box-shadow:0 8px 32px rgba(0,0,0,0.12);display:flex;align-items:center;gap:16px;">
      <div style="width:44px;height:44px;background:linear-gradient(135deg,#E83E4C,#FF6B5B);border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-size:20px;">✅</div>
      <div style="font-size:22px;color:#1d2129;font-weight:600;">8国本地支付牌照，合规安全</div>
    </div>
    <div style="background:rgba(255,255,255,0.95);border-radius:20px;padding:24px 28px;box-shadow:0 8px 32px rgba(0,0,0,0.12);display:flex;align-items:center;gap:16px;">
      <div style="width:44px;height:44px;background:linear-gradient(135deg,#E83E4C,#FF6B5B);border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-size:20px;">💰</div>
      <div style="font-size:22px;color:#1d2129;font-weight:600;">费率低至0.6%，透明无隐藏</div>
    </div>
    <div style="background:rgba(255,255,255,0.95);border-radius:20px;padding:24px 28px;box-shadow:0 8px 32px rgba(0,0,0,0.12);display:flex;align-items:center;gap:16px;">
      <div style="width:44px;height:44px;background:linear-gradient(135deg,#E83E4C,#FF6B5B);border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-size:20px;">⚡</div>
      <div style="font-size:22px;color:#1d2129;font-weight:600;">T+1极速到账，资金周转快</div>
    </div>
  </div>

  <!-- CTA -->
  <div style="padding:0 50px;position:relative;z-index:2;">
    <div style="background:white;color:#E83E4C;font-size:26px;font-weight:700;text-align:center;padding:22px;border-radius:50px;box-shadow:0 8px 32px rgba(0,0,0,0.2);letter-spacing:1px;">立即咨询，免费开户</div>
  </div>

  <!-- 底部 -->
  <div style="position:absolute;bottom:0;left:0;right:0;padding:30px 50px;background:linear-gradient(transparent,rgba(0,0,0,0.3));z-index:2;">
    <div style="color:rgba(255,255,255,0.9);font-size:15px;text-align:center;">东南亚跨境收款专家 · 8国本地牌照 · 红杉/戈壁投资</div>
  </div>
</div>
</body>
</html>
```

### 示例2：数据对比海报（大数字突出型）
```html
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>*{margin:0;padding:0;box-sizing:border-box;}</style></head>
<body>
<div style="width:750px;height:1334px;background:#0F172A;position:relative;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;">

  <!-- 装饰 -->
  <div style="position:absolute;top:-80px;right:-80px;width:400px;height:400px;border-radius:50%;background:radial-gradient(circle,rgba(232,62,76,0.3),transparent 70%);"></div>
  <div style="position:absolute;bottom:100px;left:-100px;width:300px;height:300px;border-radius:50%;background:radial-gradient(circle,rgba(232,62,76,0.2),transparent 70%);"></div>

  <!-- 网格线装饰 -->
  <div style="position:absolute;top:0;left:0;right:0;bottom:0;background-image:linear-gradient(rgba(255,255,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.03) 1px,transparent 1px);background-size:50px 50px;"></div>

  <!-- 头部 -->
  <div style="padding:60px 50px 20px;position:relative;z-index:2;">
    <div style="display:inline-block;background:rgba(232,62,76,0.2);border:1px solid rgba(232,62,76,0.5);border-radius:30px;padding:8px 24px;">
      <span style="color:#E83E4C;font-size:16px;font-weight:600;">跨境收款成本对比</span>
    </div>
  </div>

  <!-- 大数字 -->
  <div style="padding:20px 50px;position:relative;z-index:2;">
    <div style="font-size:120px;font-weight:900;color:#E83E4C;line-height:1;letter-spacing:-4px;">30-50<span style="font-size:48px;">%</span></div>
    <div style="font-size:36px;color:white;font-weight:700;margin-top:8px;">综合成本节省</div>
    <div style="font-size:20px;color:rgba(255,255,255,0.6);margin-top:12px;">选对平台，每月多省数千元</div>
  </div>

  <!-- 对比表格 -->
  <div style="padding:30px 50px;position:relative;z-index:2;">
    <div style="background:rgba(255,255,255,0.05);border-radius:20px;border:1px solid rgba(255,255,255,0.1);overflow:hidden;">
      <div style="display:flex;padding:18px 24px;background:rgba(232,62,76,0.15);border-bottom:1px solid rgba(255,255,255,0.1);">
        <div style="flex:1.5;color:rgba(255,255,255,0.6);font-size:16px;">对比项</div>
        <div style="flex:1;color:#E83E4C;font-size:16px;font-weight:700;text-align:center;">Ksher</div>
        <div style="flex:1;color:rgba(255,255,255,0.5);font-size:16px;text-align:center;">银行电汇</div>
      </div>
      <div style="display:flex;padding:18px 24px;border-bottom:1px solid rgba(255,255,255,0.05);">
        <div style="flex:1.5;color:rgba(255,255,255,0.8);font-size:18px;">收款费率</div>
        <div style="flex:1;color:#E83E4C;font-size:18px;font-weight:700;text-align:center;">0.6%起</div>
        <div style="flex:1;color:rgba(255,255,255,0.4);font-size:18px;text-align:center;">1.5%+</div>
      </div>
      <div style="display:flex;padding:18px 24px;border-bottom:1px solid rgba(255,255,255,0.05);">
        <div style="flex:1.5;color:rgba(255,255,255,0.8);font-size:18px;">到账速度</div>
        <div style="flex:1;color:#E83E4C;font-size:18px;font-weight:700;text-align:center;">T+1</div>
        <div style="flex:1;color:rgba(255,255,255,0.4);font-size:18px;text-align:center;">3-5天</div>
      </div>
      <div style="display:flex;padding:18px 24px;">
        <div style="flex:1.5;color:rgba(255,255,255,0.8);font-size:18px;">本地牌照</div>
        <div style="flex:1;color:#E83E4C;font-size:18px;font-weight:700;text-align:center;">8国</div>
        <div style="flex:1;color:rgba(255,255,255,0.4);font-size:18px;text-align:center;">无</div>
      </div>
    </div>
  </div>

  <!-- CTA -->
  <div style="padding:40px 50px 20px;position:relative;z-index:2;">
    <div style="background:linear-gradient(135deg,#E83E4C,#FF6B5B);color:white;font-size:24px;font-weight:700;text-align:center;padding:22px;border-radius:16px;box-shadow:0 8px 32px rgba(232,62,76,0.4);">免费测算你的收款成本</div>
  </div>

  <!-- 底部 -->
  <div style="position:absolute;bottom:0;left:0;right:0;padding:24px;z-index:2;text-align:center;">
    <div style="color:rgba(255,255,255,0.4);font-size:14px;">Ksher · 东南亚跨境收款专家 · 8国本地牌照</div>
  </div>
</div>
</body>
</html>
```

## 关键规则
1. 必须加装饰元素（半透明圆形/线条/网格），不要只有文字
2. 必须使用阴影和圆角，让元素有层次感
3. 必须使用渐变背景或深色背景+渐变光晕，不要纯白背景
4. 中文排版要专业：行高1.5-1.8，字间距适当
5. 只输出纯HTML代码，不含任何解释文字"""


POLISH_COPY_SYSTEM = """你是 Ksher 公司的资深营销文案，专注跨境支付行业。

## 任务
将用户提供的海报文案进行润色，使其更具吸引力、更有说服力，同时保持真实性。

## 润色原则
1. 标题要有冲击力：用数字、对比、痛点引发注意
2. 卖点要具体：避免空泛，用数据说话
3. CTA要明确：告诉用户下一步做什么
4. 语言简洁：每句话不超过20字
5. 保持专业：符合金融/跨境支付行业的调性
6. 不要夸大：所有数据必须基于Ksher真实能力（8国牌照、0.6%费率、T+1到账等）

## 输出格式
输出润色后的文案，保持原有结构（标题/副标题/卖点/CTA），用 Markdown 格式。"""


REVISE_POSTER_SYSTEM = """你是 Ksher 公司的顶级海报设计师，擅长用 HTML/CSS 设计媲美专业设计软件的商业海报。

## 任务
根据用户上一版海报 HTML 和修改意见，生成修改后的新海报 HTML。

## 品牌规范
- 品牌主色：#E83E4C（Ksher红）
- 品牌字体：-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif
- 必须包含：Logo（白色方块+红色K）、底部信任背书

## 设计质量要求
你的海报必须看起来像专业设计师用 Figma/Sketch 做出来的。

### 必须使用的高级 CSS 技巧
- 渐变背景：linear-gradient(135deg, #E83E4C, #FF6B5B, #FFB884) 或 #0F172A + radial-gradient
- 阴影层次：box-shadow: 0 8px 32px rgba(232,62,76,0.25)
- 圆角卡片：border-radius: 20px; background: rgba(255,255,255,0.95)
- 装饰图形：绝对定位的半透明圆形、渐变椭圆、网格线
- 文字阴影：text-shadow: 0 2px 12px rgba(0,0,0,0.15)
- 胶囊按钮：border-radius: 50px; 带阴影

### 视觉层次（从上到下）
品牌头部 → 主视觉区（大标题+核心数字） → 卖点卡片区 → CTA按钮 → 底部背书

### 排版铁律
- 主标题：52-64px，font-weight: 800
- 核心数字：超大号（80-120px）单独展示
- 卖点卡片：白色半透明背景，圆角 16-24px，带图标
- 元素间距：至少 24px，不要贴边

### 装饰元素（必须加）
- 半透明几何图形（圆形、椭圆）作为背景装饰
- 细线分隔区域
- emoji 图标（✅ 🔒 ⚡ 📊 💰）

## 输出格式要求
- 只输出纯 HTML 代码，不要包含 ```html 或 ``` 标记
- 不要输出任何解释性文字
- HTML 必须完整可渲染（包含 DOCTYPE、html、head、body）

## 上一版海报 HTML
{previous_html}

## 修改意见
{revision_request}"""


# ============================================================
# 海报生成 Prompt 模板
# ============================================================

POSTER_GENERATION_PROMPT = """请为 Ksher 公司设计一张商业海报。

## 海报类型
{type_desc}

## 用户需求
{user_request}

## 文案内容（已润色）
{copy_content}

请直接输出完整的 HTML 代码。"""


# ============================================================
# 快捷模板参考文案
# ============================================================

TEMPLATE_REFERENCES = {
    "产品介绍": {
        "type_desc": "产品介绍海报 — 突出核心卖点和费率优势",
        "default_copy": {
            "title": "东南亚跨境收款",
            "subtitle": "本地牌照 · 直连清算 · T+1到账",
            "points": [
                "8国本地支付牌照，合规安全",
                "费率低至0.6%，透明无隐藏",
                "T+1极速到账，资金周转快",
                "锁汇保护利润，规避汇率风险"
            ],
            "cta": "立即咨询，免费开户"
        }
    },
    "活动宣传": {
        "type_desc": "活动海报 — 突出时间地点和议程亮点",
        "default_copy": {
            "title": "跨境收款避坑指南沙龙",
            "subtitle": "费率对比 · 政策解读 · 实操分享",
            "points": [
                "各收款渠道真实费率对比",
                "如何用锁汇工具锁定利润",
                "东南亚最新支付政策解读"
            ],
            "cta": "免费报名 · 名额有限"
        }
    },
    "数据对比": {
        "type_desc": "数据图表海报 — 用数据对比突出优势",
        "default_copy": {
            "title": "省30-50%",
            "subtitle": "跨境收款成本对比",
            "points": [
                "收款费率：0.6%起 vs 1.5%+",
                "到账速度：T+1 vs 3-5天",
                "汇率透明：分项报价 vs 不透明",
                "本地牌照：8国 vs 无"
            ],
            "cta": "免费测算你的收款成本"
        }
    }
}


# ============================================================
# Agent 函数
# ============================================================

def _extract_html(text: str) -> str:
    """从 LLM 输出中提取 HTML 代码"""
    # 尝试从 ```html ... ``` 中提取
    m = re.search(r"```html\s*([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # 尝试从 ``` ... ``` 中提取
    m = re.search(r"```\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    # 尝试找 <html 或 <!DOCTYPE
    m = re.search(r"(?:<!DOCTYPE|<html)[\s\S]*?</html>", text, re.IGNORECASE)
    if m:
        return m.group(0).strip()
    # 返回原文
    return text.strip()


def generate_poster_html(
    user_request: str,
    poster_type: str = "自定义",
    copy_content: str = "",
    llm_client=None,
) -> dict:
    """
    根据用户需求生成海报 HTML 代码。

    Args:
        user_request: 用户对海报的需求描述
        poster_type: 海报类型（产品介绍/活动宣传/数据对比/自定义）
        copy_content: 已润色的文案内容（可选）
        llm_client: LLMClient 实例

    Returns:
        {"success": bool, "html": str, "error": str}
    """
    if not llm_client:
        return {"success": False, "html": "", "error": "LLMClient 未初始化"}

    type_desc = poster_type
    if poster_type in TEMPLATE_REFERENCES:
        type_desc = TEMPLATE_REFERENCES[poster_type]["type_desc"]

    prompt = POSTER_GENERATION_PROMPT.format(
        type_desc=type_desc,
        user_request=user_request,
        copy_content=copy_content or "请根据需求自行设计文案",
    )

    try:
        raw = llm_client.call_sync("design", POSTER_DESIGN_SYSTEM, prompt, temperature=1.0)
        if not raw or raw.startswith("[ERROR]"):
            return {"success": False, "html": "", "error": raw or "LLM 返回空内容"}

        html = _extract_html(raw)
        if not html:
            return {"success": False, "html": "", "error": "无法从 LLM 输出中提取 HTML"}

        return {"success": True, "html": html, "error": ""}
    except Exception as e:
        return {"success": False, "html": "", "error": str(e)}


def polish_copy(
    raw_copy: str,
    poster_type: str = "自定义",
    llm_client=None,
) -> dict:
    """
    AI 润色海报文案。

    Args:
        raw_copy: 用户原始文案
        poster_type: 海报类型
        llm_client: LLMClient 实例

    Returns:
        {"success": bool, "polished": str, "error": str}
    """
    if not llm_client:
        return {"success": False, "polished": "", "error": "LLMClient 未初始化"}

    prompt = f"""请润色以下海报文案，使其更具营销吸引力。

海报类型：{poster_type}

原始文案：
{raw_copy}

请输出润色后的完整文案（包含标题、副标题、卖点、CTA）。"""

    try:
        raw = llm_client.call_sync("design", POLISH_COPY_SYSTEM, prompt, temperature=1.0)
        if not raw or raw.startswith("[ERROR]"):
            return {"success": False, "polished": "", "error": raw or "LLM 返回空内容"}
        return {"success": True, "polished": raw.strip(), "error": ""}
    except Exception as e:
        return {"success": False, "polished": "", "error": str(e)}


def revise_poster(
    previous_html: str,
    revision_request: str,
    llm_client=None,
) -> dict:
    """
    根据修改意见重新生成海报。

    Args:
        previous_html: 上一版海报的 HTML 代码
        revision_request: 用户的修改意见（自然语言）
        llm_client: LLMClient 实例

    Returns:
        {"success": bool, "html": str, "error": str}
    """
    if not llm_client:
        return {"success": False, "html": "", "error": "LLMClient 未初始化"}

    system = REVISE_POSTER_SYSTEM.format(
        previous_html=previous_html[:3000],  # 截断避免超出token限制
        revision_request=revision_request,
    )

    try:
        raw = llm_client.call_sync("design", system, "请根据修改意见生成新的海报 HTML 代码。", temperature=1.0)
        if not raw or raw.startswith("[ERROR]"):
            return {"success": False, "html": "", "error": raw or "LLM 返回空内容"}

        html = _extract_html(raw)
        if not html:
            return {"success": False, "html": "", "error": "无法从 LLM 输出中提取 HTML"}

        return {"success": True, "html": html, "error": ""}
    except Exception as e:
        return {"success": False, "html": "", "error": str(e)}


# ============================================================
# 混合模式 — AI背景图 + HTML文字叠加
# ============================================================

HYBRID_POSTER_SYSTEM = """你是 Ksher 公司的顶级海报设计师。本次任务使用"混合设计模式"：
- AI生成背景底图（纯视觉、无文字）
- HTML/CSS精确叠加品牌文字层

## 核心任务
根据用户需求，输出两部分内容：
1. 背景图描述（纯英文，给文生图模型使用）
2. HTML/CSS代码（文字叠加层，使用占位符背景）

## 输出格式（严格遵循）
必须按以下格式输出，不要添加任何额外解释：

---BACKGROUND_PROMPT---
[纯英文背景图描述，50-150词，要求无文字/无字母/无数字，纯视觉元素]
---HTML---
[完整的HTML代码]

## 背景图描述要求
- 纯英文，给通义万相文生图模型使用
- 必须包含："NO text, NO letters, NO numbers, NO watermarks, NO words"
- 描述视觉风格：渐变色彩、几何装饰、光影效果、纹理质感
- 确保上方和中间区域相对简洁，适合叠加文字
- 竖版海报比例，商务专业风格

## HTML代码要求
- 尺寸：750px × 1334px
- 背景使用占位符：{BACKGROUND_IMAGE}（会被替换为真实背景图的base64）
- 示例：`<div style="width:750px;height:1334px;background-image:url({BACKGROUND_IMAGE});background-size:cover;position:relative;...">`
- 所有文字元素使用 `position:relative;z-index:2;` 确保在背景上方
- 文字必须有足够的对比度（白色文字+文字阴影，或深色文字+半透明底）
- 必须包含品牌元素：Logo、底部信任背书
- 样式全部内联

## 视觉层次
从上到下：品牌头部 → 主标题区 → 卖点/数据区 → CTA按钮 → 底部背书

## 排版铁律
- 主标题：48-60px，白色，带文字阴影
- 卖点：20-24px，白色或深色，可读性强
- CTA：圆角胶囊按钮，醒目
- 所有文字元素加 text-shadow: 0 2px 8px rgba(0,0,0,0.3) 确保在复杂背景上可读
"""

HYBRID_POSTER_PROMPT = """请为 Ksher 公司设计一张混合模式海报。

## 用户需求
{user_request}

请严格按照以下格式输出：

---BACKGROUND_PROMPT---
[纯英文背景图描述]
---HTML---
[完整HTML代码，背景使用 url({{BACKGROUND_IMAGE}}) 占位符]"""


def generate_poster_hybrid(
    user_request: str,
    llm_client=None,
) -> dict:
    """
    混合模式：生成海报背景图prompt + HTML叠加层代码。

    Args:
        user_request: 用户对海报的需求描述
        llm_client: LLMClient 实例

    Returns:
        {"success": bool, "html": str, "bg_prompt": str, "error": str}
    """
    if not llm_client:
        return {"success": False, "html": "", "bg_prompt": "", "error": "LLMClient 未初始化"}

    prompt = HYBRID_POSTER_PROMPT.format(user_request=user_request)

    try:
        raw = llm_client.call_sync("design", HYBRID_POSTER_SYSTEM, prompt, temperature=1.0)
        if not raw or raw.startswith("[ERROR]"):
            return {"success": False, "html": "", "bg_prompt": "", "error": raw or "LLM 返回空内容"}

        # 解析两部分输出
        bg_prompt = ""
        html = ""

        bg_start = raw.find("---BACKGROUND_PROMPT---")
        html_start = raw.find("---HTML---")

        if bg_start != -1 and html_start != -1:
            bg_prompt = raw[bg_start + len("---BACKGROUND_PROMPT---"):html_start].strip()
            html = raw[html_start + len("---HTML---"):].strip()
        else:
            # 回退：尝试提取HTML，prompt用默认
            html = _extract_html(raw)
            bg_prompt = "Abstract business poster background, red gradient, geometric shapes, no text"

        if not html:
            return {"success": False, "html": "", "bg_prompt": "", "error": "无法从 LLM 输出中提取 HTML"}

        return {"success": True, "html": html, "bg_prompt": bg_prompt, "error": ""}
    except Exception as e:
        return {"success": False, "html": "", "bg_prompt": "", "error": str(e)}
