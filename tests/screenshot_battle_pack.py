"""
用 Playwright 截图 Battle Pack UI
"""
import json
import subprocess
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# 读取预生成的作战包数据
with open(PROJECT_ROOT / "tests" / "e2e_battle_pack_result.json", "r") as f:
    battle_pack = json.load(f)

# 创建一个临时 Streamlit 脚本，直接展示作战包
temp_script = PROJECT_ROOT / "tests" / "_temp_battle_pack_demo.py"

battle_pack_json = json.dumps(battle_pack, ensure_ascii=False)

script_content = '''
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import BRAND_COLORS, BATTLEFIELD_TYPES
from ui.components.battle_pack_display import render_battle_pack

st.set_page_config(
    page_title="Ksher AgentAI - Battle Pack Demo",
    page_icon="⚔️",
    layout="wide",
)

# 品牌 CSS
st.markdown("""
<style>
.stApp { background-color: #0F0F1A !important; }
</style>
""", unsafe_allow_html=True)

# 客户上下文
context = {
    "company": "深圳外贸工厂",
    "industry": "b2b",
    "target_country": "thailand",
    "monthly_volume": 80,
    "current_channel": "招商银行电汇",
    "pain_points": ["手续费高", "到账慢", "汇率损失大"],
    "battlefield": "increment",
}

battle_pack = ''' + battle_pack_json + '''

st.title("⚔️ 一键备战")
st.markdown("<span style='color:#B0B0C0;'>作战包展示</span>", unsafe_allow_html=True)
st.markdown("---")

bf_type = context["battlefield"]
bf_info = BATTLEFIELD_TYPES.get(bf_type, {})
bf_label = bf_info.get("label", bf_type)

st.markdown(f"""
<div style='display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;'>
    <span style='background: #E83E4C; color: #FFF; padding: 0.3rem 0.8rem; border-radius: 1rem; font-size: 0.8rem; font-weight: 600;'>
        {bf_label}
    </span>
    <span style='color: #B0B0C0; font-size: 0.85rem;'>
        为客户「深圳外贸工厂」生成
    </span>
</div>
""", unsafe_allow_html=True)

render_battle_pack(battle_pack, context)
'''

temp_script.write_text(script_content, encoding="utf-8")

# 启动临时 Streamlit
proc = subprocess.Popen(
    ["streamlit", "run", str(temp_script),
     "--server.headless", "true",
     "--server.port", "8502",
     "--browser.gatherUsageStats", "false"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

print("Starting temporary Streamlit on port 8502...")
time.sleep(5)

# 用 Playwright 截图
try:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("http://localhost:8502")
        time.sleep(4)

        # 截图 - 话术部分
        page.screenshot(path=str(PROJECT_ROOT / "tests" / "battle_pack_screenshot_1.png"), full_page=True)
        print("Screenshot 1 saved: battle_pack_screenshot_1.png")

        # 滚动到成本部分
        page.evaluate("window.scrollTo(0, 900)")
        time.sleep(1)
        page.screenshot(path=str(PROJECT_ROOT / "tests" / "battle_pack_screenshot_2.png"), full_page=True)
        print("Screenshot 2 saved: battle_pack_screenshot_2.png")

        # 滚动到方案部分
        page.evaluate("window.scrollTo(0, 1800)")
        time.sleep(1)
        page.screenshot(path=str(PROJECT_ROOT / "tests" / "battle_pack_screenshot_3.png"), full_page=True)
        print("Screenshot 3 saved: battle_pack_screenshot_3.png")

        # 滚动到异议部分
        page.evaluate("window.scrollTo(0, 2600)")
        time.sleep(1)
        page.screenshot(path=str(PROJECT_ROOT / "tests" / "battle_pack_screenshot_4.png"), full_page=True)
        print("Screenshot 4 saved: battle_pack_screenshot_4.png")

        browser.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    proc.terminate()
    proc.wait()
    temp_script.unlink()
    print("Cleanup done")
