"""
HTML → PNG 渲染服务

基于 html2image + Chrome headless 将 HTML/CSS 渲染为 PNG 图片。
支持原始HTML渲染和模板渲染（从 assets/templates/ 加载）。

用法：
    from services.html_renderer import render_template, render_html_to_png
    result = render_template("moment_card", {"content": "文案内容", ...})
    if result["success"]:
        with open("card.png", "wb") as f:
            f.write(result["png_bytes"])
"""

import os
import shutil
import tempfile

# ---- 动态导入 ----
_HAS_HTML2IMAGE = False

try:
    from html2image import Html2Image
    _HAS_HTML2IMAGE = True
except Exception:
    pass

# 模板目录
_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "templates"
)

# Chrome 查找路径（macOS）
_CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]


def _find_chrome() -> str | None:
    """查找 Chrome/Chromium 可执行文件"""
    for p in _CHROME_PATHS:
        if os.path.exists(p):
            return p
    return None


def _empty_result(error: str = "") -> dict:
    return {
        "success": False,
        "png_bytes": None,
        "width": 0,
        "height": 0,
        "error": error,
    }


def render_html_to_png(html: str, css: str = "",
                       width: int = 375, height: int = 667) -> dict:
    """
    将 HTML 字符串渲染为 PNG。

    Args:
        html: HTML内容
        css: 可选CSS样式
        width: 图片宽度(px)
        height: 图片高度(px)

    Returns:
        {"success": bool, "png_bytes": bytes|None, "width": int, "height": int, "error": str}
    """
    if not _HAS_HTML2IMAGE:
        return _empty_result("html2image 未安装，请运行 pip install html2image")

    chrome = _find_chrome()
    if not chrome:
        return _empty_result("未找到 Chrome/Chromium 浏览器")

    tmp_dir = tempfile.mkdtemp()
    try:
        hti = Html2Image(
            output_path=tmp_dir,
            browser_executable=chrome,
            custom_flags=[
                "--no-sandbox",
                "--disable-gpu",
                "--hide-scrollbars",
            ],
        )

        output_file = "render.png"
        hti.screenshot(
            html_str=html,
            css_str=css,
            save_as=output_file,
            size=(width, height),
        )

        output_path = os.path.join(tmp_dir, output_file)
        if not os.path.exists(output_path):
            return _empty_result("渲染失败：未生成输出文件")

        with open(output_path, "rb") as f:
            png_bytes = f.read()

        if len(png_bytes) < 100:
            return _empty_result("渲染失败：输出文件过小")

        return {
            "success": True,
            "png_bytes": png_bytes,
            "width": width,
            "height": height,
            "error": "",
        }

    except Exception as e:
        return _empty_result(f"渲染失败: {str(e)[:200]}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def render_template(template_name: str, context: dict,
                    width: int = 375, height: int = 667) -> dict:
    """
    从 assets/templates/ 加载HTML模板，替换变量后渲染为PNG。

    Args:
        template_name: 模板名称（不含.html后缀）
        context: 模板变量字典
        width: 图片宽度
        height: 图片高度
    """
    template_path = os.path.join(_TEMPLATES_DIR, f"{template_name}.html")
    if not os.path.exists(template_path):
        return _empty_result(f"模板不存在: {template_name}.html")

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html = f.read()

        # 用 safe_substitute 风格替换：{key} → value
        for key, value in context.items():
            html = html.replace("{" + key + "}", str(value))

        return render_html_to_png(html, width=width, height=height)

    except Exception as e:
        return _empty_result(f"模板渲染失败: {str(e)[:200]}")


def is_available() -> bool:
    """html2image 和 Chrome 是否都可用"""
    return _HAS_HTML2IMAGE and _find_chrome() is not None


def get_status() -> str:
    """返回当前状态"""
    parts = []
    parts.append("html2image ✓" if _HAS_HTML2IMAGE else "html2image ✗")
    parts.append("Chrome ✓" if _find_chrome() else "Chrome ✗")
    return " | ".join(parts)
