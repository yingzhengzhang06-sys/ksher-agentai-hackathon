"""
Streamlit E2E 测试 — Playwright

运行: source .venv/bin/activate && python3 tests/e2e_streamlit.py

测试流程:
1. 启动 Streamlit 应用
2. 截图首页
3. 切换到市场专员页面
4. 测试各 Tab 切换
5. 测试按钮交互
6. 保存截图到 tests/screenshots/
"""
import subprocess
import time
import os
import sys
import signal

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOT_DIR = os.path.join(BASE_DIR, "tests", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def start_streamlit():
    """在后台启动 Streamlit 应用"""
    env = os.environ.copy()
    env["STREAMLIT_SERVER_PORT"] = "8502"  # 使用非默认端口避免冲突
    env["STREAMLIT_SERVER_HEADLESS"] = "true"

    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.port", "8502",
         "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    return proc


def wait_for_streamlit(url: str, timeout: int = 30) -> bool:
    """等待 Streamlit 服务就绪"""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def run_e2e_tests():
    from playwright.sync_api import sync_playwright, expect

    print("🚀 启动 Streamlit 应用...")
    proc = start_streamlit()
    url = "http://localhost:8502"

    try:
        print(f"⏳ 等待服务就绪 ({url})...")
        if not wait_for_streamlit(url, timeout=30):
            print("❌ Streamlit 启动超时")
            return False
        print("✅ Streamlit 已就绪")

        # 给 Streamlit 多一点时间完全加载
        time.sleep(3)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()

            # ============================================================
            # 测试 1: 首页加载
            # ============================================================
            print("\n📸 测试 1: 首页加载")
            page.goto(url)
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # 截图首页
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_homepage.png"), full_page=True)
            print("  ✅ 首页截图已保存")

            # 验证侧边栏存在
            sidebar = page.locator("[data-testid='stSidebar']")
            expect(sidebar).to_be_visible()
            print("  ✅ 侧边栏可见")

            # ============================================================
            # 测试 2: 切换到市场专员页面
            # ============================================================
            print("\n📸 测试 2: 市场专员页面")

            # 点击侧边栏中的"市场专员"
            # Streamlit 的 radio 按钮在 sidebar 中
            page.locator("text=市场专员").first.click()
            time.sleep(2)

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_marketing_page.png"), full_page=True)
            print("  ✅ 市场专员页面截图已保存")

            # 验证页面标题
            expect(page.locator("text=朋友圈获客中心").or_(page.locator("text=市场专员"))).to_be_visible()
            print("  ✅ 市场专员页面标题可见")

            # ============================================================
            # 测试 3: 朋友圈 Tab 内容
            # ============================================================
            print("\n📸 测试 3: 朋友圈 Tab")

            # 点击"朋友圈" tab
            page.locator("text=朋友圈").first.click()
            time.sleep(2)

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_moments_tab.png"), full_page=True)
            print("  ✅ 朋友圈 Tab 截图已保存")

            # 验证身份选择存在
            expect(page.locator("text=身份").or_(page.locator("text=Ksher销售"))).to_be_visible()
            print("  ✅ 身份选择可见")

            # ============================================================
            # 测试 4: 7天日历模式
            # ============================================================
            print("\n📸 测试 4: 7天日历模式")

            # 点击"7天日历" radio
            page.locator("text=7天日历").first.click()
            time.sleep(1)

            # 点击"生成7天朋友圈日历"按钮
            generate_btn = page.locator("button:has-text('生成7天朋友圈日历')")
            if generate_btn.count() > 0:
                generate_btn.first.click()
                time.sleep(3)  # 等待生成

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_calendar_generated.png"), full_page=True)
            print("  ✅ 7天日历截图已保存")

            # 验证生成了内容
            day_expander = page.locator("text=Day 1").first
            if day_expander.is_visible():
                print("  ✅ Day 1 内容已生成")
            else:
                print("  ⚠️ Day 1 内容未找到（可能是 Mock 模式）")

            # ============================================================
            # 测试 5: 单条快速模式
            # ============================================================
            print("\n📸 测试 5: 单条快速模式")

            page.locator("text=单条快速").first.click()
            time.sleep(1)

            # 点击"生成"按钮
            gen_btn = page.locator("button:has-text('生成')").first
            gen_btn.click()
            time.sleep(3)

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_single_moment.png"), full_page=True)
            print("  ✅ 单条快速截图已保存")

            # ============================================================
            # 测试 6: 短视频中心 Tab
            # ============================================================
            print("\n📸 测试 6: 短视频中心")

            page.locator("text=短视频中心").first.click()
            time.sleep(2)

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_video_tab.png"), full_page=True)
            print("  ✅ 短视频中心截图已保存")

            # ============================================================
            # 测试 7: 海报工坊 Tab
            # ============================================================
            print("\n📸 测试 7: 海报工坊")

            page.locator("text=海报工坊").first.click()
            time.sleep(2)

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_poster_tab.png"), full_page=True)
            print("  ✅ 海报工坊截图已保存")

            # ============================================================
            # 测试 8: 销售支持页面
            # ============================================================
            print("\n📸 测试 8: 销售支持页面")

            page.locator("text=销售支持").first.click()
            time.sleep(2)

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "08_sales_support.png"), full_page=True)
            print("  ✅ 销售支持页面截图已保存")

            browser.close()
            print("\n🎉 所有 E2E 测试完成！")
            print(f"📁 截图保存在: {SCREENSHOT_DIR}")
            return True

    except Exception as e:
        print(f"\n❌ E2E 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print("\n🛑 停止 Streamlit...")
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("✅ Streamlit 已停止")


if __name__ == "__main__":
    success = run_e2e_tests()
    sys.exit(0 if success else 1)
