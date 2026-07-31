"""Request-scoped pipeline tracer (Phase 1 — orchestrator spine)."""

from __future__ import annotations

import logging
import secrets
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("pipeline")

_MAX_TRACES = 100
_lock = threading.Lock()
_traces: dict[str, dict[str, Any]] = {}
_order: deque[str] = deque(maxlen=_MAX_TRACES)
# Flat event list for backward-compatible GET /logs
_events: deque[dict[str, Any]] = deque(maxlen=1000)


def new_request_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"req_{stamp}_{secrets.token_hex(2)}"


def start(request_id: str, message: str) -> None:
    preview = (message or "")[:200]
    with _lock:
        if request_id in _traces:
            _forget(request_id)
        _traces[request_id] = {
            "request_id": request_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "status": "running",
            "message_preview": preview,
            "steps": [],
        }
        _order.append(request_id)
        while len(_order) > _MAX_TRACES:
            old = _order.popleft()
            _traces.pop(old, None)

    step(request_id, "processing", "enter", detail=preview)


def step(
    request_id: str,
    component: str,
    event: str,
    detail: str = "",
    data: dict[str, Any] | None = None,
    duration_ms: int | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "request_id": request_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "seq": 0,
        "component": component,
        "event": event,
        "detail": detail or "",
        "data": data,
        "duration_ms": duration_ms,
    }

    with _lock:
        trace = _traces.get(request_id)
        if trace is not None:
            entry["seq"] = len(trace["steps"]) + 1
            trace["steps"].append(entry)
        else:
            entry["seq"] = 1
        _events.append(entry)

    log.info(
        "[%s #%s] %s | %s | %s",
        request_id,
        entry["seq"],
        component,
        event,
        detail or "-",
    )
    return entry


def finish(
    request_id: str,
    status: str = "ok",
    detail: str = "",
    duration_ms: int | None = None,
) -> None:
    step(
        request_id,
        "processing",
        "exit",
        detail=detail or f"status={status}",
        data={"status": status},
        duration_ms=duration_ms,
    )
    with _lock:
        trace = _traces.get(request_id)
        if trace is not None:
            trace["status"] = status
            trace["finished_at"] = datetime.now(timezone.utc).isoformat()
            if duration_ms is not None:
                trace["duration_ms"] = duration_ms


def get_trace(request_id: str) -> dict[str, Any] | None:
    with _lock:
        trace = _traces.get(request_id)
        return dict(trace) if trace else None


def get_recent_summaries(limit: int = 20) -> list[dict[str, Any]]:
    with _lock:
        ids = list(_order)[-limit:]
        ids.reverse()
        out = []
        for rid in ids:
            t = _traces.get(rid)
            if not t:
                continue
            out.append(
                {
                    "request_id": t["request_id"],
                    "status": t["status"],
                    "started_at": t["started_at"],
                    "finished_at": t.get("finished_at"),
                    "message_preview": t.get("message_preview"),
                    "step_count": len(t.get("steps", [])),
                    "duration_ms": t.get("duration_ms"),
                }
            )
        return out


def get_recent_events(limit: int = 100) -> list[dict[str, Any]]:
    with _lock:
        events = list(_events)[-limit:]
    events.reverse()
    return events


def _forget(request_id: str) -> None:
    _traces.pop(request_id, None)
