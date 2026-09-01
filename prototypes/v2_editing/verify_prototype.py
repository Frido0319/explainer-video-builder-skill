#!/usr/bin/env python3
"""Verify the V2 editing prototype outputs and render a comparison sheet."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

from build_prototype import EDITED_FILENAME, load_timeline, require_runtime_paths, validate_timeline


ROOT = Path(__file__).resolve().parent
TIMELINE = ROOT / "timeline.json"
SAMPLE_TIMES = [6.0, 9.0, 11.0, 16.4, 19.0, 24.0, 27.0]
EVENT_TIMES = [6.0, 11.0, 16.4, 19.0, 24.0]
FONT = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def probe(path: Path) -> dict:
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_name,codec_type,width,height,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ]
    )
    return json.loads(result.stdout)


def volume(path: Path) -> tuple[float, float]:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    mean_match = re.search(r"mean_volume:\s+(-?[\d.]+) dB", result.stderr)
    max_match = re.search(r"max_volume:\s+(-?[\d.]+) dB", result.stderr)
    if not mean_match or not max_match:
        raise AssertionError("volumedetect did not report mean/max volume")
    return float(mean_match.group(1)), float(max_match.group(1))


def extract_frame(video: Path, timestamp: float, destination: Path) -> Image.Image:
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(destination),
        ]
    )
    return Image.open(destination).convert("RGB")


def mean_difference(first: Image.Image, second: Image.Image) -> float:
    stat = ImageStat.Stat(ImageChops.difference(first, second))
    return sum(stat.mean) / len(stat.mean)


def bright_pixels(image: Image.Image, box: tuple[int, int, int, int]) -> int:
    gray = image.crop(box).convert("L")
    histogram = gray.histogram()
    return sum(histogram[206:])


def assert_media(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise AssertionError(f"missing output: {path}")
    info = probe(path)
    duration = float(info["format"]["duration"])
    if abs(duration - 28.0) > 0.10:
        raise AssertionError(f"{path.name}: duration {duration:.3f}s")
    video_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio_stream = next(s for s in info["streams"] if s["codec_type"] == "audio")
    if (video_stream["codec_name"], video_stream["width"], video_stream["height"]) != (
        "h264",
        1920,
        1080,
    ):
        raise AssertionError(f"{path.name}: unexpected video stream {video_stream}")
    if (
        audio_stream["codec_name"],
        audio_stream["sample_rate"],
        audio_stream["channels"],
    ) != ("aac", "44100", 2):
        raise AssertionError(f"{path.name}: unexpected audio stream {audio_stream}")
    return info


def build_contact_sheet(
    baseline_frames: list[Image.Image], edited_frames: list[Image.Image], destination: Path
) -> None:
    font = ImageFont.truetype(str(FONT), 22)
    width, height = 640, 360
    canvas = Image.new("RGB", (width * 2, height * len(SAMPLE_TIMES)), "black")
    for row, timestamp in enumerate(SAMPLE_TIMES):
        for column, (name, frames) in enumerate(
            (("原版", baseline_frames), ("V2精剪", edited_frames))
        ):
            frame = frames[row].resize((width, height))
            draw = ImageDraw.Draw(frame)
            draw.rounded_rectangle((8, 8, 240, 46), radius=8, fill=(0, 0, 0, 210))
            draw.text((18, 11), f"{name}  t={timestamp:.1f}s", font=font, fill="white")
            canvas.paste(frame, (column * width, row * height))
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, quality=92)


def main() -> None:
    data = load_timeline(TIMELINE)
    validate_timeline(data)
    require_runtime_paths(data)
    output_dir = Path(data["output_dir"])
    baseline = output_dir / "原版片段_36-64s.mp4"
    edited = output_dir / EDITED_FILENAME
    frame_dir = output_dir / "work" / "verification_frames"

    baseline_info = assert_media(baseline)
    edited_info = assert_media(edited)
    baseline_volume = volume(baseline)
    edited_volume = volume(edited)
    if baseline_volume[0] < -60 or edited_volume[0] < -60:
        raise AssertionError("audio is effectively silent")
    if abs(baseline_volume[0] - edited_volume[0]) > 0.5:
        raise AssertionError("edited audio loudness differs from baseline")

    baseline_frames: list[Image.Image] = []
    edited_frames: list[Image.Image] = []
    differences: dict[str, float] = {}
    for timestamp in SAMPLE_TIMES:
        tag = str(timestamp).replace(".", "_")
        baseline_frame = extract_frame(
            baseline, timestamp, frame_dir / f"baseline_{tag}.jpg"
        )
        edited_frame = extract_frame(edited, timestamp, frame_dir / f"edited_{tag}.jpg")
        baseline_frames.append(baseline_frame)
        edited_frames.append(edited_frame)
        differences[f"{timestamp:.1f}"] = mean_difference(baseline_frame, edited_frame)

    for timestamp in EVENT_TIMES:
        if differences[f"{timestamp:.1f}"] < 0.75:
            raise AssertionError(f"visual event not detectable at {timestamp:.1f}s")

    for timestamp, frame in zip(SAMPLE_TIMES, edited_frames):
        # The verified ASS style renders subtitles around y=890–920. Bright pixels
        # in this band confirm the rebased subtitle layer is present when a cue is active.
        if timestamp in (6.0, 19.0, 24.0):
            count = bright_pixels(frame, (200, 850, 1720, 980))
            if count < 60:
                raise AssertionError(f"subtitle band looks empty at {timestamp:.1f}s")

    contact_sheet = output_dir / "V2精剪对比接触表.jpg"
    build_contact_sheet(baseline_frames, edited_frames, contact_sheet)
    report = {
        "baseline": {
            "duration": float(baseline_info["format"]["duration"]),
            "size": int(baseline_info["format"]["size"]),
            "mean_volume_db": baseline_volume[0],
            "max_volume_db": baseline_volume[1],
        },
        "edited": {
            "duration": float(edited_info["format"]["duration"]),
            "size": int(edited_info["format"]["size"]),
            "mean_volume_db": edited_volume[0],
            "max_volume_db": edited_volume[1],
        },
        "frame_mean_differences": differences,
        "contact_sheet": str(contact_sheet),
    }
    report_path = output_dir / "verification_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("验证通过")


if __name__ == "__main__":
    main()
