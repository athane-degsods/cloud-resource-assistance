"""Filter and request — select relevant runbook docs by words."""

from typing import TypedDict


class RunbookDoc(TypedDict):
    name: str
    path: str
    content: str


def filter_and_request(words: list[str]) -> list[RunbookDoc]:
    """
    params: words: list[str]
    return: documents: list[RunbookDoc]
    """
    # TODO: Akshita — fetch docs from runbook folder by filtered words
    return []
