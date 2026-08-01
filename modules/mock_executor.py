"""
Mock executor — allowlisted fake cloud actions only.

Never calls real AWS. Used only after human approve in the action stream.
"""

from __future__ import annotations

from typing import Any

from modules.json_handler import ALLOWED_ACTIONS, BLOCKED_ACTIONS


def _msg_stop(instance_id: str | None) -> str:
    return f"stop_instance has been accomplished for {instance_id}"


def _msg_start(instance_id: str | None) -> str:
    return f"start_instance has been accomplished for {instance_id}"


def _msg_resize(instance_id: str | None) -> str:
    return f"resize_instance has been accomplished for {instance_id}"


def _msg_monitor(instance_id: str | None) -> str:
    return f"monitor_instance has been accomplished for {instance_id}"


def _msg_no_action(instance_id: str | None) -> str:
    target = instance_id or "n/a"
    return f"no_action: nothing changed for {target}"


_HANDLERS = {
    "stop_instance": _msg_stop,
    "start_instance": _msg_start,
    "resize_instance": _msg_resize,
    "monitor_instance": _msg_monitor,
    "no_action": _msg_no_action,
}

_ACTIONS_NEEDING_INSTANCE = {
    "stop_instance",
    "start_instance",
    "resize_instance",
    "monitor_instance",
}


def execute(action: str, instance_id: str | None = None) -> dict[str, Any]:
    """
    Run one allowlisted mock action.

    return:
      success: { "ok": True,  "results": [str] }
      failure: { "ok": False, "results": [], "error": str }
    """
    normalized = (action or "").strip().lower()

    if normalized in BLOCKED_ACTIONS:
        return {
            "ok": False,
            "results": [],
            "error": f"Blocked destructive action: {normalized}",
        }

    if normalized not in ALLOWED_ACTIONS:
        return {
            "ok": False,
            "results": [],
            "error": f"Unsupported action: {normalized!r}",
        }

    if normalized in _ACTIONS_NEEDING_INSTANCE and not instance_id:
        return {
            "ok": False,
            "results": [],
            "error": f"instance_id is required for {normalized}",
        }

    handler = _HANDLERS[normalized]
    return {
        "ok": True,
        "results": [handler(instance_id)],
    }
