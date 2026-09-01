"""Read-only PowerPoint slide rasterization for V2 image segments."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path


def _tool(*names: str) -> str:
    environment_name = f"EXPLAINER_VIDEO_{names[0].upper()}"
    override = os.environ.get(environment_name)
    if override:
        return override
    for name in names:
        for directory in (Path("/usr/bin"), Path("/usr/local/bin")):
            candidate = directory / name
            if candidate.is_file():
                return str(candidate)
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    raise RuntimeError(f"required presentation tool not found: {' or '.join(names)}")


def render_pptx_slide(source: Path, slide: int, cache_dir: Path) -> Path:
    source = Path(source).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() not in {".ppt", ".pptx"}:
        raise ValueError(f"unsupported presentation source: {source}")
    if not isinstance(slide, int) or isinstance(slide, bool) or slide <= 0:
        raise ValueError("slide must be a positive integer")

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    pdf = cache_dir / f"{source.stem}.pdf"
    output = cache_dir / f"slide-{slide}.png"
    stamp = cache_dir / "source.sha256"
    signature = hashlib.sha256(source.read_bytes()).hexdigest()
    cache_matches = stamp.is_file() and stamp.read_text(encoding="ascii") == signature
    if cache_matches and output.is_file() and output.stat().st_size:
        return output

    if not cache_matches:
        pdf.unlink(missing_ok=True)
        for stale_slide in cache_dir.glob("slide-*.png"):
            stale_slide.unlink()

    if not pdf.is_file():
        subprocess.run(
            [
                _tool("libreoffice", "soffice"),
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(cache_dir),
                str(source),
            ],
            check=True,
        )
    if not pdf.is_file():
        raise RuntimeError(f"PowerPoint conversion did not produce PDF: {pdf}")

    prefix = cache_dir / f"slide-{slide}"
    subprocess.run(
        [
            _tool("pdftoppm"),
            "-png",
            "-r",
            "120",
            "-f",
            str(slide),
            "-l",
            str(slide),
            "-singlefile",
            str(pdf),
            str(prefix),
        ],
        check=True,
    )
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"PowerPoint slide {slide} was not rendered: {source}")
    stamp.write_text(signature, encoding="ascii")
    return output
