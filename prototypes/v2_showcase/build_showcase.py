#!/usr/bin/env python3
"""Build the 72-second V2 technology showcase video."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import subprocess
import wave
from pathlib import Path
from typing import Any

import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TIMELINE = Path(__file__).with_name("timeline.json")
FONT_BOLD = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
FONT_REGULAR = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
VOICE = "zh-CN-YunjianNeural"
RATE = "+18%"
SR = 44100
BGM_VOL = 0.08
CARD_FILTER_PREFIX = "scale=7680:4320:flags=lanczos,zoompan"
FINAL_FILENAME = "驭远智擎_专属RAG科技成果展示版_PPT风格修正版.mp4"

PPT_BLUE = (52, 88, 165)
PPT_DARK_BLUE = (18, 54, 112)
PPT_LIGHT_BLUE = (224, 231, 245)
PPT_RED = (205, 10, 18)
PPT_YELLOW = (255, 235, 0)
PPT_TEXT = (20, 25, 35)
PPT_GRAY = (246, 247, 249)


def load_timeline(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("source_main", "source_generalization", "output_dir"):
        data[key] = os.path.expandvars(data[key])
    return data


def require_runtime_paths(data: dict[str, Any]) -> None:
    for key in ("source_main", "source_generalization", "output_dir"):
        if "$" in data[key]:
            raise ValueError(f"unresolved environment variable in {key}: {data[key]}")


def validate_timeline(data: dict[str, Any]) -> None:
    duration = float(data["duration"])
    if duration != 72.0:
        raise ValueError("showcase duration must be 72 seconds")
    visuals = data["visuals"]
    if not visuals or visuals[0]["start"] != 0 or visuals[-1]["end"] != duration:
        raise ValueError("visual timeline must cover the full duration")
    for first, second in zip(visuals, visuals[1:]):
        if float(first["end"]) != float(second["start"]):
            raise ValueError("visual timeline must be contiguous")
    for visual in visuals:
        if float(visual["start"]) >= float(visual["end"]):
            raise ValueError(f"invalid visual segment: {visual['id']}")
    for narration in data["narration"]:
        if not 0 <= float(narration["start"]) < float(narration["end_limit"]) <= duration:
            raise ValueError(f"narration outside timeline: {narration['id']}")
    required_metrics = {
        "index_blocks": 1817,
        "four_before": 85.8,
        "four_after": 96.5,
        "general_before": 60,
        "general_after": 89,
        "variance_before": 83,
        "variance_after": 29,
        "traceable": "9/9",
    }
    if data["metrics"] != required_metrics:
        raise ValueError("metrics differ from the authoritative project report")


def run(command: list[str]) -> None:
    print("运行：", " ".join(command))
    subprocess.run(command, check=True)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


def background() -> Image.Image:
    width, height = 1920, 1080
    image = Image.new("RGB", (width, height), (252, 252, 252))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, width, 12), fill=PPT_BLUE)
    draw.rectangle((0, 12, width, 18), fill=(104, 133, 194))
    return image


def pill(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, color: str) -> None:
    colors = {
        "blue": (PPT_BLUE, PPT_DARK_BLUE, (255, 255, 255)),
        "green": (PPT_LIGHT_BLUE, PPT_BLUE, PPT_DARK_BLUE),
        "orange": ((255, 239, 224), PPT_RED, PPT_RED),
    }
    fill, outline, text_fill = colors[color]
    draw.rounded_rectangle(box, radius=12, fill=fill, outline=outline, width=3)
    draw.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 - 2), text, font=font(32, True), fill=text_fill, anchor="mm")


def title(draw: ImageDraw.ImageDraw, kicker: str, headline: str, subline: str = "") -> None:
    draw.text((84, 62), kicker, font=font(26, True), fill=PPT_BLUE)
    draw.text((84, 116), headline, font=font(68, True), fill=PPT_TEXT)
    draw.rectangle((84, 222, 1836, 228), fill=PPT_BLUE)
    if subline:
        draw.text((84, 258), subline, font=font(32), fill=PPT_DARK_BLUE)


def conclusion_bar(draw: ImageDraw.ImageDraw, lead: str, detail: str) -> None:
    draw.rectangle((80, 805, 1840, 875), fill=PPT_BLUE)
    draw.text((118, 840), lead, font=font(28, True), fill=PPT_YELLOW, anchor="lm")
    lead_width = draw.textbbox((0, 0), lead, font=font(28, True))[2]
    draw.text((140 + lead_width, 840), detail, font=font(28), fill="white", anchor="lm")


def render_card(card_id: str, destination: Path) -> None:
    image = background()
    draw = ImageDraw.Draw(image, "RGBA")
    if card_id == "hero":
        draw.rectangle((0, 18, 1920, 210), fill=PPT_BLUE)
        draw.text((960, 92), "驭远智擎 · 专属 RAG", font=font(38, True), fill="white", anchor="mm")
        draw.text((960, 158), "教材知识增强与真实问答验证", font=font(28), fill=PPT_YELLOW, anchor="mm")
        draw.text((960, 340), "回答更准确", font=font(102, True), fill=PPT_TEXT, anchor="mm")
        draw.text((960, 475), "证据可追溯", font=font(102, True), fill=PPT_RED, anchor="mm")
        pill(draw, (420, 610, 850, 700), "2 本核心教材", "blue")
        pill(draw, (900, 610, 1500, 700), "1817 个知识块", "green")
        draw.rectangle((0, 790, 1920, 798), fill=PPT_RED)
        draw.rectangle((0, 798, 1920, 806), fill=PPT_BLUE)
        draw.text((960, 855), "发动机原理 × 电动汽车原理与构造", font=font(34), fill=PPT_DARK_BLUE, anchor="mm")
    elif card_id == "pipeline":
        title(draw, "技术流程", "专属 RAG 如何工作", "让答案回到教材证据链")
        labels = [("问题理解", "01"), ("检索 40 候选", "02"), ("交叉重新排序", "03"), ("证据注入", "04")]
        for index, (label, number) in enumerate(labels):
            x = 105 + index * 445
            draw.rounded_rectangle((x, 390, x + 360, 650), radius=14, fill=PPT_GRAY, outline=PPT_BLUE, width=3)
            draw.rectangle((x, 390, x + 360, 455), fill=PPT_BLUE)
            draw.text((x + 30, 423), number, font=font(26, True), fill=PPT_YELLOW, anchor="lm")
            label_color = PPT_RED if number == "03" else PPT_TEXT
            label_font = 34 if number == "03" else 38
            draw.text((x + 180, 548), label, font=font(label_font, True), fill=label_color, anchor="mm")
            if index < 3:
                draw.line((x + 372, 520, x + 420, 520), fill=PPT_BLUE, width=6)
                draw.polygon(((x + 420, 520), (x + 402, 508), (x + 402, 532)), fill=PPT_BLUE)
        pill(draw, (650, 720, 1270, 805), "最相关证据 · 最多注入 10 块", "green")
        conclusion_bar(draw, "流程闭环：", "检索、重新排序、证据注入")
    elif card_id == "four_metrics":
        title(draw, "真实题验证", "四道真实题，结果更可靠", "覆盖教材 PPT 与课后习题")
        draw.text((575, 520), "85.8%", font=font(116, True), fill=PPT_TEXT, anchor="mm")
        draw.text((960, 520), "→", font=font(90, True), fill=PPT_RED, anchor="mm")
        draw.text((1345, 520), "96.5%", font=font(116, True), fill=PPT_BLUE, anchor="mm")
        pill(draw, (230, 670, 675, 755), "E5  43% → 86%", "orange")
        pill(draw, (735, 670, 1185, 755), "其余三题 100%", "blue")
        pill(draw, (1245, 670, 1690, 755), "引用全部提升", "green")
        conclusion_bar(draw, "验证结果：", "平均命中率提升，回答出处更完整")
    elif card_id == "gen_intro":
        title(draw, "泛化能力测试", "不是背答案，而是理解问题", "同一知识点，换三种表达方式")
        for index, (label, detail) in enumerate((("直问", "标准提问"), ("口语化", "自然表达"), ("设问", "换角度追问"))):
            x = 250 + index * 500
            draw.rounded_rectangle((x, 405, x + 410, 690), radius=14, fill=PPT_GRAY, outline=PPT_BLUE, width=3)
            draw.rectangle((x, 405, x + 410, 480), fill=PPT_BLUE)
            draw.text((x + 205, 443), label, font=font(42, True), fill=PPT_YELLOW, anchor="mm")
            draw.text((x + 205, 585), detail, font=font(34), fill=PPT_TEXT, anchor="mm")
        conclusion_bar(draw, "检验目标：", "换一种问法，仍能稳定命中")
    elif card_id == "final_metrics":
        title(draw, "量化结果", "换一种问法，依然稳定命中", "三知识点 × 三问法 · 九问验证")
        metrics = (("60% → 89%", "平均命中率"), ("83pp → 29pp", "跨问法波动"), ("9 / 9", "引用可溯源"))
        for index, (value, label) in enumerate(metrics):
            x = 180 + index * 570
            draw.rounded_rectangle((x, 395, x + 470, 700), radius=12, fill=PPT_LIGHT_BLUE, outline=PPT_BLUE, width=3)
            draw.rectangle((x, 395, x + 470, 465), fill=PPT_BLUE)
            draw.text((x + 235, 565), value, font=font(64, True), fill=PPT_RED if index == 0 else PPT_TEXT, anchor="mm")
            draw.text((x + 235, 650), label, font=font(32, True), fill=PPT_DARK_BLUE, anchor="mm")
        conclusion_bar(draw, "总体结论：", "准确度提升、稳定性增强、证据链完整")
    elif card_id == "ending":
        draw.rectangle((0, 18, 1920, 355), fill=PPT_BLUE)
        draw.text((960, 145), "驭远智擎", font=font(92, True), fill="white", anchor="mm")
        draw.text((960, 255), "让专业回答更可靠", font=font(56, True), fill=PPT_YELLOW, anchor="mm")
        draw.text((960, 505), "让每个结论都有依据", font=font(70, True), fill=PPT_TEXT, anchor="mm")
        draw.rectangle((0, 625, 1920, 634), fill=PPT_RED)
        draw.rectangle((0, 634, 1920, 643), fill=PPT_BLUE)
        pill(draw, (610, 720, 1310, 810), "准确 · 稳定 · 可溯源", "blue")
    else:
        raise ValueError(f"unknown card: {card_id}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, quality=96)


def render_label(text: str, destination: Path) -> None:
    image = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    text_font = font(36, True)
    bbox = draw.textbbox((0, 0), text, font=text_font)
    width = bbox[2] - bbox[0] + 70
    left = 1856 - width
    draw.rounded_rectangle((left, 70, 1856, 142), radius=12, fill=(*PPT_BLUE, 238), outline=(*PPT_DARK_BLUE, 255), width=3)
    draw.text((left + 35, 106), text, font=text_font, fill="white", anchor="lm")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


def build_card_segment(card: Path, output: Path, duration: float, fps: int) -> None:
    frames = int(round(duration * fps))
    zoom = f"1.0+0.025*on/{max(1, frames - 1)}"
    vf = (
        f"scale=7680:4320:flags=lanczos,zoompan=z='{zoom}':"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d=1:s=1920x1080:fps={fps},format=yuv420p"
    )
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-loop", "1", "-framerate", str(fps), "-i", str(card), "-t", f"{duration:.3f}", "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(output)])


def build_source_segment(source: Path, visual: dict[str, Any], label: Path, output: Path, fps: int) -> None:
    output_duration = float(visual["end"] - visual["start"])
    source_duration = float(visual["source_duration"])
    speed = output_duration / source_duration
    graph = (
        f"[0:v]setpts={speed:.8f}*PTS,fps={fps},scale=1920:1080:flags=lanczos,setsar=1[base];"
        "[1:v]format=rgba[label];[base][label]overlay=0:0:shortest=1,format=yuv420p[v]"
    )
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-ss", f"{visual['source_start']:.3f}", "-t", f"{source_duration:.3f}", "-i", str(source), "-loop", "1", "-framerate", str(fps), "-i", str(label), "-filter_complex", graph, "-map", "[v]", "-t", f"{output_duration:.3f}", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(output)])


def concat_segments(segment_paths: list[Path], output: Path, work_dir: Path) -> None:
    concat_file = work_dir / "concat.txt"
    concat_file.write_text("".join(f"file '{path}'\n" for path in segment_paths), encoding="utf-8")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", "-t", "72.000", str(output)])


async def generate_tts_files(data: dict[str, Any], audio_dir: Path) -> dict[str, Path]:
    audio_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for narration in data["narration"]:
        path = audio_dir / f"{narration['id']}.mp3"
        await edge_tts.Communicate(narration["text"], VOICE, rate=RATE).save(str(path))
        paths[narration["id"]] = path
    return paths


def media_duration(path: Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)], text=True, capture_output=True, check=True)
    return float(result.stdout.strip())


def split_subtitle(text: str, limit: int = 20) -> list[str]:
    clean = re.sub(r"[。！？；]+", "|", text)
    parts: list[str] = []
    for sentence in clean.split("|"):
        sentence = sentence.strip(" ，、：")
        while len(sentence) > limit:
            cut = max(sentence.rfind(mark, 0, limit + 1) for mark in ("，", "、", "："))
            if cut <= 0:
                cut = limit
            parts.append(sentence[:cut].rstrip("，、： "))
            sentence = sentence[cut:].lstrip("，、： ")
        if sentence:
            parts.append(sentence.rstrip("，、： "))
    return parts


def ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    hours, cs = divmod(cs, 360000)
    minutes, cs = divmod(cs, 6000)
    secs, cs = divmod(cs, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def build_ass(data: dict[str, Any], durations: dict[str, float], destination: Path) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK SC,30,&H00FFFFFF,&H000000FF,&H00101824,&H78000000,0,0,0,0,100,100,0,0,1,3,1,2,80,80,125,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: list[str] = []
    for narration in data["narration"]:
        start = float(narration["start"])
        end = min(start + durations[narration["id"]], float(narration["end_limit"]) - 0.08)
        chunks = split_subtitle(narration["text"])
        weights = [max(1, len(chunk)) for chunk in chunks]
        cursor = start
        for index, (chunk, weight) in enumerate(zip(chunks, weights)):
            chunk_end = end if index == len(chunks) - 1 else cursor + (end - start) * weight / sum(weights)
            events.append(f"Dialogue: 0,{ass_time(cursor)},{ass_time(chunk_end)},Default,,0,0,0,,{chunk}")
            cursor = chunk_end
    destination.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def decode_pcm(path: Path, channels: int) -> np.ndarray:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-acodec", "pcm_s16le", "-ar", str(SR), "-ac", str(channels), "-"], stdout=subprocess.PIPE, check=True)
    raw = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return raw.reshape(-1, channels)


def mix_audio(data: dict[str, Any], tts_paths: dict[str, Path], output: Path, bgm_path: Path) -> dict[str, float]:
    total_samples = int(round(float(data["duration"]) * SR))
    voice = np.zeros((total_samples, 2), dtype=np.float32)
    durations: dict[str, float] = {}
    for narration in data["narration"]:
        mono = decode_pcm(tts_paths[narration["id"]], 1)[:, 0]
        durations[narration["id"]] = len(mono) / SR
        available = float(narration["end_limit"]) - float(narration["start"])
        if durations[narration["id"]] > available:
            raise RuntimeError(f"{narration['id']} voice {durations[narration['id']]:.2f}s exceeds {available:.2f}s")
        start_sample = int(round(float(narration["start"]) * SR))
        end_sample = min(total_samples, start_sample + len(mono))
        voice[start_sample:end_sample, 0] += mono[: end_sample - start_sample]
        voice[start_sample:end_sample, 1] += mono[: end_sample - start_sample]
    bgm = decode_pcm(bgm_path, 2)
    repeats = math.ceil(total_samples / len(bgm))
    bed = np.tile(bgm, (repeats, 1))[:total_samples] * BGM_VOL
    fade_samples = int(4.0 * SR)
    bed[-fade_samples:] *= np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)[:, None]
    mixed = voice + bed
    peak = float(np.max(np.abs(mixed)))
    if peak > 0.99:
        mixed *= 0.99 / peak
    pcm = (np.clip(mixed, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SR)
        wav.writeframes(pcm.tobytes())
    return durations


def build_visuals(data: dict[str, Any], work_dir: Path) -> Path:
    cards_dir = work_dir / "cards"
    labels_dir = work_dir / "labels"
    segments_dir = work_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    for card_id in ("hero", "pipeline", "four_metrics", "gen_intro", "final_metrics", "ending"):
        render_card(card_id, cards_dir / f"{card_id}.png")
    segment_paths: list[Path] = []
    for index, visual in enumerate(data["visuals"]):
        segment_path = segments_dir / f"{index:02d}_{visual['id']}.mp4"
        duration = float(visual["end"] - visual["start"])
        if visual["kind"] == "card":
            build_card_segment(cards_dir / f"{visual['id']}.png", segment_path, duration, int(data["fps"]))
        else:
            label_path = labels_dir / f"{visual['id']}.png"
            render_label(visual["label"], label_path)
            source = Path(data["source_main"] if visual["kind"] == "main_clip" else data["source_generalization"])
            build_source_segment(source, visual, label_path, segment_path, int(data["fps"]))
        segment_paths.append(segment_path)
    video_only = work_dir / "video_only.mp4"
    concat_segments(segment_paths, video_only, work_dir)
    return video_only


def final_compose(video_only: Path, audio: Path, subtitles: Path, output: Path) -> None:
    sub_path = str(subtitles).replace(":", "\\:").replace("'", "\\'")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-i", str(video_only), "-i", str(audio), "-vf", f"subtitles='{sub_path}'", "-map", "0:v:0", "-map", "1:a:0", "-t", "72.000", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", "-movflags", "+faststart", str(output)])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, default=DEFAULT_TIMELINE)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    data = load_timeline(args.timeline)
    validate_timeline(data)
    print("时间轴验证通过")
    if args.validate_only:
        return
    require_runtime_paths(data)
    output_dir = Path(data["output_dir"])
    work_dir = output_dir / "work"
    output_dir.mkdir(parents=True, exist_ok=True)
    video_only = build_visuals(data, work_dir)
    tts_paths = asyncio.run(generate_tts_files(data, work_dir / "audio"))
    full_audio = work_dir / "full_audio.wav"
    durations = mix_audio(data, tts_paths, full_audio, ROOT / "assets" / "bgm_default.mp3")
    subtitles = work_dir / "subtitles.ass"
    build_ass(data, durations, subtitles)
    final_output = output_dir / FINAL_FILENAME
    final_compose(video_only, full_audio, subtitles, final_output)
    print(f"成片输出：{final_output}")


if __name__ == "__main__":
    main()
