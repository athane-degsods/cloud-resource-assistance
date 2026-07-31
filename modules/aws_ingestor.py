"""AWS service ingestor — read available EC2 source (mock JSON / API stub)."""

from typing import Any


def ingest(source: str = "mock") -> dict | list:
    """
    params: source: str (path or mock endpoint id)
    return: raw_ec2_payload: dict | list
    """
    # TODO: Akshita — load mock JSON or call stub endpoint
    return {}
