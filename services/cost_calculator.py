"""
成本计算器 — 纯 Python 计算引擎（不调用 AI）

输入：客户画像（行业/国家/月流水/当前渠道）
输出：5 项成本对比数据（Ksher vs 当前渠道）

计算公式：
  1. 显性手续费 = 月流水 × 手续费率 × 12
  2. 汇率损失 = 月流水 × 汇率差 × 12
  3. 资金时间成本 = 月流水 × (结算天数/365) × 年化利率6% × 12
  4. 多平台管理成本 = 估算值
  5. 合规风险成本 = 定性描述

费率数据从 knowledge/fee_structure.json 读取
"""
import json
import os
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CostBreakdown:
    """单项成本明细"""
    fee: float          # 显性手续费（年）
    fx_loss: float      # 汇率损失（年）
    time_cost: float    # 资金时间成本（年）
    mgmt_cost: float    # 多平台管理成本（年）
    compliance_cost: float  # 合规风险成本（年，用数值表示）
    total: float        # 年度总计
    compliance_note: str    # 合规风险定性描述


def load_fee_structure() -> dict:
    """加载 fee_structure.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "knowledge", "fee_structure.json")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_ksher_rate(industry: str, target_country: str, fee_data: dict) -> Optional[dict]:
    """获取 Ksher 对应行业和国家的费率配置"""
    ksher = fee_data.get("ksher", {})
    if industry not in ksher:
        return None
    countries = ksher[industry].get("countries", {})
    return countries.get(target_country)


def get_competitor_rate(channel: str, industry: str, fee_data: dict) -> Optional[dict]:
    """获取竞品费率配置（支持模糊匹配）"""
    competitors = fee_data.get("competitors", {})
    channel_lower = channel.lower()

    for key, comp in competitors.items():
        name = comp.get("name", "").lower()
        if key.lower() in channel_lower or name in channel_lower:
            # 选择对应行业的费率
            fee_key = f"{industry}_fee_rate" if industry else "b2c_fee_rate"
            fee_rate = comp.get(fee_key, comp.get("b2c_fee_rate", 0))
            return {
                "name": comp.get("name", key),
                "fee_rate": fee_rate,
                "fx_spread": comp.get("fx_spread", 0.005),
                "settlement_days": comp.get("settlement_days", 2),
                "notes": comp.get("notes", ""),
            }
    return None


def get_bank_rate(fee_data: dict) -> dict:
    """获取银行电汇费率配置"""
    bank = fee_data.get("bank", {})
    wire = bank.get("wire_transfer", {})
    return {
        "name": bank.get("name", "银行电汇"),
        "fee_fixed_per_transaction": wire.get("fee_fixed_per_transaction", 150),
        "fee_rate": wire.get("fee_rate", 0.015),
        "fx_spread": wire.get("fx_spread", 0.008),
        "settlement_days": wire.get("settlement_days", 3),
    }


def estimate_monthly_transactions(monthly_volume: float) -> int:
    """估算月交易笔数（基于月流水）"""
    # 假设平均每笔 2000-5000 USD
    if monthly_volume <= 0:
        return 0
    avg_tx = 3500
    return max(1, int(monthly_volume / avg_tx))


def calculate_costs(
    monthly_volume: float,
    fee_rate: float,
    fx_spread: float,
    settlement_days: int,
    fixed_fee_per_tx: float = 0,
    monthly_tx_count: int = 0,
) -> CostBreakdown:
    """
    计算 5 项年度成本

    Args:
        monthly_volume: 月流水（USD）
        fee_rate: 手续费率
        fx_spread: 汇率差
        settlement_days: 结算天数
        fixed_fee_per_tx: 每笔固定手续费（元）
        monthly_tx_count: 月交易笔数
    """
    # 1. 显性手续费
    annual_fee = monthly_volume * fee_rate * 12
    annual_fixed_fee = fixed_fee_per_tx * monthly_tx_count * 12
    total_fee = annual_fee + annual_fixed_fee

    # 2. 汇率损失
    annual_fx_loss = monthly_volume * fx_spread * 12

    # 3. 资金时间成本 = 月流水 × (结算天数/365) × 年化利率6% × 12
    annual_time_cost = monthly_volume * (settlement_days / 365) * 0.06 * 12

    # 4. 多平台管理成本（估算：多一天结算 = 多一份管理成本）
    # 基准：T+1 无额外成本，每多一天增加约 0.05% 管理成本
    mgmt_rate = max(0, (settlement_days - 1) * 0.0005)
    annual_mgmt_cost = monthly_volume * mgmt_rate * 12

    # 5. 合规风险成本（定性转定量：无本地牌照 = 0.3% 风险溢价）
    compliance_rate = 0.003 if settlement_days > 1 else 0.001
    annual_compliance_cost = monthly_volume * compliance_rate * 12

    total = total_fee + annual_fx_loss + annual_time_cost + annual_mgmt_cost + annual_compliance_cost

    return CostBreakdown(
        fee=round(total_fee, 2),
        fx_loss=round(annual_fx_loss, 2),
        time_cost=round(annual_time_cost, 2),
        mgmt_cost=round(annual_mgmt_cost, 2),
        compliance_cost=round(annual_compliance_cost, 2),
        total=round(total, 2),
        compliance_note="",
    )


def get_compliance_note(channel_type: str) -> str:
    """获取合规风险定性描述"""
    notes = {
        "bank": "银行合规完善，但跨境回款链路长，存在中间行退单风险",
        "competitor": "第三方跨境支付平台，无东南亚本地央行牌照，资金需经多层中转",
        "ksher": "持有东南亚多国本地支付牌照，资金本地清算，合规链路短",
    }
    return notes.get(channel_type, "合规情况需具体评估")


def calculate_comparison(
    industry: str,
    target_country: str,
    monthly_volume: float,
    current_channel: str,
) -> dict:
    """
    主入口：计算 Ksher vs 当前渠道的 5 项成本对比

    Args:
        industry: "b2c" | "b2b" | "service"
        target_country: "thailand" | "malaysia" | ...
        monthly_volume: 月流水（USD）
        current_channel: 当前收款渠道名称

    Returns:
        dict: {
            "ksher": CostBreakdown,
            "current": CostBreakdown,
            "annual_saving": float,
            "comparison_table": dict,  # 符合 INTERFACES.md 格式
            "chart_data": dict,        # Plotly 图表数据
        }
    """
    fee_data = load_fee_structure()
    monthly_tx = estimate_monthly_transactions(monthly_volume)

    # ── Ksher 成本 ──
    ksher_config = get_ksher_rate(industry, target_country, fee_data)
    if not ksher_config:
        # 回退：使用默认费率
        ksher_config = {"fee_rate": 0.008, "fx_spread": 0.002, "settlement_days": 1}

    ksher_costs = calculate_costs(
        monthly_volume=monthly_volume,
        fee_rate=ksher_config.get("fee_rate", 0.008),
        fx_spread=ksher_config.get("fx_spread", 0.002),
        settlement_days=ksher_config.get("settlement_days", 1),
    )
    ksher_costs.compliance_note = get_compliance_note("ksher")

    # ── 当前渠道成本 ──
    # 判断是银行还是竞品
    bank_keywords = ["银行", "bank", "招商", "工商", "建设", "中国", "电汇"]
    is_bank = any(kw in current_channel.lower() for kw in bank_keywords)

    if is_bank:
        bank_config = get_bank_rate(fee_data)
        current_costs = calculate_costs(
            monthly_volume=monthly_volume,
            fee_rate=bank_config["fee_rate"],
            fx_spread=bank_config["fx_spread"],
            settlement_days=bank_config["settlement_days"],
            fixed_fee_per_tx=bank_config["fee_fixed_per_transaction"],
            monthly_tx_count=monthly_tx,
        )
        current_costs.compliance_note = get_compliance_note("bank")
    else:
        comp_config = get_competitor_rate(current_channel, industry, fee_data)
        if comp_config:
            current_costs = calculate_costs(
                monthly_volume=monthly_volume,
                fee_rate=comp_config["fee_rate"],
                fx_spread=comp_config["fx_spread"],
                settlement_days=comp_config["settlement_days"],
            )
            current_costs.compliance_note = get_compliance_note("competitor")
        else:
            # 未知渠道：使用保守估计（银行费率）
            bank_config = get_bank_rate(fee_data)
            current_costs = calculate_costs(
                monthly_volume=monthly_volume,
                fee_rate=bank_config["fee_rate"],
                fx_spread=bank_config["fx_spread"],
                settlement_days=bank_config["settlement_days"],
                fixed_fee_per_tx=bank_config["fee_fixed_per_transaction"],
                monthly_tx_count=monthly_tx,
            )
            current_costs.compliance_note = f"当前渠道「{current_channel}」费率数据暂缺，按银行电汇保守估算"

    # ── 计算节省 ──
    annual_saving = round(current_costs.total - ksher_costs.total, 2)

    # ── 构建 comparison_table（符合 INTERFACES.md）──
    comparison_table = {
        "ksher": {
            "fee": ksher_costs.fee,
            "fx_loss": ksher_costs.fx_loss,
            "time_cost": ksher_costs.time_cost,
            "mgmt_cost": ksher_costs.mgmt_cost,
            "compliance_cost": ksher_costs.compliance_cost,
            "total": ksher_costs.total,
        },
        "current": {
            "fee": current_costs.fee,
            "fx_loss": current_costs.fx_loss,
            "time_cost": current_costs.time_cost,
            "mgmt_cost": current_costs.mgmt_cost,
            "compliance_cost": current_costs.compliance_cost,
            "total": current_costs.total,
        },
    }

    # ── 生成 Plotly 图表数据 ──
    chart_data = {
        "bar": {
            "data": [
                {
                    "x": ["显性手续费", "汇率损失", "资金时间成本", "多平台管理", "合规风险"],
                    "y": [
                        current_costs.fee,
                        current_costs.fx_loss,
                        current_costs.time_cost,
                        current_costs.mgmt_cost,
                        current_costs.compliance_cost,
                    ],
                    "name": current_channel,
                    "type": "bar",
                    "marker": {"color": "#6B6B7B"},
                },
                {
                    "x": ["显性手续费", "汇率损失", "资金时间成本", "多平台管理", "合规风险"],
                    "y": [
                        ksher_costs.fee,
                        ksher_costs.fx_loss,
                        ksher_costs.time_cost,
                        ksher_costs.mgmt_cost,
                        ksher_costs.compliance_cost,
                    ],
                    "name": "Ksher",
                    "type": "bar",
                    "marker": {"color": "#E83E4C"},
                },
            ],
            "layout": {
                "barmode": "group",
                "title": "年度收款成本对比（元）",
                "yaxis": {"title": "年度成本（元）"},
                "paper_bgcolor": "rgba(0,0,0,0)",
                "plot_bgcolor": "rgba(0,0,0,0)",
                "font": {"color": "#FFFFFF"},
            },
        },
        "pie": {
            "data": [
                {
                    "values": [current_costs.total, max(0, annual_saving)],
                    "labels": [f"{current_channel} 成本", "切换到 Ksher 节省"],
                    "type": "pie",
                    "marker": {"colors": ["#6B6B7B", "#00C9A7"]},
                    "hole": 0.4,
                }
            ],
            "layout": {
                "title": "成本结构占比",
                "paper_bgcolor": "rgba(0,0,0,0)",
                "font": {"color": "#FFFFFF"},
            },
        },
    }

    return {
        "ksher": ksher_costs,
        "current": current_costs,
        "annual_saving": annual_saving,
        "monthly_saving": round(annual_saving / 12, 2),
        "saving_rate": round(annual_saving / current_costs.total * 100, 1) if current_costs.total > 0 else 0,
        "comparison_table": comparison_table,
        "chart_data": chart_data,
        "details": {
            "monthly_volume": monthly_volume,
            "monthly_transactions": monthly_tx,
            "current_channel": current_channel,
            "target_country": target_country,
            "industry": industry,
            "ksher_config": ksher_config,
        },
    }


def format_cost_summary(result: dict) -> str:
    """将计算结果格式化为易读的文本摘要（供 LLM 使用）"""
    ksher = result["ksher"]
    current = result["current"]
    ch = result["details"]["current_channel"]

    lines = [
        "## 成本对比计算结果\n",
        f"客户月流水：{result['details']['monthly_volume']:,.0f} USD",
        f"预估月交易笔数：{result['details']['monthly_transactions']} 笔\n",
        f"### {ch} 年度成本：¥{current.total:,.2f}",
        f"- 显性手续费：¥{current.fee:,.2f}",
        f"- 汇率损失：¥{current.fx_loss:,.2f}",
        f"- 资金时间成本：¥{current.time_cost:,.2f}",
        f"- 多平台管理成本：¥{current.mgmt_cost:,.2f}",
        f"- 合规风险成本：¥{current.compliance_cost:,.2f}",
        f"- 合规说明：{current.compliance_note}",
        "",
        f"### Ksher 年度成本：¥{ksher.total:,.2f}",
        f"- 显性手续费：¥{ksher.fee:,.2f}",
        f"- 汇率损失：¥{ksher.fx_loss:,.2f}",
        f"- 资金时间成本：¥{ksher.time_cost:,.2f}",
        f"- 多平台管理成本：¥{ksher.mgmt_cost:,.2f}",
        f"- 合规风险成本：¥{ksher.compliance_cost:,.2f}",
        f"- 合规说明：{ksher.compliance_note}",
        "",
        f"### 💰 年度节省：¥{result['annual_saving']:,.2f}（节省 {result['saving_rate']}%）",
        f"相当于每月多赚 ¥{result['monthly_saving']:,.2f}",
    ]
    return "\n".join(lines)


# ── 便捷函数 ──
def quick_calculate(
    industry: str,
    target_country: str,
    monthly_volume: float,
    current_channel: str,
) -> dict:
    """便捷函数：一键计算成本对比"""
    return calculate_comparison(industry, target_country, monthly_volume, current_channel)


if __name__ == "__main__":
    print("=" * 60)
    print("CostCalculator 测试")
    print("=" * 60)

    # 测试场景1：B2C + 泰国 + 银行电汇
    print("\n【场景1】B2C 跨境电商，月流水 $50,000，银行电汇 → Ksher")
    r1 = calculate_comparison("b2c", "thailand", 50000, "银行电汇")
    print(format_cost_summary(r1))

    # 测试场景2：B2B + 马来西亚 + PingPong
    print("\n" + "=" * 60)
    print("【场景2】B2B 跨境货贸，月流水 $200,000，PingPong → Ksher")
    r2 = calculate_comparison("b2b", "malaysia", 200000, "PingPong")
    print(format_cost_summary(r2))

    # 测试场景3：B2C + 越南 + 万里汇
    print("\n" + "=" * 60)
    print("【场景3】B2C 跨境电商，月流水 $100,000，万里汇 → Ksher")
    r3 = calculate_comparison("b2c", "vietnam", 100000, "万里汇")
    print(format_cost_summary(r3))
