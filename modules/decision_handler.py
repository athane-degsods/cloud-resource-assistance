"""
Action stream — decision / action handler (HITL gate).

Placeholder until mock_executor + draft_store are wired.
Does not call the LLM or re-run the request stream.
"""

from __future__ import annotations

from typing import Any, Literal

from modules import pipeline_log

Decision = Literal["approve", "reject", "edit"]


def handle_decision(
    request_id: str,
    decision: Decision | str,
    path_id: str | None = None,
) -> dict[str, Any]:
    """
    Resolve a human decision against a stored draft.

    params:
      - request_id: chat turn id from the request stream
      - decision: approve | reject | edit
      - path_id: required when decision == approve

    return:
      { status, results, message, request_id, decision, path_id }

    Planned flow (teammate fill-in):
      draft_store.get(request_id)
      → approve: find path → mock_executor(action, instance_id)
      → reject / edit: log only, no execute
    """
    normalized = (decision or "").strip().lower()
    pipeline_log.step(
        request_id,
        "decision_handler",
        "info",
        detail=f"decision={normalized} path_id={path_id}",
        data={"decision": normalized, "path_id": path_id},
    )

    if normalized not in {"approve", "reject", "edit"}:
        return {
            "status": "blocked",
            "results": [],
            "message": f"Unsupported decision: {decision!r}",
            "request_id": request_id,
            "decision": normalized,
            "path_id": path_id,
        }

    if normalized == "approve" and not path_id:
        return {
            "status": "blocked",
            "results": [],
            "message": "path_id is required when decision is approve",
            "request_id": request_id,
            "decision": normalized,
            "path_id": path_id,
        }

    # Placeholder: real lookup + mock execute comes next (Mrunali / wiring).
    status_map = {
        "approve": "not_implemented",
        "reject": "rejected",
        "edit": "edit_requested",
    }
    messages = {
        "approve": "Action stream approve path not implemented yet.",
        "reject": "Decision recorded as reject (no execution).",
        "edit": "Decision recorded as edit (no execution; re-run via POST /chat).",
    }

    result = {
        "status": status_map[normalized],
        "results": [],
        "message": messages[normalized],
        "request_id": request_id,
        "decision": normalized,
        "path_id": path_id,
    }

    pipeline_log.step(
        request_id,
        "decision_handler",
        "exit",
        detail=f"status={result['status']}",
        data=result,
    )
    return result
