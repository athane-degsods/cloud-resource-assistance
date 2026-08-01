"""String breakdown — split a string into an array of words."""

import re


def breakdown(text: str) -> list[str]:
    """
    params: text: str
    return: words: list[str]
    """
    if not text or not str(text).strip():
        return []

    words = re.findall(r"[a-z0-9_]+", str(text).lower())
    return words
