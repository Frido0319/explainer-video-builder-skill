#!/usr/bin/env python3
"""Build the V2 editing prototype from a single timeline configuration."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


MAX_ZOOM = 1.08
SUBTITLE_SAFE_Y = 820
MAX_CALLOUT_HEIGHT = 80
FONT_BOLD = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
EDITED_FILENAME = "V2精剪样片_平滑推进版_36-64s.mp4"


def load_timeline(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("source", "reference", "subtitles", "output_dir"):
        data[key] = os.path.expandvars(data[key])
    return data


def require_runtime_paths(data: dict[str, Any]) -> None:
    for key in ("source", "reference", "subtitles", "output_dir"):
        if "$" in data[key]:
            raise ValueError(f"unresolved environment variable in {key}: {data[key]}")


def _number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    return float(value)


def validate_timeline(data: dict[str, Any]) -> None:
    clip = data["clip"]
    clip_start = _number(clip["start"], "clip.start")
    clip_end = _number(clip["end"], "clip.end")
    duration = clip_end - clip_start
    if abs(duration - 28.0) > 1e-6:
        raise ValueError(f"clip duration must be 28.0 seconds, got {duration}")

    previous_end = 0.0
    for index, segment in enumerate(data["zoom_segments"]):
        start = _number(segment["start"], f"zoom_segments[{index}].start")
        end = _number(segment["end"], f"zoom_segments[{index}].end")
        zoom_start = _number(segment["zoom_start"], "zoom_start")
        zoom_end = _number(segment["zoom_end"], "zoom_end")
        if start < previous_end:
            raise ValueError("zoom segments overlap")
        if not 0 <= start < end <= duration:
            raise ValueError("zoom segment is outside clip")
        if zoom_start < 1.0 or zoom_end < zoom_start or zoom_end > MAX_ZOOM:
            raise ValueError(f"zoom must stay between 1.0 and {MAX_ZOOM}")
        previous_end = end

    chapter = data["chapter"]
    if not 0 <= _number(chapter["start"], "chapter.start") < _number(
        chapter["end"], "chapter.end"
    ) <= duration:
        raise ValueError("chapter is outside clip")

    for index, callout in enumerate(data["callouts"]):
        start = _number(callout["start"], f"callouts[{index}].start")
        end = _number(callout["end"], f"callouts[{index}].end")
        y = _number(callout["y"], f"callouts[{index}].y")
        if not 0 <= start < end <= duration:
            raise ValueError("callout is outside clip")
        if y + MAX_CALLOUT_HEIGHT > SUBTITLE_SAFE_Y:
            raise ValueError("callout violates subtitle safe area")


def parse_ass_time(value: str) -> float:
    match = re.fullmatch(r"(\d+):(\d{2}):(\d{2})\.(\d{2})", value.strip())
    if not match:
        raise ValueError(f"invalid ASS timestamp: {value}")
    hours, minutes, seconds, centiseconds = map(int, match.groups())
    return hours * 3600 + minutes * 60 + seconds + centiseconds / 100


def format_ass_time(seconds: float) -> str:
    total_centiseconds = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(total_centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    whole_seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"


def rebase_ass(
    source: Path, destination: Path, start: float, end: float
) -> int:
    output: list[str] = []
    retained = 0
    for raw_line in source.read_text(encoding="utf-8").splitlines():
        if not raw_line.startswith("Dialogue:"):
            output.append(raw_line)
            continue
        fields = raw_line.split(",", 3)
        if len(fields) != 4:
            raise ValueError(f"malformed ASS dialogue: {raw_line}")
        event_start = parse_ass_time(fields[1])
        event_end = parse_ass_time(fields[2])
        if event_end <= start or event_start >= end:
            continue
        rebased_start = format_ass_time(max(event_start, start) - start)
        rebased_end = format_ass_time(min(event_end, end) - start)
        output.append(f"{fields[0]},{rebased_start},{rebased_end},{fields[3]}")
        retained += 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(output) + "\n", encoding="utf-8")
    return retained


def _render_label(text: str, destination: Path, color: str, chapter: bool) -> None:
    palette = {
        "blue": ((13, 54, 110, 224), (91, 169, 255, 255)),
        "green": ((9, 82, 73, 224), (72, 215, 185, 255)),
    }
    background, border = palette[color]
    font_size = 54 if chapter else 36
    horizontal_padding = 34 if chapter else 26
    vertical_padding = 18 if chapter else 12
    font = ImageFont.truetype(str(FONT_BOLD), font_size)
    probe = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    width = right - left + horizontal_padding * 2
    height = bottom - top + vertical_padding * 2
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (1, 1, width - 2, height - 2),
        radius=18 if chapter else 14,
        fill=background,
        outline=border,
        width=3,
    )
    draw.text(
        (horizontal_padding - left, vertical_padding - top),
        text,
        font=font,
        fill=(255, 255, 255, 255),
    )
    image.save(destination)


def render_assets(data: dict[str, Any], work_dir: Path) -> dict[str, Path]:
    work_dir.mkdir(parents=True, exist_ok=True)
    assets: dict[str, Path] = {}
    chapter_path = work_dir / "chapter.png"
    _render_label(data["chapter"]["text"], chapter_path, "blue", chapter=True)
    assets["chapter"] = chapter_path
    for index, callout in enumerate(data["callouts"]):
        path = work_dir / f"callout_{index}.png"
        _render_label(callout["text"], path, callout["color"], chapter=False)
        assets[f"callout_{index}"] = path
    return assets


def _filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def build_filter_graph(
    data: dict[str, Any], assets: dict[str, Path], ass_path: Path
) -> str:
    first, second = data["zoom_segments"]
    fps = int(data["clip"]["fps"])
    first_start_frame = int(round(first["start"] * fps))
    first_end_frame = int(round(first["end"] * fps))
    second_start_frame = int(round(second["start"] * fps))
    second_end_frame = int(round(second["end"] * fps))
    zoom_expression = (
        f"if(gte(on,{first_start_frame})*lt(on,{first_end_frame}),"
        f"{first['zoom_start']:.5f}+({first['zoom_end'] - first['zoom_start']:.5f})*"
        f"(on-{first_start_frame})/{first_end_frame - first_start_frame - 1},"
        f"if(gte(on,{second_start_frame})*lt(on,{second_end_frame}),"
        f"{second['zoom_start']:.5f}+({second['zoom_end'] - second['zoom_start']:.5f})*"
        f"(on-{second_start_frame})/{second_end_frame - second_start_frame - 1},1.0))"
    )
    focus_y_expression = (
        f"if(gte(on,{first_start_frame})*lt(on,{first_end_frame}),"
        f"ih*{first['focus_y']:.5f}-(ih/zoom/2),"
        f"if(gte(on,{second_start_frame})*lt(on,{second_end_frame}),"
        f"ih*{second['focus_y']:.5f}-(ih/zoom/2),ih/2-(ih/zoom/2)))"
    )
    graph = [
        "[0:v]fps=24,scale=7680:4320:flags=lanczos,"
        f"zoompan=z='{zoom_expression}':"
        "x='iw/2-(iw/zoom/2)':"
        f"y='{focus_y_expression}':d=1:s=1920x1080:fps=24,"
        f"setsar=1[base]"
    ]

    events = [("chapter", data["chapter"])] + [
        (f"callout_{index}", callout)
        for index, callout in enumerate(data["callouts"])
    ]
    previous = "base"
    for index, (asset_name, event) in enumerate(events):
        input_index = index + 2
        asset_label = f"asset{index}"
        output_label = f"visual{index}"
        graph.append(f"[{input_index}:v]format=rgba[{asset_label}]")
        graph.append(
            f"[{previous}][{asset_label}]"
            f"overlay=x={int(event['x'])}:y={int(event['y'])}:"
            f"enable='between(t,{event['start']:.3f},{event['end']:.3f})'"
            f"[{output_label}]"
        )
        previous = output_label

    graph.append(f"[{previous}]subtitles='{_filter_path(ass_path)}'[vout]")
    return ";".join(graph)


def _run(command: list[str]) -> None:
    print("运行：", " ".join(command))
    subprocess.run(command, check=True)


def build_baseline(data: dict[str, Any], output: Path) -> None:
    clip = data["clip"]
    duration = clip["end"] - clip["start"]
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-ss",
            f"{clip['start']:.3f}",
            "-i",
            data["reference"],
            "-t",
            f"{duration:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )


def build_edited(
    data: dict[str, Any], work_dir: Path, output: Path
) -> None:
    clip = data["clip"]
    duration = clip["end"] - clip["start"]
    work_dir.mkdir(parents=True, exist_ok=True)
    ass_path = work_dir / "rebased.ass"
    retained = rebase_ass(
        Path(data["subtitles"]), ass_path, clip["start"], clip["end"]
    )
    if retained == 0:
        raise RuntimeError("no subtitles overlap the prototype interval")
    assets = render_assets(data, work_dir / "assets")
    filter_graph = build_filter_graph(data, assets, ass_path)

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-ss",
        f"{clip['start']:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        data["source"],
        "-ss",
        f"{clip['start']:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        data["reference"],
    ]
    for asset_name in ["chapter", "callout_0", "callout_1", "callout_2", "callout_3"]:
        command.extend(["-loop", "1", "-i", str(assets[asset_name])])
    command.extend(
        [
            "-filter_complex",
            filter_graph,
            "-map",
            "[vout]",
            "-map",
            "1:a:0",
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    _run(command)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeline", type=Path, default=Path(__file__).with_name("timeline.json")
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    timeline_path = args.timeline
    data = load_timeline(timeline_path)
    validate_timeline(data)
    print(f"Timeline valid: {timeline_path}")
    if args.validate_only:
        return
    require_runtime_paths(data)
    output_dir = Path(data["output_dir"])
    work_dir = output_dir / "work"
    build_baseline(data, output_dir / "原版片段_36-64s.mp4")
    build_edited(data, work_dir, output_dir / EDITED_FILENAME)
    print(f"输出完成：{output_dir}")


if __name__ == "__main__":
    main()
