"""Visual theme tokens for V2 cards."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Theme:
    name: str
    background: tuple[int, int, int]
    blue: tuple[int, int, int]
    dark_blue: tuple[int, int, int]
    light_blue: tuple[int, int, int]
    red: tuple[int, int, int]
    yellow: tuple[int, int, int]
    text: tuple[int, int, int]
    gray: tuple[int, int, int]
    font_regular: Path
    font_bold: Path
    subtitle_safe_y: int


def _font_path(environment_name: str, candidates: tuple[Path, ...]) -> Path:
    override = os.environ.get(environment_name)
    if override:
        return Path(override).expanduser()
    return next((path for path in candidates if path.is_file()), candidates[0])


WINDOWS_FONTS = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
REGULAR_FONT = _font_path(
    "EXPLAINER_VIDEO_FONT_REGULAR",
    (
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        WINDOWS_FONTS / "msyh.ttc",
    ),
)
BOLD_FONT = _font_path(
    "EXPLAINER_VIDEO_FONT_BOLD",
    (
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        WINDOWS_FONTS / "msyhbd.ttc",
    ),
)


RESEARCH_PPT = Theme(
    name="research_ppt",
    background=(252, 252, 252),
    blue=(52, 88, 165),
    dark_blue=(18, 54, 112),
    light_blue=(224, 231, 245),
    red=(205, 10, 18),
    yellow=(255, 235, 0),
    text=(20, 25, 35),
    gray=(246, 247, 249),
    font_regular=REGULAR_FONT,
    font_bold=BOLD_FONT,
    subtitle_safe_y=875,
)


def get_theme(name: str) -> Theme:
    if name != RESEARCH_PPT.name:
        raise ValueError(f"unsupported theme: {name}")
    return RESEARCH_PPT
