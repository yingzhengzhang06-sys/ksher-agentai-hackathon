"""
图像生成服务 — 封装国内文生图API

当前支持：阿里云百炼通义万相（wan2.7-image-pro / wanx-v1）
用途：生成海报背景底图（无文字、纯视觉元素）

.env 配置：
    DASHSCOPE_API_KEY=sk-xxxx
"""

import os
import time
import base64
import requests
from typing import Optional

from config import MATERIALS_DIR

# ============================================================
# 配置
# ============================================================

_DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"

# 海报竖版 9:16 分辨率映射（通义万相2.7支持的尺寸：2K / 4K）
_POSTER_SIZE = "2K"  # 文生图支持 2K（混合推理）/ 4K（仅文生图）


# ============================================================
# 工具函数
# ============================================================

def is_image_api_available() -> bool:
    """检查是否配置了文生图API Key"""
    return bool(_DASHSCOPE_API_KEY)


def _headers(async_mode: bool = False) -> dict:
    h = {
        "Authorization": f"Bearer {_DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }
    if async_mode:
        h["X-DashScope-Async"] = "enable"
    return h


def _generate_sync(prompt: str, size: str = _POSTER_SIZE, n: int = 1) -> dict:
    """
    同步调用文生图 API。
    返回 {"success": bool, "image_url": str, "error": str}
    """
    url = f"{_DASHSCOPE_BASE_URL}/services/aigc/multimodal-generation/generation"
    payload = {
        "model": "wan2.7-image-pro",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ]
        },
        "parameters": {
            "size": size,
            "n": n,
            "watermark": False,
        },
    }
    try:
        resp = requests.post(url, headers=_headers(), json=payload, timeout=120)
        data = resp.json()
        if resp.status_code == 200:
            choices = data.get("output", {}).get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", [])
                for item in content:
                    if item.get("type") == "image":
                        return {"success": True, "image_url": item.get("image", ""), "error": ""}
            return {"success": False, "image_url": "", "error": "API 返回成功但未包含图片 URL"}
        err_msg = data.get("message", f"HTTP {resp.status_code}")
        return {"success": False, "image_url": "", "error": err_msg}
    except Exception as e:
        return {"success": False, "image_url": "", "error": str(e)}


def _query_task(task_id: str) -> dict:
    """
    查询任务状态。
    返回 {"success": bool, "status": str, "image_url": str, "error": str}
    status: PENDING / RUNNING / SUCCEEDED / FAILED
    """
    url = f"{_DASHSCOPE_BASE_URL}/tasks/{task_id}"
    try:
        resp = requests.get(url, headers=_headers(), timeout=30)
        data = resp.json()
        if resp.status_code != 200:
            return {
                "success": False,
                "status": "FAILED",
                "image_url": "",
                "error": data.get("message", f"HTTP {resp.status_code}"),
            }

        output = data.get("output", {})
        status = output.get("task_status", "UNKNOWN")

        if status == "SUCCEEDED":
            results = output.get("results", [])
            if results:
                return {
                    "success": True,
                    "status": status,
                    "image_url": results[0].get("url", ""),
                    "error": "",
                }
            return {
                "success": False,
                "status": "FAILED",
                "image_url": "",
                "error": "任务成功但未返回图片URL",
            }

        if status == "FAILED":
            return {
                "success": False,
                "status": "FAILED",
                "image_url": "",
                "error": output.get("message", "任务执行失败"),
            }

        return {"success": True, "status": status, "image_url": "", "error": ""}
    except Exception as e:
        return {"success": False, "status": "FAILED", "image_url": "", "error": str(e)}


def _download_image(image_url: str, save_path: str) -> dict:
    """下载图片到本地"""
    try:
        resp = requests.get(image_url, timeout=60)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return {"success": True, "path": save_path, "error": ""}
        return {"success": False, "path": "", "error": f"下载失败 HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "path": "", "error": str(e)}


# ============================================================
# 主接口
# ============================================================

def generate_poster_background(
    prompt: str,
    size: str = _POSTER_SIZE,
    max_wait_seconds: int = 120,
    poll_interval: int = 3,
) -> dict:
    """
    生成海报背景底图。

    流程：同步调用 API → 下载图片

    Args:
        prompt: 背景图描述（必须要求无文字、纯视觉）
        size: 分辨率（默认 2K）
        max_wait_seconds: 保留参数（同步模式不使用）
        poll_interval: 保留参数（同步模式不使用）

    Returns:
        {"success": bool, "image_path": str, "error": str}
        image_path: 本地保存的PNG路径
    """
    if not is_image_api_available():
        return {"success": False, "image_path": "", "error": "未配置 DASHSCOPE_API_KEY"}

    # 1. 同步调用生成
    gen = _generate_sync(prompt, size=size)
    if not gen["success"]:
        return {"success": False, "image_path": "", "error": f"生成失败：{gen['error']}"}

    image_url = gen["image_url"]
    if not image_url:
        return {"success": False, "image_path": "", "error": "API 未返回图片 URL"}

    # 2. 下载图片
    import hashlib
    url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
    save_path = os.path.join(MATERIALS_DIR, "bg", f"poster_bg_{url_hash}.png")
    dl = _download_image(image_url, save_path)
    # 统一返回 key 名
    if dl["success"]:
        return {"success": True, "image_path": dl["path"], "error": ""}
    return dl


def image_to_base64(image_path: str) -> str:
    """将本地图片转为 base64 data URL"""
    with open(image_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    ext = os.path.splitext(image_path)[1].lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{b64}"


# ============================================================
# Prompt 构建工具
# ============================================================

def build_background_prompt(user_request: str, style_hint: str = "") -> str:
    """
    根据用户需求构建文生图背景prompt。
    自动添加约束：无文字、适合叠加文字、商务风格。
    """
    base = (
        "Abstract business poster background, clean and modern design, "
        "suitable for text overlay on top and center areas, "
        "NO text, NO letters, NO numbers, NO watermarks, "
        "soft gradient colors, geometric decorative elements, "
        "minimalist professional style, high quality, 8k, "
    )

    style = style_hint or "red and orange gradient tones with subtle geometric patterns"

    return f"{base}{style}. Theme: {user_request}"
