"""
Test script for Ksher AgentAI Streamlit app - Marketing Specialist role
Navigates through all tabs and takes screenshots.
"""
import subprocess
import time
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

PROJECT_ROOT = Path(__file__).parent.parent
SCREENSHOT_DIR = PROJECT_ROOT / "tests" / "screenshots" / time.strftime("%Y%m%d_%H%M%S")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

REPORT = []

def log(msg, level="INFO"):
    print(f"[{level}] {msg}")
    REPORT.append({"level": level, "msg": msg})

def take_screenshot(page, name, full_page=True):
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=full_page)
    log(f"Screenshot saved: {path.name}")
    return path

def check_for_errors(page):
    """Check page for common error indicators"""
    errors = []
    page_content = page.content()

    error_indicators = [
        "Traceback",
        "Exception",
        "Error:",
        "streamlit.errors",
        "KeyError",
        "AttributeError",
        "ModuleNotFoundError",
        "ImportError",
    ]

    for indicator in error_indicators:
        if indicator in page_content:
            # Try to extract the error context
            idx = page_content.find(indicator)
            context = page_content[max(0, idx-100):min(len(page_content), idx+300)]
            errors.append(f"Found '{indicator}' in page: ...{context}...")

    return errors

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # ============================================================
        # 1. Navigate to main page
        # ============================================================
        log("Navigating to http://localhost:8501")
        page.goto("http://localhost:8501")
        page.wait_for_load_state("networkidle")
        time.sleep(3)  # Wait for Streamlit to render

        take_screenshot(page, "01_main_page")

        errors = check_for_errors(page)
        if errors:
            for e in errors:
                log(e, "ERROR")
            take_screenshot(page, "01_main_page_errors")

        # ============================================================
        # 2. Click on "市场专员" in sidebar
        # ============================================================
        log("Looking for '市场专员' in sidebar...")

        # Streamlit sidebar radio buttons - try to find and click
        try:
            # Try finding by text content
            marketing_link = page.locator("text=市场专员").first
            if marketing_link.is_visible():
                marketing_link.click()
                log("Clicked '市场专员' in sidebar")
                time.sleep(3)
                take_screenshot(page, "02_marketing_role_page")
            else:
                log("'市场专员' link not visible, trying alternative selectors", "WARN")
                # Try to find in the sidebar radio buttons
                sidebar = page.locator('[data-testid="stSidebar"]')
                if sidebar.is_visible():
                    # Look for the text within sidebar
                    marketing_in_sidebar = sidebar.locator("text=市场专员")
                    if marketing_in_sidebar.count() > 0:
                        marketing_in_sidebar.first.click()
                        log("Clicked '市场专员' via sidebar locator")
                        time.sleep(3)
                        take_screenshot(page, "02_marketing_role_page")
                    else:
                        log("Could not find '市场专员' in sidebar", "ERROR")
                else:
                    log("Sidebar not found", "ERROR")
        except Exception as e:
            log(f"Error clicking '市场专员': {e}", "ERROR")
            take_screenshot(page, "02_marketing_role_error")

        errors = check_for_errors(page)
        for e in errors:
            log(e, "ERROR")

        # ============================================================
        # 3. Test Tab 1: 朋友圈 (Moments)
        # ============================================================
        log("=== Testing Tab: 朋友圈 ===")
        try:
            moments_tab = page.locator('button:has-text("朋友圈")').first
            if moments_tab.is_visible():
                moments_tab.click()
                log("Clicked '朋友圈' tab")
                time.sleep(2)
                take_screenshot(page, "03_tab_moments")
            else:
                log("'朋友圈' tab not found", "WARN")
        except Exception as e:
            log(f"Error with 朋友圈 tab: {e}", "ERROR")

        # Test Mode 1: 日常朋友圈
        log("--- Testing Mode: 日常朋友圈 ---")
        try:
            daily_mode = page.locator('label:has-text("日常朋友圈")').first
            if daily_mode.is_visible():
                daily_mode.click()
                log("Selected '日常朋友圈' mode")
                time.sleep(2)
                take_screenshot(page, "04_moments_daily")
            else:
                log("'日常朋友圈' mode not found", "WARN")
        except Exception as e:
            log(f"Error with 日常朋友圈: {e}", "ERROR")

        # Test Mode 2: 素材转文案
        log("--- Testing Mode: 素材转文案 ---")
        try:
            material_mode = page.locator('label:has-text("素材转文案")').first
            if material_mode.is_visible():
                material_mode.click()
                log("Selected '素材转文案' mode")
                time.sleep(2)
                take_screenshot(page, "05_moments_material")
            else:
                log("'素材转文案' mode not found", "WARN")
        except Exception as e:
            log(f"Error with 素材转文案: {e}", "ERROR")

        # Test Mode 3: 爆款改写
        log("--- Testing Mode: 爆款改写 ---")
        try:
            rewrite_mode = page.locator('label:has-text("爆款改写")').first
            if rewrite_mode.is_visible():
                rewrite_mode.click()
                log("Selected '爆款改写' mode")
                time.sleep(2)
                take_screenshot(page, "06_moments_rewrite")
            else:
                log("'爆款改写' mode not found", "WARN")
        except Exception as e:
            log(f"Error with 爆款改写: {e}", "ERROR")

        # Test Mode 4: 朋友圈诊断
        log("--- Testing Mode: 朋友圈诊断 ---")
        try:
            diagnose_mode = page.locator('label:has-text("朋友圈诊断")').first
            if diagnose_mode.is_visible():
                diagnose_mode.click()
                log("Selected '朋友圈诊断' mode")
                time.sleep(2)
                take_screenshot(page, "07_moments_diagnose")
            else:
                log("'朋友圈诊断' mode not found", "WARN")
        except Exception as e:
            log(f"Error with 朋友圈诊断: {e}", "ERROR")

        # Test Mode 5: 热点追踪
        log("--- Testing Mode: 热点追踪 ---")
        try:
            hot_mode = page.locator('label:has-text("热点追踪")').first
            if hot_mode.is_visible():
                hot_mode.click()
                log("Selected '热点追踪' mode")
                time.sleep(2)
                take_screenshot(page, "08_moments_hot")
            else:
                log("'热点追踪' mode not found", "WARN")
        except Exception as e:
            log(f"Error with 热点追踪: {e}", "ERROR")

        # ============================================================
        # 4. Test Tab 2: 短视频中心
        # ============================================================
        log("=== Testing Tab: 短视频中心 ===")
        try:
            video_tab = page.locator('button:has-text("短视频中心")').first
            if video_tab.is_visible():
                video_tab.click()
                log("Clicked '短视频中心' tab")
                time.sleep(2)
                take_screenshot(page, "09_tab_video")
            else:
                log("'短视频中心' tab not found", "WARN")
        except Exception as e:
            log(f"Error with 短视频中心 tab: {e}", "ERROR")

        # ============================================================
        # 5. Test Tab 3: 海报工坊
        # ============================================================
        log("=== Testing Tab: 海报工坊 ===")
        try:
            poster_tab = page.locator('button:has-text("海报工坊")').first
            if poster_tab.is_visible():
                poster_tab.click()
                log("Clicked '海报工坊' tab")
                time.sleep(2)
                take_screenshot(page, "10_tab_poster")
            else:
                log("'海报工坊' tab not found", "WARN")
        except Exception as e:
            log(f"Error with 海报工坊 tab: {e}", "ERROR")

        # ============================================================
        # 6. Test Tab 4: 素材库
        # ============================================================
        log("=== Testing Tab: 素材库 ===")
        try:
            assets_tab = page.locator('button:has-text("素材库")').first
            if assets_tab.is_visible():
                assets_tab.click()
                log("Clicked '素材库' tab")
                time.sleep(2)
                take_screenshot(page, "11_tab_assets")
            else:
                log("'素材库' tab not found", "WARN")
        except Exception as e:
            log(f"Error with 素材库 tab: {e}", "ERROR")

        # Test Sub-tab 1: 品牌素材
        log("--- Testing Sub-tab: 品牌素材 ---")
        try:
            brand_sub = page.locator('label:has-text("品牌素材")').first
            if brand_sub.is_visible():
                brand_sub.click()
                log("Selected '品牌素材' sub-tab")
                time.sleep(2)
                take_screenshot(page, "12_assets_brand")
            else:
                log("'品牌素材' sub-tab not found", "WARN")
        except Exception as e:
            log(f"Error with 品牌素材: {e}", "ERROR")

        # Test Sub-tab 2: 产品知识卡片
        log("--- Testing Sub-tab: 产品知识卡片 ---")
        try:
            knowledge_sub = page.locator('label:has-text("产品知识卡片")').first
            if knowledge_sub.is_visible():
                knowledge_sub.click()
                log("Selected '产品知识卡片' sub-tab")
                time.sleep(2)
                take_screenshot(page, "13_assets_knowledge")
            else:
                log("'产品知识卡片' sub-tab not found", "WARN")
        except Exception as e:
            log(f"Error with 产品知识卡片: {e}", "ERROR")

        # Test Sub-tab 3: 竞品内容收藏
        log("--- Testing Sub-tab: 竞品内容收藏 ---")
        try:
            competitor_sub = page.locator('label:has-text("竞品内容收藏")').first
            if competitor_sub.is_visible():
                competitor_sub.click()
                log("Selected '竞品内容收藏' sub-tab")
                time.sleep(2)
                take_screenshot(page, "14_assets_competitor")
            else:
                log("'竞品内容收藏' sub-tab not found", "WARN")
        except Exception as e:
            log(f"Error with 竞品内容收藏: {e}", "ERROR")

        # Test Sub-tab 4: 社交平台监控
        log("--- Testing Sub-tab: 社交平台监控 ---")
        try:
            social_sub = page.locator('label:has-text("社交平台监控")').first
            if social_sub.is_visible():
                social_sub.click()
                log("Selected '社交平台监控' sub-tab")
                time.sleep(2)
                take_screenshot(page, "15_assets_social")
            else:
                log("'社交平台监控' sub-tab not found", "WARN")
        except Exception as e:
            log(f"Error with 社交平台监控: {e}", "ERROR")

        # Test Sub-tab 5: 竞品分析报告
        log("--- Testing Sub-tab: 竞品分析报告 ---")
        try:
            report_sub = page.locator('label:has-text("竞品分析报告")').first
            if report_sub.is_visible():
                report_sub.click()
                log("Selected '竞品分析报告' sub-tab")
                time.sleep(2)
                take_screenshot(page, "16_assets_report")
            else:
                log("'竞品分析报告' sub-tab not found", "WARN")
        except Exception as e:
            log(f"Error with 竞品分析报告: {e}", "ERROR")

        # ============================================================
        # 7. Test Tab 5: 数字员工
        # ============================================================
        log("=== Testing Tab: 数字员工 ===")
        try:
            # Look for tab with emoji or text
            digital_tab = page.locator('button:has-text("数字员工")').first
            if not digital_tab.is_visible():
                digital_tab = page.locator('button:has-text("🤖")').first
            if digital_tab.is_visible():
                digital_tab.click()
                log("Clicked '数字员工' tab")
                time.sleep(2)
                take_screenshot(page, "17_tab_digital")
            else:
                log("'数字员工' tab not found", "WARN")
        except Exception as e:
            log(f"Error with 数字员工 tab: {e}", "ERROR")

        # ============================================================
        # Final error check
        # ============================================================
        errors = check_for_errors(page)
        for e in errors:
            log(e, "ERROR")

        browser.close()

    # Write report
    report_path = SCREENSHOT_DIR / "report.txt"
    with open(report_path, "w") as f:
        for entry in REPORT:
            f.write(f"[{entry['level']}] {entry['msg']}\n")

    log(f"\nAll screenshots saved to: {SCREENSHOT_DIR}")
    log(f"Report saved to: {report_path}")

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    errors_count = sum(1 for e in REPORT if e['level'] == 'ERROR')
    warns_count = sum(1 for e in REPORT if e['level'] == 'WARN')
    print(f"Total log entries: {len(REPORT)}")
    print(f"Errors: {errors_count}")
    print(f"Warnings: {warns_count}")
    print(f"Screenshots directory: {SCREENSHOT_DIR}")

    return errors_count == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
