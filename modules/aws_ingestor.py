"""AWS service ingestor — read raw CloudWatch-style EC2 data, return text only."""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "samples" / "ec2-cloudwatch.json"


def ingest(source: str | None = None) -> str:
    """
    params: source: str (path to raw CW/EC2 JSON; defaults to samples/ec2-cloudwatch.json)
    return: text document describing EC2 instances only
    """
    path = Path(source) if source else DEFAULT_SOURCE
    if not path.is_absolute():
        path = ROOT / path

    if not path.exists():
        log.error("CW source not found: %s", path)
        return ""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.error("Failed to ingest CW data: %s", exc)
        return ""

    return _to_ec2_text(payload)


def _to_ec2_text(payload: dict | list) -> str:
    """Keep only EC2 instance facts; format as a plain text document."""
    instances: list[dict] = []

    if isinstance(payload, dict):
        raw = payload.get("instances") or payload.get("Reservations") or []
        if isinstance(raw, list):
            # Flatten DescribeInstances-style Reservations if present
            for item in raw:
                if isinstance(item, dict) and "Instances" in item:
                    instances.extend(item.get("Instances") or [])
                elif isinstance(item, dict):
                    instances.append(item)
    elif isinstance(payload, list):
        instances = [i for i in payload if isinstance(i, dict)]

    lines = [
        "EC2 CloudWatch snapshot",
        f"source_service: {payload.get('service', 'EC2') if isinstance(payload, dict) else 'EC2'}",
        f"instance_count: {len(instances)}",
        "",
    ]

    for inst in instances:
        metrics = inst.get("Metrics") or {}
        cpu = (metrics.get("CPUUtilization") or {}).get("Average24h", "")
        network = (metrics.get("NetworkIn") or {}).get("Average24h", "")

        lines.extend(
            [
                f"instance_id: {inst.get('InstanceId', '')}",
                f"name: {inst.get('Name', '')}",
                f"state: {inst.get('State', '')}",
                f"env: {inst.get('Environment', '')}",
                f"region: {inst.get('Region', '')}",
                f"cpu_avg_24h: {cpu}",
                f"network_avg: {network}",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"
