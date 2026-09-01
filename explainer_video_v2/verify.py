"""Media verification helpers for V2 outputs."""

from __future__ import annotations

import json
import re
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .builder import prepare_project
from .provenance import assert_build_fingerprint
from .themes import get_theme


def _ass_seconds(value: str) -> float:
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def ass_dialogue_midpoints(path: Path) -> list[float]:
    """Return representative subtitle cue midpoints from an ASS file."""
    midpoints: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("Dialogue:"):
            continue
        fields = line.split(",", 9)
        if len(fields) < 10:
            continue
        start = _ass_seconds(fields[1])
        end = _ass_seconds(fields[2])
        if end > start:
            midpoints.append((start + end) / 2)
    if not midpoints:
        raise RuntimeError("subtitle ASS contains no dialogue cues")
    indexes = sorted({0, len(midpoints) // 2, len(midpoints) - 1})
    return [midpoints[index] for index in indexes]


def assert_subtitle_frame_diff(
    final_frame: Path,
    reference_frame: Path,
    safe_y: int,
    pixel_threshold: int = 20,
    minimum_subtitle_pixels: int = 300,
    maximum_content_pixels: int = 5000,
) -> dict[str, int]:
    """Prove subtitle pixels render in the reserved band, not over content."""
    final = np.asarray(Image.open(final_frame).convert("RGB"), dtype=np.int16)
    reference = np.asarray(Image.open(reference_frame).convert("RGB"), dtype=np.int16)
    if final.shape != reference.shape:
        raise RuntimeError(
            f"subtitle verification frame shape mismatch: {final.shape} != {reference.shape}"
        )
    difference = np.max(np.abs(final - reference), axis=2)
    content_pixels = int(np.count_nonzero(difference[:safe_y] > pixel_threshold))
    subtitle_band_pixels = int(
        np.count_nonzero(difference[safe_y:] > pixel_threshold)
    )
    if subtitle_band_pixels <= minimum_subtitle_pixels:
        raise RuntimeError(
            f"subtitle rendering missing: changed pixels={subtitle_band_pixels}"
        )
    if content_pixels > maximum_content_pixels:
        raise RuntimeError(
            f"subtitle rendering outside safe band: changed pixels={content_pixels}"
        )
    return {
        "content_pixels": content_pixels,
        "subtitle_band_pixels": subtitle_band_pixels,
    }


def _stream(metadata: dict[str, Any], kind: str) -> dict[str, Any] | None:
    return next(
        (item for item in metadata.get("streams", []) if item.get("codec_type") == kind),
        None,
    )


def assert_verification_report(data: dict[str, Any], report: dict[str, Any]) -> None:
    actual_duration = float(report["duration"])
    expected_duration = float(data["duration"])
    tolerance = float(data["verification"]["duration_tolerance"])
    if abs(actual_duration - expected_duration) > tolerance:
        raise RuntimeError(
            f"duration mismatch: expected {expected_duration:.3f}, got {actual_duration:.3f}"
        )

    video = _stream(report["metadata"], "video")
    expected_video = (
        "h264",
        int(data["width"]),
        int(data["height"]),
        Fraction(int(data["fps"]), 1),
    )
    actual_video = None
    if video is not None:
        actual_video = (
            video.get("codec_name"),
            video.get("width"),
            video.get("height"),
            Fraction(video.get("r_frame_rate", "0/1")),
        )
    if actual_video != expected_video:
        raise RuntimeError(
            f"video specification mismatch: expected {expected_video}, got {actual_video}"
        )

    audio = _stream(report["metadata"], "audio")
    expected_audio = ("aac", 44100, 2)
    actual_audio = None
    if audio is not None:
        actual_audio = (
            audio.get("codec_name"),
            int(audio.get("sample_rate", 0)),
            audio.get("channels"),
        )
    if actual_audio != expected_audio:
        raise RuntimeError(
            f"audio specification mismatch: expected {expected_audio}, got {actual_audio}"
        )

    if report["black_intervals"]:
        raise RuntimeError(f"black frames detected: {report['black_intervals']}")
    mean_volume = report.get("mean_volume_db")
    max_volume = report.get("max_volume_db")
    if mean_volume is None or mean_volume < -60.0:
        raise RuntimeError(f"audio is missing or effectively silent: {mean_volume}")
    if max_volume is None or max_volume > -0.1:
        raise RuntimeError(f"audio clipping risk: max_volume={max_volume}")


def extract_verification_frames(
    output: Path, frame_times: list[float], destination: Path
) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for index, timestamp in enumerate(frame_times):
        frame = destination / f"{index:02d}_{timestamp:.3f}s.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(output),
                "-frames:v",
                "1",
                str(frame),
            ],
            check=True,
        )
        if not frame.is_file() or frame.stat().st_size == 0:
            raise RuntimeError(f"verification frame missing at {timestamp:.3f}s")
        paths.append(str(frame))
    return paths


def verify_project(manifest_path: Path) -> dict[str, Any]:
    data = prepare_project(manifest_path)
    output = Path(data["output_dir"]) / data["output_name"]
    work_dir = Path(data["output_dir"]) / "work"
    if not output.is_file():
        raise FileNotFoundError(output)
    assert_build_fingerprint(data, work_dir, output)
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
            "-of",
            "json",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    metadata = json.loads(probe.stdout)
    actual_duration = float(metadata["format"]["duration"])
    black = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-v",
            "info",
            "-i",
            str(output),
            "-vf",
            "blackdetect=d=0.20:pix_th=0.10",
            "-an",
            "-f",
            "null",
            "-",
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    black_intervals = re.findall(r"black_start:[^\n]+", black.stderr)
    volume = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-v",
            "info",
            "-i",
            str(output),
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
    mean_match = re.search(r"mean_volume:\s+(-?[\d.]+) dB", volume.stderr)
    max_match = re.search(r"max_volume:\s+(-?[\d.]+) dB", volume.stderr)
    report = {
        "output": str(output),
        "duration": actual_duration,
        "black_intervals": black_intervals,
        "mean_volume_db": float(mean_match.group(1)) if mean_match else None,
        "max_volume_db": float(max_match.group(1)) if max_match else None,
        "metadata": metadata,
    }
    assert_verification_report(data, report)
    report["verification_frames"] = extract_verification_frames(
        output,
        [float(value) for value in data["verification"]["frame_times"]],
        work_dir / "verification_frames",
    )
    subtitle_times = ass_dialogue_midpoints(work_dir / "subtitles.ass")
    final_subtitle_frames = extract_verification_frames(
        output, subtitle_times, work_dir / "verification_subtitles" / "final"
    )
    reference_subtitle_frames = extract_verification_frames(
        work_dir / "video_only.mp4",
        subtitle_times,
        work_dir / "verification_subtitles" / "reference",
    )
    safe_y = get_theme(data["theme"]).subtitle_safe_y
    report["subtitle_checks"] = [
        assert_subtitle_frame_diff(Path(final), Path(reference), safe_y)
        for final, reference in zip(final_subtitle_frames, reference_subtitle_frames)
    ]
    return report
