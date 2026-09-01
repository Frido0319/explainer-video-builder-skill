"""Bind V2 verification to the exact manifest used for a successful build."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


FINGERPRINT_FILE = "build_provenance.json"


def _without_runtime_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_runtime_metadata(item)
            for key, item in value.items()
            if not key.startswith("_")
        }
    if isinstance(value, list):
        return [_without_runtime_metadata(item) for item in value]
    return value


def manifest_fingerprint(data: dict[str, Any]) -> str:
    canonical = json.dumps(
        _without_runtime_metadata(data),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_paths(data: dict[str, Any]) -> list[Path]:
    paths = {
        Path(visual["source"])
        for visual in data["visuals"]
        if visual["kind"] in {"clip", "image", "pptx"}
    }
    bgm = data.get("audio", {}).get("bgm")
    if bgm:
        paths.add(Path(bgm))
    return sorted(paths, key=str)


def _source_fingerprints(data: dict[str, Any]) -> dict[str, str]:
    return {str(path): file_fingerprint(path) for path in _source_paths(data)}


def write_build_fingerprint(
    data: dict[str, Any], work_dir: Path, output: Path
) -> Path:
    path = Path(work_dir) / FINGERPRINT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "manifest_sha256": manifest_fingerprint(data),
        "source_sha256": _source_fingerprints(data),
        "output_sha256": file_fingerprint(output),
    }
    path.write_text(
        json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def assert_build_fingerprint(
    data: dict[str, Any], work_dir: Path, output: Path
) -> None:
    path = Path(work_dir) / FINGERPRINT_FILE
    if not path.is_file():
        raise RuntimeError(f"build manifest fingerprint missing: {path}")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("manifest_sha256") != manifest_fingerprint(data):
        raise RuntimeError(
            "build manifest fingerprint does not match the current project; rebuild before verify"
        )
    if record.get("source_sha256") != _source_fingerprints(data):
        raise RuntimeError(
            "build source fingerprint does not match the current source files; rebuild before verify"
        )
    if record.get("output_sha256") != file_fingerprint(output):
        raise RuntimeError(
            "build output fingerprint does not match the current video; rebuild before verify"
        )
