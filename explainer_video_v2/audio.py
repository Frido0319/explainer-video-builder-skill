"""Narration, subtitles, and deterministic audio mixing."""

from __future__ import annotations

import asyncio
import math
import re
import subprocess
import wave
from pathlib import Path
from typing import Any

import edge_tts
import numpy as np


DEFAULT_VOICE = "zh-CN-YunjianNeural"
DEFAULT_RATE = "+18%"
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_BGM_VOLUME = 0.08
DEFAULT_BGM_FADE_SECONDS = 3.0
DEFAULT_BGM_SILENT_TAIL_SECONDS = 5.0


def apply_bgm_outro(
    bed: np.ndarray,
    sample_rate: int,
    fade_seconds: float = DEFAULT_BGM_FADE_SECONDS,
    silent_tail_seconds: float = DEFAULT_BGM_SILENT_TAIL_SECONDS,
) -> np.ndarray:
    """Fade only the BGM bed, then keep its final tail silent."""
    result = bed.copy()
    silent_samples = min(
        len(result), max(0, int(round(silent_tail_seconds * sample_rate)))
    )
    silent_start = len(result) - silent_samples
    fade_samples = min(
        silent_start, max(0, int(round(fade_seconds * sample_rate)))
    )
    if fade_samples:
        fade_start = silent_start - fade_samples
        result[fade_start:silent_start] *= np.linspace(
            1.0, 0.0, fade_samples, endpoint=False, dtype=np.float32
        )[:, None]
    if silent_samples:
        result[silent_start:] = 0.0
    return result


async def generate_tts_files(data: dict[str, Any], audio_dir: Path) -> dict[str, Path]:
    audio_dir.mkdir(parents=True, exist_ok=True)
    settings = data.get("audio", {})
    voice = settings.get("voice", DEFAULT_VOICE)
    rate = settings.get("rate", DEFAULT_RATE)
    paths: dict[str, Path] = {}
    for narration in data["narration"]:
        path = audio_dir / f"{narration['id']}.mp3"
        await edge_tts.Communicate(narration["text"], voice, rate=rate).save(str(path))
        paths[narration["id"]] = path
    return paths


def _decode_pcm(path: Path, channels: int, sample_rate: int) -> np.ndarray:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            "-",
        ],
        stdout=subprocess.PIPE,
        check=True,
    )
    raw = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return raw.reshape(-1, channels)


def mix_audio(
    data: dict[str, Any],
    tts_paths: dict[str, Path],
    output: Path,
    bgm_path: Path | None,
) -> dict[str, float]:
    settings = data.get("audio", {})
    sample_rate = int(settings.get("sample_rate", DEFAULT_SAMPLE_RATE))
    total_samples = int(round(float(data["duration"]) * sample_rate))
    voice = np.zeros((total_samples, 2), dtype=np.float32)
    durations: dict[str, float] = {}
    for narration in data["narration"]:
        mono = _decode_pcm(tts_paths[narration["id"]], 1, sample_rate)[:, 0]
        durations[narration["id"]] = len(mono) / sample_rate
        available = float(narration["end_limit"]) - float(narration["start"])
        if durations[narration["id"]] > available:
            raise RuntimeError(
                f"{narration['id']} voice {durations[narration['id']]:.2f}s exceeds {available:.2f}s"
            )
        start = int(round(float(narration["start"]) * sample_rate))
        end = min(total_samples, start + len(mono))
        voice[start:end, 0] += mono[: end - start]
        voice[start:end, 1] += mono[: end - start]

    bed = np.zeros_like(voice)
    if bgm_path is not None:
        bgm = _decode_pcm(bgm_path, 2, sample_rate)
        repeats = math.ceil(total_samples / len(bgm))
        volume = float(settings.get("bgm_volume", DEFAULT_BGM_VOLUME))
        bed = np.tile(bgm, (repeats, 1))[:total_samples] * volume
        bed = apply_bgm_outro(
            bed,
            sample_rate,
            fade_seconds=float(settings.get("fade_seconds", DEFAULT_BGM_FADE_SECONDS)),
            silent_tail_seconds=float(
                settings.get("silent_tail_seconds", DEFAULT_BGM_SILENT_TAIL_SECONDS)
            ),
        )

    mixed = voice + bed
    peak = float(np.max(np.abs(mixed))) if len(mixed) else 0.0
    if peak > 0.99:
        mixed *= 0.99 / peak
    pcm = (np.clip(mixed, -1.0, 1.0) * 32767.0).astype(np.int16)
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return durations


def _split_subtitle(text: str, limit: int = 20) -> list[str]:
    clean = re.sub(r"[。！？；]+", "|", text)
    result: list[str] = []
    for sentence in clean.split("|"):
        sentence = sentence.strip(" ，、：")
        while len(sentence) > limit:
            cuts = [sentence.rfind(mark, 0, limit + 1) for mark in ("，", "、", "：")]
            cut = max(cuts)
            if cut <= 0:
                cut = limit
            result.append(sentence[:cut].rstrip(" ，、："))
            sentence = sentence[cut:].lstrip(" ，、：")
        if sentence:
            result.append(sentence.rstrip(" ，、："))
    return result


def _ass_time(seconds: float) -> str:
    centiseconds = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, cs = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def build_ass(
    data: dict[str, Any],
    durations: dict[str, float],
    destination: Path,
    width: int,
    height: int,
) -> None:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
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
        chunks = _split_subtitle(narration["text"])
        weights = [max(1, len(chunk)) for chunk in chunks]
        cursor = start
        for index, (chunk, weight) in enumerate(zip(chunks, weights)):
            chunk_end = end if index == len(chunks) - 1 else cursor + (end - start) * weight / sum(weights)
            events.append(
                f"Dialogue: 0,{_ass_time(cursor)},{_ass_time(chunk_end)},Default,,0,0,0,,{chunk}"
            )
            cursor = chunk_end
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def build_audio_assets(
    data: dict[str, Any], work_dir: Path, bgm_path: Path | None
) -> tuple[Path, Path, dict[str, float]]:
    tts_paths = asyncio.run(generate_tts_files(data, work_dir / "audio"))
    full_audio = work_dir / "full_audio.wav"
    durations = mix_audio(data, tts_paths, full_audio, bgm_path)
    subtitles = work_dir / "subtitles.ass"
    build_ass(data, durations, subtitles, int(data["width"]), int(data["height"]))
    return full_audio, subtitles, durations
