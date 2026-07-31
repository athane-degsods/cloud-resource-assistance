"""EC2 data processor — normalize raw EC2 info to clean records."""

from typing import TypedDict

from modules.aws_ingestor import ingest


class EC2Record(TypedDict):
    instance_id: str
    name: str
    state: str
    cpu_avg_24h: int
    network_avg: int
    env: str


def process_ec2(request_hint: str = "") -> list[EC2Record]:
    """
    params: request_hint: str (optional filters from user intent)
    return: ec2_records: list[EC2Record]
    """
    # TODO: Akshita — ask ingestor, normalize to clean CSV-shaped records
    _raw: dict | list = ingest(source="mock")
    return []
