"""
Action stream — decision / action handler (HITL gate).

Loads the stored draft, branches on approve | reject | edit,
and mock-executes only after approve. Does not call the LLM.
"""

from __future__ import annotations

from typing import Any, Literal

from modules import draft_store, pipeline_log
from modules.mock_executor import execute

Decision = Literal["approve", "reject", "edit"]


def _response(
    status: str,
    message: str,
    request_id: str,
    decision: str,
    path_id: str | None,
    results: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "results": list(results or []),
        "message": message,
        "request_id": request_id,
        "decision": decision,
        "path_id": path_id,
    }


def _find_path(draft: dict[str, Any], path_id: str) -> dict[str, Any] | None:
    paths = draft.get("paths") or []
    if not isinstance(paths, list):
        return None
    for path in paths:
        if isinstance(path, dict) and path.get("id") == path_id:
            return path
    return None


def _approve(
    request_id: str,
    path_id: str,
    draft: dict[str, Any],
) -> dict[str, Any]:
    path = _find_path(draft, path_id)
    if not path:
        return _response(
            "blocked",
            f"Unknown path_id: {path_id}",
            request_id,
            "approve",
            path_id,
        )

    mock = path.get("mock_action") or {}
    if not isinstance(mock, dict):
        return _response(
            "blocked",
            "Path is missing a valid mock_action.",
            request_id,
            "approve",
            path_id,
        )

    action = mock.get("action")
    instance_id = mock.get("instance_id")
    if isinstance(instance_id, str):
        instance_id = instance_id.strip() or None
    else:
        instance_id = None

    outcome = execute(str(action) if action is not None else "", instance_id)
    if not outcome.get("ok"):
        return _response(
            "blocked",
            str(outcome.get("error") or "Action refused"),
            request_id,
            "approve",
            path_id,
        )

    draft_store.clear(request_id)
    return _response(
        "executed",
        "Mock action completed.",
        request_id,
        "approve",
        path_id,
        results=list(outcome.get("results") or []),
    )


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
        result = _response(
            "blocked",
            f"Unsupported decision: {decision!r}",
            request_id,
            normalized,
            path_id,
        )
        pipeline_log.step(
            request_id,
            "decision_handler",
            "exit",
            detail=f"status={result['status']}",
            data=result,
        )
        return result

    if normalized == "approve" and not path_id:
        result = _response(
            "blocked",
            "path_id is required when decision is approve",
            request_id,
            normalized,
            path_id,
        )
        pipeline_log.step(
            request_id,
            "decision_handler",
            "exit",
            detail=f"status={result['status']}",
            data=result,
        )
        return result

    draft = draft_store.get(request_id)
    if draft is None:
        result = _response(
            "not_found",
            f"No stored draft for request_id={request_id}",
            request_id,
            normalized,
            path_id,
        )
        pipeline_log.step(
            request_id,
            "decision_handler",
            "exit",
            detail=f"status={result['status']}",
            data=result,
        )
        return result

    if normalized == "approve":
        result = _approve(request_id, path_id or "", draft)
    elif normalized == "reject":
        draft_store.clear(request_id)
        result = _response(
            "rejected",
            "Decision recorded as reject (no execution).",
            request_id,
            normalized,
            path_id,
        )
    else:  # edit
        result = _response(
            "edit_requested",
            "Decision recorded as edit (no execution; re-run via POST /chat).",
            request_id,
            normalized,
            path_id,
        )

    pipeline_log.step(
        request_id,
        "decision_handler",
        "exit",
        detail=f"status={result['status']} results={len(result['results'])}",
        data=result,
    )
    return result
