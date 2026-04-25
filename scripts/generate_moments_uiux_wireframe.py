"""
生成发朋友圈数字员工移动端验收截图。

用途：
- 对本地 Streamlit 页面做 390px 宽度的 Chrome headless 可视化参考截图。
- 截图仅作为参考；若 Streamlit 停留骨架屏，需按 07_Test_Cases.md 做人工浏览器验收。

运行示例：
    .venv/bin/python scripts/generate_moments_uiux_wireframe.py --url http://127.0.0.1:8502
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


DEFAULT_CHROME_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)


def find_chrome() -> str | None:
    for candidate in DEFAULT_CHROME_PATHS:
        if Path(candidate).exists():
            return candidate
    return shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chrome")


def generate_screenshot(url: str, output: Path, *, width: int = 390, height: int = 1000) -> int:
    chrome = find_chrome()
    if not chrome:
        print("未找到 Chrome/Chromium，跳过截图生成。")
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=10000",
        f"--screenshot={output}",
        f"--window-size={width},{height}",
        url,
    ]
    result = subprocess.run(command, check=False)
    if result.returncode == 0 and output.exists():
        print(f"截图已生成：{output}")
        print("说明：Chrome headless 可能只捕获 Streamlit 骨架屏，最终移动端验收仍以人工浏览器检查为准。")
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 moments 移动端验收截图")
    parser.add_argument("--url", default="http://127.0.0.1:8502")
    parser.add_argument("--output", default="/tmp/moments_mobile_check.png")
    parser.add_argument("--width", type=int, default=390)
    parser.add_argument("--height", type=int, default=1000)
    args = parser.parse_args()

    return generate_screenshot(
        args.url,
        Path(args.output),
        width=args.width,
        height=args.height,
    )


if __name__ == "__main__":
    raise SystemExit(main())
