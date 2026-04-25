"""
语音/视频转文字服务

基于 faster-whisper（CTranslate2 加速版 Whisper）实现本地语音识别。
支持音频(mp3/wav/m4a/ogg)和视频(mp4/webm/mov，需ffmpeg提取音频)。

用法：
    from services.audio_transcriber import transcribe_file, is_available
    if is_available():
        result = transcribe_file(file_bytes, "meeting.mp3")
        if result["success"]:
            print(result["text"])
"""

import os
import shutil
import subprocess
import tempfile
from typing import List

# ---- 动态导入 ----
_HAS_FASTER_WHISPER = False

try:
    from faster_whisper import WhisperModel
    _HAS_FASTER_WHISPER = True
except Exception:
    pass

_HAS_FFMPEG = shutil.which("ffmpeg") is not None

# 模型缓存（首次加载后复用）
_model_cache = {}

# 支持的格式
AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac")
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".avi", ".mkv")
ALL_EXTENSIONS = AUDIO_EXTENSIONS + VIDEO_EXTENSIONS


def _empty_result(error: str = "") -> dict:
    return {
        "success": False,
        "text": "",
        "language": "",
        "language_prob": 0.0,
        "duration_sec": 0.0,
        "segments": [],
        "error": error,
    }


def _get_model(model_size: str = "base"):
    """获取或创建 Whisper 模型实例（缓存）"""
    if model_size not in _model_cache:
        _model_cache[model_size] = WhisperModel(
            model_size, device="cpu", compute_type="int8"
        )
    return _model_cache[model_size]


def _extract_audio_from_video(video_path: str, output_wav: str) -> bool:
    """用 ffmpeg 从视频中提取音频为 WAV"""
    try:
        subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-vn",                    # 不要视频
                "-acodec", "pcm_s16le",   # 16-bit PCM
                "-ar", "16000",           # 16kHz采样率
                "-ac", "1",               # 单声道
                "-y",                     # 覆盖
                output_wav,
            ],
            capture_output=True,
            timeout=120,
        )
        return os.path.exists(output_wav) and os.path.getsize(output_wav) > 0
    except Exception:
        return False


def transcribe_file(file_bytes: bytes, filename: str,
                    model_size: str = "base") -> dict:
    """
    转录音频/视频文件。

    Args:
        file_bytes: 文件二进制内容
        filename: 原始文件名（用于判断格式）
        model_size: Whisper模型大小 ("tiny"/"base"/"small"/"medium")

    Returns:
        {
            "success": bool,
            "text": str,
            "language": str,
            "language_prob": float,
            "duration_sec": float,
            "segments": [{"start": float, "end": float, "text": str}],
            "error": str,
        }
    """
    if not _HAS_FASTER_WHISPER:
        return _empty_result("faster-whisper 未安装，请运行 pip install faster-whisper")

    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALL_EXTENSIONS:
        return _empty_result(f"不支持的格式: {ext}，支持: {', '.join(ALL_EXTENSIONS)}")

    is_video = ext in VIDEO_EXTENSIONS
    if is_video and not _HAS_FFMPEG:
        return _empty_result("处理视频文件需要 ffmpeg，请运行 brew install ffmpeg")

    tmp_dir = tempfile.mkdtemp()
    try:
        # 写入临时文件
        input_path = os.path.join(tmp_dir, f"input{ext}")
        with open(input_path, "wb") as f:
            f.write(file_bytes)

        # 视频 → 提取音频
        audio_path = input_path
        if is_video:
            audio_path = os.path.join(tmp_dir, "audio.wav")
            if not _extract_audio_from_video(input_path, audio_path):
                return _empty_result("ffmpeg 提取音频失败，请检查视频文件是否有效")

        # 加载模型并转录
        model = _get_model(model_size)
        segments_iter, info = model.transcribe(audio_path, beam_size=5)

        # 拼接结果
        segments: List[dict] = []
        text_parts: List[str] = []
        last_end = 0.0

        for seg in segments_iter:
            segments.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
            })
            text_parts.append(seg.text.strip())
            last_end = seg.end

        full_text = " ".join(text_parts)

        return {
            "success": True,
            "text": full_text,
            "language": info.language or "",
            "language_prob": round(info.language_probability or 0.0, 3),
            "duration_sec": round(last_end, 1),
            "segments": segments,
            "error": "",
        }

    except Exception as e:
        return _empty_result(f"转录失败: {str(e)[:200]}")
    finally:
        # 清理临时文件
        shutil.rmtree(tmp_dir, ignore_errors=True)


def is_available() -> bool:
    """faster-whisper 是否可用"""
    return _HAS_FASTER_WHISPER


def ffmpeg_available() -> bool:
    """ffmpeg 是否可用"""
    return _HAS_FFMPEG


def get_status() -> str:
    """返回当前状态"""
    parts = []
    parts.append("faster-whisper ✓" if _HAS_FASTER_WHISPER else "faster-whisper ✗")
    parts.append("ffmpeg ✓" if _HAS_FFMPEG else "ffmpeg ✗")
    return " | ".join(parts)
