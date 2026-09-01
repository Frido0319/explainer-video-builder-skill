"""Data-driven card templates for V2 videos."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .themes import Theme


WIDTH = 1920
HEIGHT = 1080


def _font(theme: Theme, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(theme.font_bold if bold else theme.font_regular), size)


def _canvas(theme: Theme) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), theme.background)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, WIDTH, 12), fill=theme.blue)
    draw.rectangle((0, 12, WIDTH, 18), fill=(104, 133, 194))
    return image, draw


def _title(draw: ImageDraw.ImageDraw, theme: Theme, spec: dict[str, Any]) -> None:
    draw.text((84, 62), spec.get("kicker", ""), font=_font(theme, 26, True), fill=theme.blue)
    draw.text((84, 116), spec["title"], font=_font(theme, 68, True), fill=theme.text)
    draw.rectangle((84, 222, 1836, 228), fill=theme.blue)
    subtitle = spec.get("subtitle", "")
    if subtitle:
        draw.text((84, 258), subtitle, font=_font(theme, 32), fill=theme.dark_blue)


def _pill(
    draw: ImageDraw.ImageDraw,
    theme: Theme,
    box: tuple[int, int, int, int],
    text: str,
    style: str,
) -> None:
    palette = {
        "blue": (theme.blue, theme.dark_blue, (255, 255, 255)),
        "light": (theme.light_blue, theme.blue, theme.dark_blue),
        "red": ((255, 239, 224), theme.red, theme.red),
    }
    fill, outline, text_fill = palette[style]
    draw.rounded_rectangle(box, radius=12, fill=fill, outline=outline, width=3)
    draw.text(
        ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 - 2),
        text,
        font=_font(theme, 32, True),
        fill=text_fill,
        anchor="mm",
    )


def _takeaway(draw: ImageDraw.ImageDraw, theme: Theme, value: dict[str, str]) -> None:
    draw.rectangle((80, 805, 1840, 866), fill=theme.blue)
    lead = value["lead"]
    lead_font = _font(theme, 28, True)
    draw.text((118, 835), lead, font=lead_font, fill=theme.yellow, anchor="lm")
    lead_width = draw.textbbox((0, 0), lead, font=lead_font)[2]
    draw.text(
        (140 + lead_width, 835),
        value["detail"],
        font=_font(theme, 28),
        fill="white",
        anchor="lm",
    )


def _render_hero(draw: ImageDraw.ImageDraw, theme: Theme, spec: dict[str, Any]) -> None:
    draw.rectangle((0, 18, WIDTH, 210), fill=theme.blue)
    draw.text((960, 92), spec["kicker"], font=_font(theme, 38, True), fill="white", anchor="mm")
    draw.text((960, 158), spec.get("subtitle", ""), font=_font(theme, 28), fill=theme.yellow, anchor="mm")
    line_y = (340, 475)
    for index, line in enumerate(spec["title_lines"][:2]):
        color = theme.red if line.get("color") == "red" else theme.text
        draw.text((960, line_y[index]), line["text"], font=_font(theme, 102, True), fill=color, anchor="mm")
    stats = spec.get("stats", [])[:2]
    if stats:
        boxes = ((420, 610, 850, 700), (900, 610, 1500, 700))
        for item, box in zip(stats, boxes):
            _pill(draw, theme, box, item["text"], item.get("style", "light"))
    draw.rectangle((0, 790, WIDTH, 798), fill=theme.red)
    draw.rectangle((0, 798, WIDTH, 806), fill=theme.blue)
    draw.text((960, 835), spec.get("footer", ""), font=_font(theme, 34), fill=theme.dark_blue, anchor="mm")


def _render_process(draw: ImageDraw.ImageDraw, theme: Theme, spec: dict[str, Any]) -> None:
    _title(draw, theme, spec)
    steps = spec["steps"]
    if not 2 <= len(steps) <= 4:
        raise ValueError("process template requires two to four steps")
    box_width = 360 if len(steps) == 4 else 460
    gap = 85
    total = len(steps) * box_width + (len(steps) - 1) * gap
    start_x = (WIDTH - total) // 2
    for index, step in enumerate(steps):
        x = start_x + index * (box_width + gap)
        draw.rounded_rectangle((x, 390, x + box_width, 650), radius=14, fill=theme.gray, outline=theme.blue, width=3)
        draw.rectangle((x, 390, x + box_width, 455), fill=theme.blue)
        draw.text((x + 30, 423), step["number"], font=_font(theme, 26, True), fill=theme.yellow, anchor="lm")
        color = theme.red if step.get("accent") == "red" else theme.text
        size = 34 if len(step["text"]) >= 6 else 38
        draw.text((x + box_width / 2, 548), step["text"], font=_font(theme, size, True), fill=color, anchor="mm")
        if index < len(steps) - 1:
            arrow_start = x + box_width + 12
            arrow_end = x + box_width + gap - 12
            draw.line((arrow_start, 520, arrow_end, 520), fill=theme.blue, width=6)
            draw.polygon(((arrow_end, 520), (arrow_end - 18, 508), (arrow_end - 18, 532)), fill=theme.blue)
    if spec.get("badge"):
        _pill(draw, theme, (650, 720, 1270, 795), spec["badge"], "light")
    _takeaway(draw, theme, spec["takeaway"])


def _render_metric_compare(draw: ImageDraw.ImageDraw, theme: Theme, spec: dict[str, Any]) -> None:
    _title(draw, theme, spec)
    draw.text((575, 520), spec["before"], font=_font(theme, 116, True), fill=theme.text, anchor="mm")
    draw.text((960, 520), "→", font=_font(theme, 90, True), fill=theme.red, anchor="mm")
    draw.text((1345, 520), spec["after"], font=_font(theme, 116, True), fill=theme.blue, anchor="mm")
    badges = spec.get("badges", [])[:3]
    styles = ("red", "blue", "light")
    boxes = ((230, 670, 675, 755), (735, 670, 1185, 755), (1245, 670, 1690, 755))
    for value, style, box in zip(badges, styles, boxes):
        _pill(draw, theme, box, value, style)
    _takeaway(draw, theme, spec["takeaway"])


def _render_chapter(draw: ImageDraw.ImageDraw, theme: Theme, spec: dict[str, Any]) -> None:
    _title(draw, theme, spec)
    items = spec["items"]
    if not 2 <= len(items) <= 3:
        raise ValueError("chapter template requires two or three items")
    box_width = 410
    gap = 90
    total = len(items) * box_width + (len(items) - 1) * gap
    start_x = (WIDTH - total) // 2
    for index, item in enumerate(items):
        x = start_x + index * (box_width + gap)
        draw.rounded_rectangle((x, 405, x + box_width, 690), radius=14, fill=theme.gray, outline=theme.blue, width=3)
        draw.rectangle((x, 405, x + box_width, 480), fill=theme.blue)
        draw.text((x + box_width / 2, 443), item["title"], font=_font(theme, 42, True), fill=theme.yellow, anchor="mm")
        draw.text((x + box_width / 2, 585), item["detail"], font=_font(theme, 34), fill=theme.text, anchor="mm")
    _takeaway(draw, theme, spec["takeaway"])


def _render_metric_grid(draw: ImageDraw.ImageDraw, theme: Theme, spec: dict[str, Any]) -> None:
    _title(draw, theme, spec)
    metrics = spec["metrics"]
    if not 2 <= len(metrics) <= 3:
        raise ValueError("metric_grid template requires two or three metrics")
    box_width = 470
    gap = 100
    total = len(metrics) * box_width + (len(metrics) - 1) * gap
    start_x = (WIDTH - total) // 2
    for index, metric in enumerate(metrics):
        x = start_x + index * (box_width + gap)
        draw.rounded_rectangle((x, 395, x + box_width, 700), radius=12, fill=theme.light_blue, outline=theme.blue, width=3)
        draw.rectangle((x, 395, x + box_width, 465), fill=theme.blue)
        color = theme.red if metric.get("accent") == "red" else theme.text
        draw.text((x + box_width / 2, 565), metric["value"], font=_font(theme, 64, True), fill=color, anchor="mm")
        draw.text((x + box_width / 2, 650), metric["label"], font=_font(theme, 32, True), fill=theme.dark_blue, anchor="mm")
    _takeaway(draw, theme, spec["takeaway"])


def _render_ending(draw: ImageDraw.ImageDraw, theme: Theme, spec: dict[str, Any]) -> None:
    draw.rectangle((0, 18, WIDTH, 355), fill=theme.blue)
    draw.text((960, 145), spec["brand"], font=_font(theme, 92, True), fill="white", anchor="mm")
    draw.text((960, 255), spec["headline"], font=_font(theme, 56, True), fill=theme.yellow, anchor="mm")
    draw.text((960, 505), spec["subline"], font=_font(theme, 70, True), fill=theme.text, anchor="mm")
    draw.rectangle((0, 625, WIDTH, 634), fill=theme.red)
    draw.rectangle((0, 634, WIDTH, 643), fill=theme.blue)
    _pill(draw, theme, (610, 720, 1310, 810), spec["badge"], "blue")


RENDERERS = {
    "hero": _render_hero,
    "process": _render_process,
    "metric_compare": _render_metric_compare,
    "chapter": _render_chapter,
    "metric_grid": _render_metric_grid,
    "ending": _render_ending,
}


def render_card(spec: dict[str, Any], theme: Theme, destination: Path) -> None:
    template = spec.get("template")
    if template not in RENDERERS:
        raise ValueError(f"unknown card template: {template}")
    image, draw = _canvas(theme)
    RENDERERS[template](draw, theme, spec)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, quality=96)


def card_content_bottom(spec: dict[str, Any]) -> int:
    template = spec.get("template")
    if template not in RENDERERS:
        raise ValueError(f"unknown card template: {template}")
    if template == "ending":
        return 810
    if template == "hero":
        return 855
    return 866
