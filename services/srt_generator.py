"""
SRT 字幕文件生成器

将带时间标记的脚本转换为标准 SRT 字幕格式。
支持两种输入：
1. 带【MM:SS-MM:SS 标签】标记的脚本 → 按标记切分
2. 纯文本 → 按句子自动均分时间
"""

import re


def parse_time_markers(script_text: str) -> list[dict]:
    """提取脚本中的时间标记和对应文本。

    格式：【0:00-0:03 钩子】文本内容
    或：  【00:00-00:03 钩子】文本内容

    Returns:
        [{"start_sec": 0.0, "end_sec": 3.0, "label": "钩子", "text": "文本内容"}]
    """
    pattern = r"【(\d{1,2}:\d{2})-(\d{1,2}:\d{2})\s*([^】]*)】([^【]*)"
    matches = re.findall(pattern, script_text)

    segments = []
    for start_str, end_str, label, text in matches:
        start_sec = _time_to_sec(start_str)
        end_sec = _time_to_sec(end_str)
        clean_text = text.strip().replace("\n", " ")
        if clean_text:
            segments.append({
                "start_sec": start_sec,
                "end_sec": end_sec,
                "label": label.strip(),
                "text": clean_text,
            })
    return segments


def _time_to_sec(time_str: str) -> float:
    """将 MM:SS 或 M:SS 转为秒数"""
    parts = time_str.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0.0


def _sec_to_srt_time(sec: float) -> str:
    """将秒数转为 SRT 时间格式 HH:MM:SS,mmm"""
    hours = int(sec // 3600)
    minutes = int((sec % 3600) // 60)
    seconds = int(sec % 60)
    millis = int((sec % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _split_text_to_sentences(text: str) -> list[str]:
    """将文本切分为句子（中文标点 + 换行）"""
    sentences = re.split(r"[。！？\n]+", text)
    return [s.strip() for s in sentences if s.strip()]


def generate_srt(script_text: str, total_duration_sec: int = 30) -> str:
    """生成 SRT 字幕内容。

    Args:
        script_text: 脚本文本（可含【MM:SS-MM:SS】标记，也可纯文本）
        total_duration_sec: 总时长（秒），纯文本模式下用于均分时间

    Returns:
        标准 SRT 格式字符串
    """
    # 尝试解析时间标记
    segments = parse_time_markers(script_text)

    if not segments:
        # 无时间标记 → 自动均分
        sentences = _split_text_to_sentences(script_text)
        if not sentences:
            return ""

        seg_duration = total_duration_sec / len(sentences)
        for i, sentence in enumerate(sentences):
            # 每条字幕不超过2行，每行不超过20字
            lines = _wrap_text(sentence, max_chars=20)
            segments.append({
                "start_sec": i * seg_duration,
                "end_sec": (i + 1) * seg_duration,
                "label": "",
                "text": "\n".join(lines),
            })
    else:
        # 有时间标记 → 每段内再按句子细分字幕
        fine_segments = []
        for seg in segments:
            sentences = _split_text_to_sentences(seg["text"])
            if not sentences:
                continue
            seg_total = seg["end_sec"] - seg["start_sec"]
            sub_dur = seg_total / len(sentences)
            for j, sentence in enumerate(sentences):
                lines = _wrap_text(sentence, max_chars=20)
                fine_segments.append({
                    "start_sec": seg["start_sec"] + j * sub_dur,
                    "end_sec": seg["start_sec"] + (j + 1) * sub_dur,
                    "label": seg["label"],
                    "text": "\n".join(lines),
                })
        segments = fine_segments

    # 生成 SRT
    srt_lines = []
    for i, seg in enumerate(segments, 1):
        start = _sec_to_srt_time(seg["start_sec"])
        end = _sec_to_srt_time(seg["end_sec"])
        srt_lines.append(f"{i}")
        srt_lines.append(f"{start} --> {end}")
        srt_lines.append(seg["text"])
        srt_lines.append("")

    return "\n".join(srt_lines)


def _wrap_text(text: str, max_chars: int = 20) -> list[str]:
    """将长文本折行，每行不超过max_chars个字符"""
    if len(text) <= max_chars:
        return [text]

    lines = []
    while text:
        if len(text) <= max_chars:
            lines.append(text)
            break
        # 在max_chars附近找标点断句
        cut = max_chars
        for punct in "，、；：。！？ ":
            idx = text.rfind(punct, 0, max_chars + 2)
            if idx > max_chars // 2:
                cut = idx + 1
                break
        lines.append(text[:cut].strip())
        text = text[cut:].strip()

    return lines[:3]  # 最多3行
