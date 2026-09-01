"""Visual segment construction for V2 projects."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .cards import render_card
from .pptx import render_pptx_slide
from .themes import Theme


def run(command: list[str]) -> None:
    print("运行：", " ".join(command))
    subprocess.run(command, check=True)


def card_video_filter(duration: float, fps: int, width: int, height: int) -> str:
    frames = max(1, int(round(duration * fps)))
    zoom = f"1.0+0.025*on/{max(1, frames - 1)}"
    return (
        f"scale={width * 4}:{height * 4}:flags=lanczos,"
        f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d=1:s={width}x{height}:fps={fps},format=yuv420p"
    )


def image_video_filter(width: int, height: int, subtitle_safe_y: int) -> str:
    return (
        f"scale={width}:{subtitle_safe_y}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={width}:{height}:(ow-iw)/2:0:color=white,setsar=1,format=yuv420p"
    )


def clip_setpts_factor(visual: dict[str, Any]) -> float:
    output_duration = float(visual["end"]) - float(visual["start"])
    return output_duration / float(visual["source_duration"])


def clip_video_filter(factor: float, fps: int, width: int, height: int) -> str:
    return (
        f"setpts={factor:.8f}*PTS,fps={fps},"
        f"scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "setsar=1"
    )


def _render_label(text: str, theme: Theme, destination: Path, width: int, height: int) -> None:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    text_font = ImageFont.truetype(str(theme.font_bold), 36)
    bbox = draw.textbbox((0, 0), text, font=text_font)
    box_width = bbox[2] - bbox[0] + 70
    right = width - 64
    left = right - box_width
    draw.rounded_rectangle(
        (left, 70, right, 142),
        radius=12,
        fill=(*theme.blue, 238),
        outline=(*theme.dark_blue, 255),
        width=3,
    )
    draw.text((left + 35, 106), text, font=text_font, fill="white", anchor="lm")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


def _build_card_segment(
    card_path: Path,
    output: Path,
    duration: float,
    fps: int,
    width: int,
    height: int,
) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-loop",
            "1",
            "-framerate",
            str(fps),
            "-i",
            str(card_path),
            "-t",
            f"{duration:.3f}",
            "-vf",
            card_video_filter(duration, fps, width, height),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )


def _build_image_segment(
    source: Path,
    output: Path,
    duration: float,
    fps: int,
    width: int,
    height: int,
    subtitle_safe_y: int,
) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-loop",
            "1",
            "-framerate",
            str(fps),
            "-i",
            str(source),
            "-t",
            f"{duration:.3f}",
            "-vf",
            image_video_filter(width, height, subtitle_safe_y),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )


def _build_clip_segment(
    visual: dict[str, Any],
    label_path: Path | None,
    output: Path,
    fps: int,
    width: int,
    height: int,
) -> None:
    duration = float(visual["end"]) - float(visual["start"])
    factor = clip_setpts_factor(visual)
    base = clip_video_filter(factor, fps, width, height)
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-ss",
        f"{float(visual['source_start']):.3f}",
        "-t",
        f"{float(visual['source_duration']):.3f}",
        "-i",
        str(visual["source"]),
    ]
    if label_path is None:
        command.extend(["-vf", f"{base},format=yuv420p"])
    else:
        command.extend(
            [
                "-loop",
                "1",
                "-framerate",
                str(fps),
                "-i",
                str(label_path),
                "-filter_complex",
                f"[0:v]{base}[base];[1:v]format=rgba[label];[base][label]overlay=0:0:shortest=1,format=yuv420p[v]",
                "-map",
                "[v]",
            ]
        )
    command.extend(
        [
            "-t",
            f"{duration:.3f}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )
    run(command)


def _concat_segments(paths: list[Path], output: Path, work_dir: Path, duration: float) -> None:
    concat_file = work_dir / "concat.txt"
    concat_file.write_text("".join(f"file '{path}'\n" for path in paths), encoding="utf-8")
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-t",
            f"{duration:.3f}",
            str(output),
        ]
    )


def build_visuals(data: dict[str, Any], theme: Theme, work_dir: Path) -> Path:
    cards_dir = work_dir / "cards"
    labels_dir = work_dir / "labels"
    segments_dir = work_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    width = int(data["width"])
    height = int(data["height"])
    fps = int(data["fps"])
    paths: list[Path] = []
    for index, visual in enumerate(data["visuals"]):
        duration = float(visual["end"]) - float(visual["start"])
        output = segments_dir / f"{index:02d}_{visual['id']}.mp4"
        if visual["kind"] == "card":
            card_path = cards_dir / f"{visual['id']}.png"
            render_card(visual["card"], theme, card_path)
            _build_card_segment(card_path, output, duration, fps, width, height)
        elif visual["kind"] in {"image", "pptx"}:
            source = Path(visual["source"])
            if visual["kind"] == "pptx":
                cache_key = hashlib.sha256(str(source.resolve()).encode("utf-8")).hexdigest()[:12]
                source = render_pptx_slide(
                    source,
                    int(visual["slide"]),
                    work_dir / "pptx" / cache_key,
                )
            _build_image_segment(
                source,
                output,
                duration,
                fps,
                width,
                height,
                theme.subtitle_safe_y,
            )
        else:
            label_path: Path | None = None
            if visual.get("label"):
                label_path = labels_dir / f"{visual['id']}.png"
                _render_label(visual["label"], theme, label_path, width, height)
            _build_clip_segment(visual, label_path, output, fps, width, height)
        paths.append(output)
    video_only = work_dir / "video_only.mp4"
    _concat_segments(paths, video_only, work_dir, float(data["duration"]))
    return video_only
