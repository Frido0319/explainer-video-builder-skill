"""Natural-language rewrites for TTS pronunciation and matching subtitles."""

from __future__ import annotations

import copy
from typing import Any


DEFAULT_REPLACEMENTS = {
    "重排": "重新排序",
    "重传": "重新传输",
    "多运营商": "多家运营商",
}
LOCKED_REPLACEMENTS = {"重排": "重新排序"}


def rewrite_text(text: str, replacements: dict[str, str] | None = None) -> str:
    rules = {
        source: target
        for source, target in DEFAULT_REPLACEMENTS.items()
        if source not in LOCKED_REPLACEMENTS
    }
    if replacements:
        rules.update(
            {
                source: target
                for source, target in replacements.items()
                if not any(locked in source for locked in LOCKED_REPLACEMENTS)
            }
        )
    rewritten = str(text)
    for source in sorted(rules, key=len, reverse=True):
        rewritten = rewritten.replace(source, rules[source])
    for source, target in LOCKED_REPLACEMENTS.items():
        rewritten = rewritten.replace(source, target)
    return rewritten


def rewrite_narration(data: dict[str, Any]) -> dict[str, Any]:
    rewritten = copy.deepcopy(data)
    replacements = rewritten.get("pronunciations", {})
    for narration in rewritten.get("narration", []):
        narration["text"] = rewrite_text(narration["text"], replacements)
    return rewritten
