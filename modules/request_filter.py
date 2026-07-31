"""Filter and request — match words to runbook metadata, extract embedded paths."""

from __future__ import annotations

import json
from pathlib import Path

METADATA_PATH = Path(__file__).resolve().parent.parent / "runbook" / "metadata.json"


def _load_metadata() -> list[dict]:
    if not METADATA_PATH.exists():
        return []
    with METADATA_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def filter_and_request(words: list[str]) -> list[str]:
    """
    params: words: list[str]  (from string_breakdown)
    return: paths: list[str]  (path field from each matched metadata record)
    """
    word_set = {w.lower() for w in words if w}
    paths: list[str] = []

    for record in _load_metadata():
        keywords = {str(k).lower() for k in record.get("keywords", [])}
        if word_set & keywords:
            path = record.get("path")
            if path:
                paths.append(str(path))

    return paths
