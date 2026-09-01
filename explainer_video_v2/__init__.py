"""Manifest-driven explainer video builder V2."""

from .manifest import load_manifest, validate_manifest
from .pronunciation import rewrite_narration, rewrite_text

__all__ = ["load_manifest", "validate_manifest", "rewrite_narration", "rewrite_text"]
