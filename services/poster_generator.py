"""
海报生成器 — Pillow 动态生成 PNG 海报

支持：选择国家 + 业务类型 → 实时生成 Ksher 品牌风格海报
尺寸：750 × 1334 px（手机竖屏，可自适应高度）
"""

import io
import os
from typing import Optional

from PIL import Image, ImageColor, ImageDraw, ImageFont

from config import BASE_DIR, COUNTRY_OPTIONS


# ============================================================
# Ksher 品牌色彩
# ============================================================
BRAND_RED = "#E60012"
BRAND_RED_LIGHT = "#FF4757"
CARD_BG = "#FFFFFF"
TEXT_DARK = "#333333"
TEXT_GRAY = "#666666"
TEXT_LIGHT = "#999999"

# 国家主题色映射
COUNTRY_COLORS = {
    "TH": ("#FF6B5B", "#FFB884"),   # 泰国 - 橙红渐变
    "MY": ("#FF6B5B", "#FFB884"),   # 马来西亚
    "PH": ("#FF6B5B", "#FFB884"),   # 菲律宾
    "ID": ("#FF6B5B", "#FFB884"),   # 印尼
    "VN": ("#FF6B5B", "#FFB884"),   # 越南
    "SG": ("#FF6B5B", "#FFB884"),   # 新加坡
    "HK": ("#FF6B5B", "#FFB884"),   # 香港
}

# 业务类型配置
BUSINESS_TYPES = {
    "b2b": {
        "title": "B2B 货物贸易收款",
        "subtitle": "本地VA账户 · 直接清算 · T+1到账",
        "selling_points": [
            ("本地VA账户", "当地银行同名账户，买家信任度高"),
            ("直接清算", "无中间行，全额到账"),
            ("T+1到账", "最快次日到账，资金周转快"),
        ],
        "fee_info": "收款费率 0.6% - 1.0%",
        "flow_steps": ["注册开户", "提交KYC", "获取VA", "发给买家", "买家打款", "确认到账"],
    },
    "b2c": {
        "title": "B2C 跨境电商收款",
        "subtitle": "Shopee / Lazada / TikTok 本土店收款",
        "selling_points": [
            ("本土店收款", "支持东南亚本土店THB/MYR/PHP等"),
            ("极速到账", "T+0/T+1到账，资金周转快"),
            ("合规持牌", "多国央行牌照，资金安全有保障"),
        ],
        "fee_info": "收款费率 0.8% - 1.2%",
        "flow_steps": ["注册账号", "申请VA", "绑定店铺", "买家下单", "平台结算", "提现结汇"],
    },
    "service": {
        "title": "服务贸易收款",
        "subtitle": "物流 / 广告 / SaaS / 技术服务收款",
        "selling_points": [
            ("多场景覆盖", "物流、广告、SaaS、技术服务"),
            ("合规申报", "完税结汇，正规入账"),
            ("7×24服务", "专属客户经理全程对接"),
        ],
        "fee_info": "收款费率 0.6% - 1.0%",
        "flow_steps": ["注册开户", "选择场景", "提交合同", "获取账户", "发起收款", "结汇提现"],
    },
}


# ============================================================
# 字体加载
# ============================================================
def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """加载字体（优先系统字体，fallback 到默认）"""
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=0 if not bold else 1)
            except Exception:
                continue
    return ImageFont.load_default()


# ============================================================
# 绘制辅助函数
# ============================================================
def _draw_gradient(draw: ImageDraw.Draw, width: int, height: int, color1: str, color2: str):
    """绘制线性渐变背景"""
    c1 = ImageColor.getrgb(color1)
    c2 = ImageColor.getrgb(color2)
    for y in range(height):
        ratio = y / height
        r = int(c1[0] + (c2[0] - c1[0]) * ratio)
        g = int(c1[1] + (c2[1] - c1[1]) * ratio)
        b = int(c1[2] + (c2[2] - c1[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def _draw_rounded_rect(draw: ImageDraw.Draw, xy, radius: int, fill, outline=None, width=1):
    """绘制圆角矩形"""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _text_size(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont):
    """获取文字尺寸"""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


# ============================================================
# 主生成函数
# ============================================================
def generate_poster(country_code: str, business_type: str, custom_title: str = "") -> Optional[bytes]:
    """
    生成 Ksher 品牌风格海报 PNG。

    Args:
        country_code: 国家代码 (TH, MY, PH, ID, VN, SG, HK)
        business_type: 业务类型 (b2b, b2c, service)
        custom_title: 自定义标题（可选）

    Returns:
        PNG 图片 bytes，失败返回 None
    """
    try:
        country_name = COUNTRY_OPTIONS.get(country_code, "东南亚")
        biz = BUSINESS_TYPES.get(business_type, BUSINESS_TYPES["b2b"])
        colors = COUNTRY_COLORS.get(country_code, ("#FF6B5B", "#FFB884"))

        # 画布尺寸
        W, H = 750, 1400
        img = Image.new("RGB", (W, H), "#FF6B5B")
        draw = ImageDraw.Draw(img)

        # ---- 渐变背景 ----
        _draw_gradient(draw, W, H, colors[0], colors[1])

        # 加载字体
        font_brand = _get_font(32, bold=True)
        font_title = _get_font(44, bold=True)
        font_subtitle = _get_font(22)
        font_card_title = _get_font(24, bold=True)
        font_card_desc = _get_font(18)
        font_tag = _get_font(16)
        font_footer = _get_font(20, bold=True)
        font_small = _get_font(14)

        # ---- 品牌头部 ----
        y = 30
        draw.text((40, y), "Ksher", fill="white", font=font_brand)
        tw, th = _text_size(draw, "Ksher", font_brand)
        draw.text((40 + tw + 8, y + 4), "开时支付", fill=(255, 255, 255, 220), font=_get_font(22))

        # ---- 主标题区 ----
        y = 90
        title = custom_title if custom_title else f"{country_name}{biz['title']}"
        draw.text((W // 2, y), title, fill="white", font=font_title, anchor="mm")

        y += 60
        draw.text((W // 2, y), biz["subtitle"], fill=(255, 255, 255, 230), font=font_subtitle, anchor="mm")

        # ---- 核心卖点卡片 ----
        y = 180
        card_margin = 30
        card_width = W - card_margin * 2
        card_padding = 20
        card_radius = 12

        for i, (sp_title, sp_desc) in enumerate(biz["selling_points"]):
            # 计算卡片高度
            title_h = _text_size(draw, sp_title, font_card_title)[1]
            desc_h = _text_size(draw, sp_desc, font_card_desc)[1]
            card_height = card_padding * 2 + title_h + 8 + desc_h

            # 白色卡片背景
            _draw_rounded_rect(
                draw,
                (card_margin, y, card_margin + card_width, y + card_height),
                card_radius,
                fill=CARD_BG,
            )

            # 左侧红色竖条
            draw.rounded_rectangle(
                (card_margin + 12, y + 15, card_margin + 16, y + card_height - 15),
                radius=2,
                fill=BRAND_RED,
            )

            # 卖点标题
            draw.text((card_margin + 28, y + card_padding), sp_title, fill=TEXT_DARK, font=font_card_title)

            # 卖点描述
            draw.text(
                (card_margin + 28, y + card_padding + title_h + 8),
                sp_desc,
                fill=TEXT_GRAY,
                font=font_card_desc,
            )

            y += card_height + 12

        # ---- 费率信息 ----
        y += 10
        fee_card_h = 60
        _draw_rounded_rect(
            draw,
            (card_margin, y, card_margin + card_width, y + fee_card_h),
            card_radius,
            fill=CARD_BG,
        )
        draw.text(
            (W // 2, y + fee_card_h // 2),
            biz["fee_info"],
            fill=BRAND_RED,
            font=_get_font(22, bold=True),
            anchor="mm",
        )

        # ---- 流程步骤 ----
        y += fee_card_h + 20
        draw.text((40, y), "开户流程", fill="white", font=_get_font(24, bold=True))
        y += 40

        step_margin = 30
        step_w = (W - step_margin * 2 - 15 * 2) // 3
        step_h = 70

        for idx, step in enumerate(biz["flow_steps"][:6]):
            row = idx // 3
            col = idx % 3
            sx = step_margin + col * (step_w + 15)
            sy = y + row * (step_h + 12)

            # 步骤卡片
            _draw_rounded_rect(
                draw,
                (sx, sy, sx + step_w, sy + step_h),
                8,
                fill=(255, 255, 255, 230),
            )

            # 步骤编号
            num_size = 20
            draw.ellipse(
                (sx + 8, sy + 8, sx + 8 + num_size, sy + 8 + num_size),
                fill=BRAND_RED,
            )
            draw.text(
                (sx + 8 + num_size // 2, sy + 8 + num_size // 2),
                str(idx + 1),
                fill="white",
                font=font_small,
                anchor="mm",
            )

            # 步骤文字
            draw.text(
                (sx + step_w // 2, sy + step_h // 2 + 5),
                step,
                fill=TEXT_DARK,
                font=font_tag,
                anchor="mm",
            )

        y += ((len(biz["flow_steps"][:6]) + 2) // 3) * (step_h + 12) + 30

        # ---- 底部 CTA ----
        cta_h = 100
        _draw_rounded_rect(
            draw,
            (card_margin, y, card_margin + card_width, y + cta_h),
            card_radius,
            fill=BRAND_RED,
        )
        draw.text(
            (W // 2, y + cta_h // 2 - 8),
            "立即申请免费开户",
            fill="white",
            font=_get_font(26, bold=True),
            anchor="mm",
        )
        draw.text(
            (W // 2, y + cta_h // 2 + 18),
            "专属客户经理 1 对 1 服务",
            fill=(255, 255, 255, 200),
            font=font_tag,
            anchor="mm",
        )

        # ---- Footer ----
        y += cta_h + 30
        footer_h = H - y
        draw.rectangle((0, y, W, H), fill="white")

        # Slogan
        draw.text(
            (40, y + 25),
            "出海无难事",
            fill=BRAND_RED,
            font=_get_font(28, bold=True),
        )
        draw.text(
            (40, y + 58),
            "现在就开时",
            fill=BRAND_RED,
            font=_get_font(28, bold=True),
        )

        # 品牌信息
        draw.text(
            (W - 40, y + 30),
            "Ksher",
            fill=TEXT_DARK,
            font=_get_font(32, bold=True),
            anchor="ra",
        )
        draw.text(
            (W - 40, y + 65),
            "跨境收付，从此简单",
            fill=TEXT_GRAY,
            font=font_tag,
            anchor="ra",
        )

        # ---- 输出 ----
        buf = io.BytesIO()
        img.save(buf, format="PNG", quality=95)
        return buf.getvalue()

    except Exception as e:
        print(f"海报生成失败: {e}")
        return None


# ============================================================
# 预生成海报列表
# ============================================================
def get_prebuilt_posters() -> list[dict]:
    """获取预生成海报列表"""
    poster_dir = os.path.join(BASE_DIR, "assets", "posters")
    if not os.path.exists(poster_dir):
        return []

    posters = []
    mapping = {
        "company-intro": ("公司介绍", "Ksher 公司介绍"),
        "b2b-intro": ("B2B业务", "B2B 货物贸易业务介绍"),
        "b2c-intro": ("B2C业务", "B2C 跨境电商业务介绍"),
        "service-trade": ("服务贸易", "服务贸易收款综合版"),
        "thailand": ("泰国", "泰国本地收款方案"),
        "philippines": ("菲律宾", "菲律宾本地收款方案"),
        "malaysia": ("马来西亚", "马来西亚本地收款方案"),
        "indonesia": ("印尼", "印尼本地收款方案"),
        "vietnam": ("越南", "越南本地收款方案"),
        "singapore": ("新加坡", "新加坡全球账户"),
        "hongkong": ("香港", "香港全球账户"),
        "fundflow": ("资金链路", "资金链路图解"),
        "glossary": ("术语速查", "常用术语速查"),
        "pobo": ("POBO", "代理付款方案"),
        "operation": ("操作指南", "收款到提现完整流程"),
        "troubleshooting": ("排查清单", "常见问题排查"),
        "kaishidui": ("开时兑", "实时换汇/预约换汇"),
    }

    for filename in sorted(os.listdir(poster_dir)):
        if not filename.endswith(".png"):
            continue
        filepath = os.path.join(poster_dir, filename)

        # 解析文件名
        name_lower = filename.lower()
        category = "其他"
        display_name = filename.replace(".png", "").replace("-", " ")

        for key, (cat, disp) in mapping.items():
            if key in name_lower:
                category = cat
                display_name = disp
                break

        posters.append({
            "filename": filename,
            "path": filepath,
            "category": category,
            "display_name": display_name,
        })

    return posters
