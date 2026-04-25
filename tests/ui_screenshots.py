"""
UI 自动化截图验收脚本 — 一键验证所有关键页面

用法:
    source .venv/bin/activate && python tests/ui_screenshots.py

功能:
    1. 启动 Streamlit（如果未运行）
    2. 使用 Playwright 截图所有关键页面
    3. 输出到 tests/screenshots/{日期}/ 目录
    4. 生成验收报告 HTML

依赖:
    pip install playwright
    python -m playwright install chromium
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_DIR = Path(__file__).parent.parent
SCREENSHOT_DIR = BASE_DIR / "tests" / "screenshots" / datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT_PATH = SCREENSHOT_DIR / "report.html"
STREAMLIT_URL = "http://localhost:8501"

# ============================================================
# 验收标准配置
# ============================================================

ACCEPTANCE_CHECKS = [
    {
        "name": "市场专员-素材库-品牌素材",
        "role": "市场专员",
        "tab": "素材库",
        "sub_tab": "品牌素材",
        "checks": [
            "品牌主色展示正确",
            "两张品牌海报图片正常显示",
        ],
        "scroll": 0,
    },
    {
        "name": "市场专员-素材库-产品知识卡片",
        "role": "市场专员",
        "tab": "素材库",
        "sub_tab": "产品知识卡片",
        "checks": [
            "分类 pills 导航正常显示",
            "默认选中'基础知识篇'",
            "卡片完整内容可见",
        ],
        "scroll": 500,
    },
    {
        "name": "市场专员-海报工坊",
        "role": "市场专员",
        "tab": "海报工坊",
        "sub_tab": None,
        "checks": [
            "生成模式切换按钮存在（纯HTML/CSS + AI背景图）",
            "输入框和参考模板可见",
        ],
        "scroll": 0,
    },
    {
        "name": "市场专员-朋友圈-日常朋友圈",
        "role": "市场专员",
        "tab": "朋友圈",
        "sub_tab": None,
        "checks": [
            "周导航和素材列表可见",
            "模式选择存在",
        ],
        "scroll": 300,
    },
    {
        "name": "销售支持-首页",
        "role": "销售支持",
        "tab": None,
        "sub_tab": None,
        "checks": [
            "话术生成器可见",
            "客户画像卡片存在",
        ],
        "scroll": 0,
    },
]


def ensure_streamlit():
    """确保 Streamlit 在运行"""
    import requests
    try:
        resp = requests.get(STREAMLIT_URL, timeout=3)
        if resp.status_code == 200:
            print("✅ Streamlit 已在运行")
            return True
    except Exception:
        pass

    print("🚀 启动 Streamlit...")
    subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.port=8501", "--server.headless=true"],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # 等待启动
    for i in range(30):
        time.sleep(1)
        try:
            import requests
            resp = requests.get(STREAMLIT_URL, timeout=3)
            if resp.status_code == 200:
                print("✅ Streamlit 启动成功")
                return True
        except Exception:
            pass
    print("❌ Streamlit 启动超时")
    return False


def take_screenshots():
    """使用 Playwright 截图所有验收页面"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 请先安装 Playwright: pip install playwright && python -m playwright install chromium")
        sys.exit(1)

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})

        for check in ACCEPTANCE_CHECKS:
            name = check["name"]
            role = check["role"]
            tab = check.get("tab")
            sub_tab = check.get("sub_tab")
            scroll = check.get("scroll", 0)

            print(f"📸 截图: {name}")
            page.goto(STREAMLIT_URL)
            page.wait_for_timeout(3000)

            # 选择角色
            try:
                page.locator(f"text={role}").first.click()
                page.wait_for_timeout(1500)
            except Exception:
                pass

            # 选择 Tab
            if tab:
                try:
                    page.locator(f"text={tab}").first.click()
                    page.wait_for_timeout(1500)
                except Exception:
                    pass

            # 选择子 Tab
            if sub_tab:
                try:
                    page.locator(f"text={sub_tab}").first.click()
                    page.wait_for_timeout(1500)
                except Exception:
                    pass

            # 滚动
            if scroll > 0:
                page.evaluate(f"window.scrollTo(0, {scroll})")
                page.wait_for_timeout(500)

            # 截图
            safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name)
            path = SCREENSHOT_DIR / f"{safe_name}.png"
            page.screenshot(path=str(path))

            results.append({
                "name": name,
                "path": str(path.relative_to(SCREENSHOT_DIR)),
                "checks": check["checks"],
                "status": "done",
            })
            print(f"   ✅ 已保存: {path.name}")

        browser.close()

    return results


def generate_report(results):
    """生成 HTML 验收报告"""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Ksher AgentAI — UI 验收报告</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem; background: #f5f5f7; }}
.header {{ background: #E83E4C; color: white; padding: 1.5rem; border-radius: 1rem; margin-bottom: 2rem; }}
.header h1 {{ margin: 0; font-size: 1.5rem; }}
.header time {{ opacity: 0.8; font-size: 0.9rem; }}
.card {{ background: white; border-radius: 0.75rem; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.card h2 {{ margin-top: 0; color: #1d2129; font-size: 1.1rem; }}
.card img {{ max-width: 100%; border-radius: 0.5rem; border: 1px solid #e5e6ea; margin-top: 0.5rem; }}
.checks {{ margin-top: 0.5rem; }}
.checks li {{ color: #4a4f59; margin-bottom: 0.25rem; }}
.stats {{ display: flex; gap: 1rem; margin-bottom: 1rem; }}
.stat {{ background: white; padding: 1rem 1.5rem; border-radius: 0.75rem; text-align: center; flex: 1; }}
.stat .num {{ font-size: 1.8rem; font-weight: 700; color: #E83E4C; }}
.stat .label {{ color: #8a8f99; font-size: 0.85rem; }}
</style>
</head>
<body>
<div class="header">
<h1>🎨 Ksher AgentAI — UI 验收报告</h1>
<time>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</time>
</div>

<div class="stats">
<div class="stat"><div class="num">{len(results)}</div><div class="label">验收页面</div></div>
<div class="stat"><div class="num">{sum(len(r['checks']) for r in results)}</div><div class="label">验收标准</div></div>
</div>
"""

    for r in results:
        checks_html = "\n".join(f"<li>☐ {c}</li>" for c in r["checks"])
        html += f"""
<div class="card">
<h2>{r['name']}</h2>
<div class="checks"><ul>{checks_html}</ul></div>
<img src="{r['path']}" alt="{r['name']}">
</div>
"""

    html += "</body></html>"

    REPORT_PATH.write_text(html, encoding="utf-8")
    return REPORT_PATH


def main():
    print("=" * 60)
    print(" Ksher AgentAI — UI 自动化截图验收")
    print("=" * 60)

    if not ensure_streamlit():
        sys.exit(1)

    results = take_screenshots()
    report_path = generate_report(results)

    print()
    print("=" * 60)
    print(f"✅ 截图完成！{len(results)} 个页面")
    print(f"📁 截图目录: {SCREENSHOT_DIR}")
    print(f"📄 验收报告: {report_path}")
    print()
    print("请打开验收报告，对照勾选验收标准 ☑️")
    print("=" * 60)


if __name__ == "__main__":
    main()
