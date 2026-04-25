"""
竞品知识库服务

基于 /竞对情报信息🔎/竞品分析报告/ 的12份竞品分析，
提供结构化竞品情报，供作战包生成和UI展示使用。

用法：
    from services.competitor_knowledge import get_competitor_by_channel, get_competitor_card
    info = get_competitor_by_channel("PingPong")
    card = get_competitor_card("PingPong")
"""

from typing import Optional


# ============================================================
# 竞品数据库（来源：竞品分析报告 00-11）
# ============================================================
COMPETITOR_DB = {
    "万里汇": {
        "name_en": "WorldFirst",
        "name_cn": "万里汇",
        "parent": "蚂蚁集团（2019年收购）",
        "founded": 2004,
        "hq": "伦敦/杭州",
        "scale": "150万+企业客户",
        "markets": "210+国家，30+全球办公室",
        "fee_rate": "B2B: 0%起；收款: 0.3%封顶",
        "settlement": "T+0同币种；T+1-2跨币种",
        "licenses": "60+全球支付牌照",
        "strengths": [
            "iResearch 2025市场份额第一",
            "蚂蚁生态深度整合（支付宝+1688合作）",
            "B2B 0%底价策略",
            "20+新兴市场币种支持",
        ],
        "weaknesses": [
            "依赖蚂蚁集团监管状态",
            "东南亚本地化不如专注型玩家",
            "费率结构不够透明",
        ],
        "ksher_advantages": [
            "东南亚本地牌照直连清算，到账更快",
            "费率模型透明：手续费+汇兑佣金分开报价",
            "本地化深度：7国本地团队服务",
            "锁汇工具更灵活（7-90天远期）",
        ],
        "threat_level": "中",
        "attack_angle": "万里汇全球覆盖广但东南亚不够深，Ksher在东南亚有本地牌照直连清算优势",
    },
    "XTransfer": {
        "name_en": "XTransfer",
        "name_cn": "夺畅网络",
        "parent": "",
        "founded": 2017,
        "hq": "上海",
        "scale": "B2B专注型",
        "markets": "200+国家，70%客户出口新兴市场",
        "fee_rate": "B2B: 0.4%封顶；收款免费",
        "settlement": "7×24小时结算",
        "licenses": "30+全球牌照（含中国MSB、马来MSB）",
        "strengths": [
            "B2B超专注（7-8年深耕）",
            "阿里/蚂蚁背景团队",
            "TradePilot LLM自研AI反洗钱",
            "非洲市场年增300%",
        ],
        "weaknesses": [
            "东南亚本地化不如Ksher",
            "品牌知名度低于PingPong",
            "偏B2B，不覆盖B2C电商",
        ],
        "ksher_advantages": [
            "东南亚本地牌照，不走中间行",
            "B2C+B2B双覆盖，客户场景更广",
            "到账速度T+0/T+1 vs XTransfer的标准流程",
            "本地化服务团队响应更快",
        ],
        "threat_level": "中",
        "attack_angle": "XTransfer B2B全球化但东南亚深度不够，Ksher本地牌照+T+0到账是核心差异",
    },
    "珊瑚跨境": {
        "name_en": "CoralGlobal",
        "name_cn": "珊瑚跨境",
        "parent": "工商银行背景",
        "founded": 2016,
        "hq": "杭州",
        "scale": "60万+跨境企业",
        "markets": "7个东南亚国家（核心），100+国家",
        "fee_rate": "0.3%-0.5%",
        "settlement": "24小时极速提现",
        "licenses": "央行支付牌照+美国MSB+英国EMI+东南亚本地牌照",
        "strengths": [
            "iResearch东南亚市场份额第一（26.3%）",
            "工商银行背景，信用背书强",
            "Lazada官方服务商",
            "e企达（花旗整合）+ 珊瑚海（供应链金融）",
        ],
        "weaknesses": [
            "费率透明度不如Ksher",
            "银行系风格，灵活性较低",
            "渠道政策不够公开",
        ],
        "ksher_advantages": [
            "费率更透明：手续费+汇兑分开报价 vs 银行系打包",
            "0.05%底价 vs 珊瑚0.3%起",
            "合作伙伴佣金政策更激进（40-50%分润）",
            "产品迭代更快，非银行系决策链",
        ],
        "threat_level": "高",
        "attack_angle": "珊瑚跨境是东南亚直接竞争对手，但费率不透明且银行系灵活性差，Ksher用透明底价+快速响应突破",
    },
    "光子易": {
        "name_en": "PhotonPay",
        "name_cn": "光子易",
        "parent": "",
        "founded": 2015,
        "hq": "香港",
        "scale": "20万+企业",
        "markets": "200+国家，60+主要币种",
        "fee_rate": "定制企业定价",
        "settlement": "97%实时结算（行业最快）",
        "licenses": "香港MSO/TCSP/SFC+美国MSB/MTL+英国FCA EMI+Discover+Mastercard双卡组织",
        "strengths": [
            "Agentic Payments（AI Agent支付4.0）",
            "Discover+Mastercard双卡组织发卡资质（大中华区稀缺）",
            "Stripe战略合作2026",
            "97%实时结算率",
            "IDG+高瓴+启明B轮",
        ],
        "weaknesses": [
            "品牌知名度低（2026年才高调）",
            "东南亚本地化深度不足",
            "定价不透明",
        ],
        "ksher_advantages": [
            "东南亚8国本地牌照 vs 光子易的全球通用路径",
            "费率透明公开 vs 光子易定制不透明",
            "本地团队服务 vs 技术驱动远程服务",
            "成熟的东南亚客户网络和合作伙伴生态",
        ],
        "threat_level": "中",
        "attack_angle": "光子易技术先进但东南亚不够深，Ksher用本地牌照+本地团队的落地能力差异化",
    },
    "PingPong": {
        "name_en": "PingPong",
        "name_cn": "乒乓",
        "parent": "",
        "founded": 2015,
        "hq": "杭州",
        "scale": "100万+跨境电商卖家",
        "markets": "200+国家，100+电商平台",
        "fee_rate": "0.4%-1%（平台相关）",
        "settlement": "当日结算可选",
        "licenses": "60+全球牌照（含40+美国州级）",
        "strengths": [
            "电商平台覆盖第一（100+平台）",
            "支付宝创始团队背景",
            "D轮独角兽（估值15亿美元+）",
            "AI产品矩阵（供应链+信用+智能选平台）",
        ],
        "weaknesses": [
            "费率结构不够透明",
            "东南亚本地化深度不如Ksher",
            "偏电商平台，B2B贸易覆盖弱",
        ],
        "ksher_advantages": [
            "东南亚本地牌照直连 vs PingPong中转路径",
            "B2B贸易收款更专业",
            "费率更透明，0.05%底价",
            "本地化服务团队，响应速度更快",
        ],
        "threat_level": "高",
        "attack_angle": "PingPong电商平台强但B2B弱、东南亚不够深，Ksher聚焦东南亚贸易+本地清算",
    },
    "连连支付": {
        "name_en": "LianLian",
        "name_cn": "连连支付",
        "parent": "",
        "founded": 2009,
        "hq": "杭州",
        "scale": "790万+企业",
        "markets": "100+国家，66+支付牌照",
        "fee_rate": "定制定价（超低费率+0汇损定位）",
        "settlement": "实时外汇",
        "licenses": "66+全球牌照（含中国央行+40美国州+英国EMI+新加坡MPI）",
        "strengths": [
            "港股上市（2592.HK），资本信心强",
            "iResearch收款工具使用频率第一",
            "790万企业规模",
            "累计处理3.3万亿+TPV",
            "一站式生态（开店+税务+融资）",
        ],
        "weaknesses": [
            "费率不够透明",
            "规模大但SME个性化服务弱",
            "东南亚不是核心市场",
        ],
        "ksher_advantages": [
            "东南亚本地牌照直连 vs 连连的全球通路",
            "费率透明公开，SME友好",
            "本地化深度：7国本地运营团队",
            "灵活定价，中小企业也能享受低费率",
        ],
        "threat_level": "中",
        "attack_angle": "连连规模大但东南亚不深，费率不透明，Ksher用本地深耕+透明定价打",
    },
    "空中云汇": {
        "name_en": "Airwallex",
        "name_cn": "空中云汇",
        "parent": "",
        "founded": 2015,
        "hq": "新加坡/墨尔本",
        "scale": "20万+企业",
        "markets": "70+国家本地收款，180+国家/160+支付方式",
        "fee_rate": "基础免费/Grow待定/加速版¥2,499/月",
        "settlement": "实时收款，T+0出款",
        "licenses": "80+全球牌照",
        "strengths": [
            "全球企业账户专家",
            "80+牌照，180+币种",
            "AI自动化工作流（会计集成）",
            "Yield利息产品（USD 3.68%）",
            "企业级客户（SHEIN/京东/得物）",
        ],
        "weaknesses": [
            "偏企业级，SME电商非核心",
            "B2B贸易专业度不如专注型玩家",
            "月费模式对中小企业门槛高",
        ],
        "ksher_advantages": [
            "0元开户+按量计费 vs 空中云汇月费模式",
            "东南亚本地牌照直连 vs 全球通路",
            "中小企业友好，无最低消费",
            "本地化服务响应 vs 全球化远程服务",
        ],
        "threat_level": "中",
        "attack_angle": "空中云汇偏企业级+月费模式，Ksher对中小企业更友好，0门槛+按量计费",
    },
    "Payoneer": {
        "name_en": "Payoneer",
        "name_cn": "派安盈",
        "parent": "",
        "founded": 2005,
        "hq": "纽约",
        "scale": "500万+用户",
        "markets": "190+国家",
        "fee_rate": "开户免费；收款0-1%；提现0-2%",
        "settlement": "因平台和目的地而异",
        "licenses": "美国MSB+英国EMI+香港MSO+新加坡+澳大利亚AFSL等",
        "strengths": [
            "20年老牌（2005年先驱）",
            "纳斯达克上市（PAYO），品牌信任",
            "2000+平台合作",
            "150+币种支持",
            "稳定币支付（7×24实时）",
        ],
        "weaknesses": [
            "通用型平台，非SME专精",
            "费率结构不透明",
            "东南亚本地化弱",
        ],
        "ksher_advantages": [
            "东南亚本地牌照，到账更快",
            "费率更低更透明",
            "本地化服务，中文团队支持",
            "专注东南亚，理解市场更深",
        ],
        "threat_level": "中",
        "attack_angle": "Payoneer全球老牌但东南亚不深、费率不透明，Ksher本地化+透明费率更优",
    },
    "易宝支付": {
        "name_en": "Yeepay",
        "name_cn": "易宝支付",
        "parent": "",
        "founded": 2003,
        "hq": "北京",
        "scale": "650万+商户",
        "markets": "中国为主+200+国家（通过TransferMate）",
        "fee_rate": "定制企业定价",
        "settlement": "实时结算",
        "licenses": "央行支付牌照（永久）+TransferMate 95牌照",
        "strengths": [
            "最早入局（2003年，22年历史）",
            "首笔跨境外汇交易完成者",
            "行业垂直专精（航旅/教育）",
            "TransferMate合作覆盖200+国家",
        ],
        "weaknesses": [
            "国内为主，东南亚非核心",
            "东南亚深度本地化缺失",
            "渠道政策不公开",
        ],
        "ksher_advantages": [
            "东南亚原生玩家 vs 易宝的间接覆盖",
            "本地牌照直连 vs 通过合作伙伴中转",
            "跨境收款专精 vs 易宝的综合支付",
            "费率透明，中小企业友好",
        ],
        "threat_level": "低",
        "attack_angle": "易宝国内强但东南亚通过合作伙伴间接覆盖，Ksher是东南亚原生选手",
    },
    "Pyvio": {
        "name_en": "Pyvio",
        "name_cn": "湃沃",
        "parent": "",
        "founded": 2022,
        "hq": "杭州萧山",
        "scale": "1.2万+出海企业",
        "markets": "14+新兴市场（东南亚+拉美+非洲）",
        "fee_rate": "1%封顶（行业最低级别）；0元开户/管理/提现",
        "settlement": "T+0实时结算可选",
        "licenses": "香港MSO+美国FinCEN MSB+加拿大FINTRAC MSB",
        "strengths": [
            "费率极低（1%封顶）",
            "16+小币种专精",
            "拉美/非洲非传统市场覆盖",
            "新客补贴力度大（最高2.5万）",
        ],
        "weaknesses": [
            "成立仅2022年，历史短",
            "规模小（1.2万企业）",
            "渠道政策未公开",
        ],
        "ksher_advantages": [
            "东南亚8国本地牌照 vs Pyvio仅3张牌照",
            "10年市场深耕 vs Pyvio 4年新公司",
            "本地化团队和合作伙伴网络成熟",
            "客户规模和处理经验更丰富",
        ],
        "threat_level": "中",
        "attack_angle": "Pyvio价格战打法但牌照少、历史短，Ksher用牌照齐全+运营成熟度碾压",
    },
    "Alipay": {
        "name_en": "Alipay / Ant Group",
        "name_cn": "支付宝 / 蚂蚁集团",
        "parent": "蚂蚁科技集团",
        "founded": 2004,
        "hq": "杭州",
        "scale": "10亿+支付宝用户，18亿+Alipay+覆盖用户",
        "markets": "100+国家，250+支付方式",
        "fee_rate": "Alipay+: 0%；Antom/万里汇各自定价",
        "settlement": "实时至T+1",
        "licenses": "全球多管辖区独立牌照",
        "strengths": [
            "生态垄断级：10亿+用户",
            "15+数字钱包一点接入",
            "入境支付2026重点（外卡内绑+外包内用）",
            "Ant International IPO推进",
        ],
        "weaknesses": [
            "监管不确定性",
            "生态复杂，中小企业个性化弱",
            "Alipay+依赖钱包合作伙伴",
        ],
        "ksher_advantages": [
            "专注出口收款 vs 蚂蚁的生态广度",
            "中小企业个性化服务 vs 大平台标准化",
            "东南亚本地牌照直连 vs 平台中转",
            "费率透明简单 vs 多产品线定价复杂",
        ],
        "threat_level": "中",
        "attack_angle": "蚂蚁生态强但出口收款非核心，Ksher专注跨境收款+本地化深度更优",
    },
}

# 渠道名 → 竞品名映射（config.py 中 CHANNEL_OPTIONS 对应）
CHANNEL_TO_COMPETITOR = {
    "万里汇": "万里汇",
    "XTransfer": "XTransfer",
    "珊瑚跨境": "珊瑚跨境",
    "光子易": "光子易",
    "PingPong": "PingPong",
    "连连支付": "连连支付",
    "空中云汇": "空中云汇",
    "Payoneer": "Payoneer",
    "易宝支付": "易宝支付",
    "Pyvio": "Pyvio",
    "Alipay": "Alipay",
    # 以下渠道暂无专门分析，归到通用
    "Skyee": None,
    "iPayLinks": None,
    "PanPay": None,
    "Sunrate": None,
    "CoGoLinks": None,
    "义支付": None,
    "Qbit": None,
    "Stripe": None,
    "Wise": None,
    "dLocal": None,
    "PayPal": None,
    "TikStar Pay": None,
}


def get_competitor_by_channel(channel: str) -> Optional[dict]:
    """根据渠道名获取竞品信息"""
    competitor_name = CHANNEL_TO_COMPETITOR.get(channel)
    if not competitor_name:
        return None
    return COMPETITOR_DB.get(competitor_name)


def get_competitor_card(channel: str) -> Optional[str]:
    """
    生成竞品信息卡片HTML（用于UI展示）。

    Returns:
        HTML 字符串 或 None
    """
    info = get_competitor_by_channel(channel)
    if not info:
        return None

    strengths_html = "".join(f"<li>{s}</li>" for s in info["strengths"][:3])
    advantages_html = "".join(f"<li>{a}</li>" for a in info["ksher_advantages"][:3])

    threat_colors = {"高": "#E83E4C", "中": "#FFB800", "低": "#00C9A7"}
    tc = threat_colors.get(info["threat_level"], "#8a8f99")

    return (
        f"<div style='background:#f8f8fa;border:1px solid #e5e6ea;border-radius:0.5rem;"
        f"padding:0.6rem 0.9rem;margin:0.3rem 0;font-size:0.75rem;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem;'>"
        f"<b>{info['name_cn']} ({info['name_en']})</b>"
        f"<span style='background:{tc}18;color:{tc};padding:0.1rem 0.4rem;"
        f"border-radius:0.2rem;font-size:0.68rem;font-weight:600;'>威胁：{info['threat_level']}</span>"
        f"</div>"
        f"<div style='color:#6b6b7b;font-size:0.72rem;margin-bottom:0.3rem;'>"
        f"成立{info['founded']}年 · {info['hq']} · {info['scale']}</div>"
        f"<div style='color:#6b6b7b;font-size:0.72rem;margin-bottom:0.2rem;'>"
        f"费率：{info['fee_rate']} · 结算：{info['settlement']}</div>"
        f"<div style='display:flex;gap:1rem;margin-top:0.3rem;'>"
        f"<div style='flex:1;'>"
        f"<div style='font-size:0.7rem;font-weight:600;color:#8a8f99;margin-bottom:0.15rem;'>竞品优势</div>"
        f"<ul style='margin:0;padding-left:1rem;font-size:0.7rem;color:#1d2129;'>{strengths_html}</ul>"
        f"</div>"
        f"<div style='flex:1;'>"
        f"<div style='font-size:0.7rem;font-weight:600;color:#E83E4C;margin-bottom:0.15rem;'>Ksher打法</div>"
        f"<ul style='margin:0;padding-left:1rem;font-size:0.7rem;color:#1d2129;'>{advantages_html}</ul>"
        f"</div>"
        f"</div>"
        f"</div>"
    )


def get_attack_angle(channel: str) -> str:
    """获取针对该竞品的攻击角度（一句话）"""
    info = get_competitor_by_channel(channel)
    if not info:
        return ""
    return info.get("attack_angle", "")


def get_competitor_weaknesses(channel: str) -> list:
    """获取竞品弱点列表"""
    info = get_competitor_by_channel(channel)
    if not info:
        return []
    return info.get("weaknesses", [])


def get_ksher_advantages_vs(channel: str) -> list:
    """获取 Ksher 相对该竞品的优势列表"""
    info = get_competitor_by_channel(channel)
    if not info:
        return []
    return info.get("ksher_advantages", [])
