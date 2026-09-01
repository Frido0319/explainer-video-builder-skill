"""Load and validate V2 project manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SUPPORTED_MODES = {"create", "enhance"}
SUPPORTED_THEMES = {"research_ppt"}
SUPPORTED_VISUAL_KINDS = {"card", "clip", "image", "pptx"}
SUPPORTED_CARD_TEMPLATES = {
    "hero",
    "process",
    "metric_compare",
    "chapter",
    "metric_grid",
    "ending",
}


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_manifest(data)
    return data


def _require(mapping: dict[str, Any], keys: tuple[str, ...], context: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ValueError(f"{context} missing fields: {', '.join(missing)}")


def validate_manifest(data: dict[str, Any]) -> None:
    _require(
        data,
        (
            "version",
            "mode",
            "theme",
            "duration",
            "fps",
            "width",
            "height",
            "output_dir",
            "output_name",
            "visuals",
            "narration",
            "verification",
        ),
        "manifest",
    )
    if data["version"] != 2:
        raise ValueError("manifest version must be 2")
    if data["mode"] not in SUPPORTED_MODES:
        raise ValueError(f"unsupported mode: {data['mode']}")
    if data["theme"] not in SUPPORTED_THEMES:
        raise ValueError(f"unsupported theme: {data['theme']}")

    duration = float(data["duration"])
    if duration <= 0 or int(data["fps"]) <= 0 or int(data["width"]) <= 0 or int(data["height"]) <= 0:
        raise ValueError("duration, fps, width, and height must be positive")
    if (int(data["width"]), int(data["height"]), int(data["fps"])) != (1920, 1080, 24):
        raise ValueError("V2 output must be 1920x1080 at 24 fps")

    output_name = data["output_name"]
    if (
        not isinstance(output_name, str)
        or not output_name.strip()
        or output_name in {".", ".."}
        or Path(output_name).is_absolute()
        or Path(output_name).name != output_name
        or "\\" in output_name
    ):
        raise ValueError("output_name must be a plain filename inside output_dir")

    visuals = data["visuals"]
    if not visuals:
        raise ValueError("visual timeline must not be empty")
    if abs(float(visuals[0]["start"])) > 1e-6 or abs(float(visuals[-1]["end"]) - duration) > 1e-6:
        raise ValueError("visual timeline must cover the full duration")

    seen_ids: set[str] = set()
    for index, visual in enumerate(visuals):
        _require(visual, ("id", "kind", "start", "end"), f"visual {index}")
        if visual["id"] in seen_ids:
            raise ValueError(f"duplicate visual id: {visual['id']}")
        seen_ids.add(visual["id"])
        if visual["kind"] not in SUPPORTED_VISUAL_KINDS:
            raise ValueError(f"unsupported visual kind: {visual['kind']}")
        if float(visual["start"]) >= float(visual["end"]):
            raise ValueError(f"invalid visual segment: {visual['id']}")
        if index and abs(float(visuals[index - 1]["end"]) - float(visual["start"])) > 1e-6:
            raise ValueError("visual timeline must be contiguous")
        if visual["kind"] == "card":
            _require(visual, ("card",), f"card visual {visual['id']}")
            template = visual["card"].get("template")
            if template not in SUPPORTED_CARD_TEMPLATES:
                raise ValueError(f"unsupported card template: {template}")
        elif visual["kind"] == "clip":
            _require(
                visual,
                ("source", "source_start", "source_duration"),
                f"clip visual {visual['id']}",
            )
            if float(visual["source_start"]) < 0 or float(visual["source_duration"]) <= 0:
                raise ValueError(f"invalid clip source timing: {visual['id']}")
        elif visual["kind"] == "image":
            _require(visual, ("source",), f"image visual {visual['id']}")
        else:
            _require(visual, ("source", "slide"), f"pptx visual {visual['id']}")
            slide = visual["slide"]
            if not isinstance(slide, int) or isinstance(slide, bool) or slide <= 0:
                raise ValueError("slide must be a positive integer")

    if data["mode"] == "enhance" and not any(item["kind"] == "clip" for item in visuals):
        raise ValueError("enhance requires at least one clip")

    narration_ids: set[str] = set()
    for narration in data["narration"]:
        _require(narration, ("id", "start", "end_limit", "text"), "narration")
        if narration["id"] in narration_ids:
            raise ValueError(f"duplicate narration id: {narration['id']}")
        narration_ids.add(narration["id"])
        if not 0 <= float(narration["start"]) < float(narration["end_limit"]) <= duration:
            raise ValueError(f"narration outside timeline: {narration['id']}")
        if not str(narration["text"]).strip():
            raise ValueError(f"empty narration: {narration['id']}")

    verification = data["verification"]
    _require(verification, ("frame_times", "duration_tolerance"), "verification")
    if not verification["frame_times"]:
        raise ValueError("verification requires at least one frame time")
    if any(not 0 <= float(value) <= duration for value in verification["frame_times"]):
        raise ValueError("verification frame time outside timeline")
    if float(verification["duration_tolerance"]) < 0:
        raise ValueError("duration tolerance must be non-negative")
