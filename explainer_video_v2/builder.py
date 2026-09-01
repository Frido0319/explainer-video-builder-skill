"""Project preparation and end-to-end V2 build orchestration."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from .audio import build_audio_assets
from .manifest import load_manifest, validate_manifest
from .media import build_visuals
from .pronunciation import rewrite_narration
from .provenance import write_build_fingerprint
from .themes import get_theme


ROOT = Path(__file__).resolve().parents[1]


def _resolve(path_value: str, project_dir: Path) -> str:
    expanded = os.path.expandvars(path_value)
    if "$" in expanded:
        raise ValueError(f"unresolved environment variable in path: {path_value}")
    path = Path(expanded)
    return str(path if path.is_absolute() else (project_dir / path).resolve())


def _assert_output_does_not_overwrite_source(data: dict[str, Any]) -> None:
    output_dir = Path(data["output_dir"])
    output_root = output_dir.resolve(strict=False)
    output = (output_dir / data["output_name"]).resolve(strict=False)
    sources = [
        Path(visual["source"])
        for visual in data["visuals"]
        if visual["kind"] in {"clip", "image", "pptx"}
    ]
    bgm = data.get("audio", {}).get("bgm")
    if bgm:
        sources.append(Path(bgm))
    for source in sources:
        resolved_source = source.resolve(strict=False)
        if resolved_source == output:
            raise ValueError(f"output path would overwrite source: {source}")
        if resolved_source == output_root or output_root in resolved_source.parents:
            raise ValueError(f"source must be outside output_dir: {source}")
    if output_dir.is_symlink():
        raise ValueError(f"output_dir must not be a symbolic link: {output_dir}")
    if output_dir.exists():
        symlink = next((path for path in output_dir.rglob("*") if path.is_symlink()), None)
        if symlink is not None:
            raise ValueError(f"output_dir contains a symbolic link: {symlink}")


def prepare_project(manifest_path: Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    data = rewrite_narration(load_manifest(manifest_path))
    project_dir = manifest_path.parent
    data["output_dir"] = _resolve(data["output_dir"], project_dir)
    for visual in data["visuals"]:
        if visual["kind"] in {"clip", "image", "pptx"}:
            visual["source"] = _resolve(visual["source"], project_dir)
    audio = data.setdefault("audio", {})
    if audio.get("bgm"):
        audio["bgm"] = _resolve(audio["bgm"], project_dir)
    else:
        audio["bgm"] = str(ROOT / "assets" / "bgm_default.mp3")
    data["_manifest_path"] = str(manifest_path)
    validate_manifest(data)
    _assert_output_does_not_overwrite_source(data)
    return data


def final_ffmpeg_command(
    video_only: Path,
    audio: Path,
    subtitles: Path,
    output: Path,
    duration: float,
) -> list[str]:
    sub_path = str(subtitles).replace(":", "\\:").replace("'", "\\'")
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-i",
        str(video_only),
        "-i",
        str(audio),
        "-vf",
        f"subtitles='{sub_path}'",
        "-map",
        "0:v:0",
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


def build_project(manifest_path: Path) -> Path:
    data = prepare_project(manifest_path)
    output_dir = Path(data["output_dir"])
    work_dir = output_dir / "work"
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    theme = get_theme(data["theme"])
    video_only = build_visuals(data, theme, work_dir)
    bgm_value = data.get("audio", {}).get("bgm")
    bgm_path = Path(bgm_value) if bgm_value else None
    full_audio, subtitles, _ = build_audio_assets(data, work_dir, bgm_path)
    output = output_dir / data["output_name"]
    command = final_ffmpeg_command(video_only, full_audio, subtitles, output, float(data["duration"]))
    print("运行：", " ".join(command))
    subprocess.run(command, check=True)
    write_build_fingerprint(data, work_dir, output)
    return output
