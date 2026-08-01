"""
Request stream orchestrator — draft-only pipeline.

Runs chat → breakdown → filter → EC2 → prompt → LLM → json handler.
Does not execute mock cloud actions (that belongs to the action stream).
"""

from __future__ import annotations

import re
import time
from typing import Any

from modules import draft_store, pipeline_log
from modules.ec2_processor import process_ec2
from modules.json_handler import handle_model_response
from modules.llm_server import call_llm
from modules.prompt_crafter import craft_prompt
from modules.request_filter import filter_and_request
from modules.string_breakdown import breakdown

# Word-boundary markers so "pass" matches but "passenger" does not.
_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("password", re.compile(r"\bpasswords?\b", re.I)),
    ("pass", re.compile(r"\bpass\b", re.I)),
    ("pwd", re.compile(r"\bpwd\b", re.I)),
    ("secret", re.compile(r"\bsecrets?\b", re.I)),
    ("ssn", re.compile(r"\bssn\b", re.I)),
    ("api_key", re.compile(r"\bapi[_-]?keys?\b", re.I)),
    ("access_key", re.compile(r"\baccess[_-]?keys?\b", re.I)),
    ("token", re.compile(r"\b(tokens?|bearer)\b", re.I)),
    ("private_key", re.compile(r"\bprivate[_-]?keys?\b", re.I)),
]


def _pii_warning(message: str) -> str | None:
    """Lightweight private-information check on user requests."""
    if not message:
        return None
    hits = [name for name, pattern in _PII_PATTERNS if pattern.search(message)]
    # Prefer the more specific label when both password and pass match.
    if "password" in hits and "pass" in hits:
        hits = [h for h in hits if h != "pass"]
    if hits:
        return f"Possible private information detected: {', '.join(hits)}"
    return None


def _blocked_privacy_response(warning: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "summary": (
            "Request blocked: possible private information detected. "
            "Remove secrets (passwords, keys, tokens) and try again."
        ),
        "privacy_warning": warning,
        "paths": [],
        "requires_human_review": True,
        "blocked_reason": warning,
    }


def run_request_stream(
    message: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    Orchestrate the request stream for one chat turn.

    params: message, optional request_id
    return: draft payload for the UI (no mock execution)
    """
    rid = request_id or pipeline_log.new_request_id()
    started = time.perf_counter()
    pipeline_log.start(rid, message)

    try:
        warning = _pii_warning(message)
        pipeline_log.step(
            rid,
            "pii_check",
            "info",
            detail=warning or "clean",
            data={"warning": warning},
        )

        if warning:
            model_response = _blocked_privacy_response(warning)
            readable = str(model_response["summary"])
            # Do not store an approvable draft for secret-bearing requests.
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            pipeline_log.step(
                rid,
                "pii_check",
                "exit",
                detail="blocked — pipeline stopped before LLM",
                data={"status": "blocked"},
            )
            pipeline_log.finish(rid, status="blocked", duration_ms=elapsed_ms)
            return {
                "request_id": rid,
                "readable_response": readable,
                "model_response": model_response,
                "pii_warning": warning,
                "words": [],
                "paths": [],
                "ec2_text": "",
                "steps": (pipeline_log.get_trace(rid) or {}).get("steps", []),
                "meta": {
                    "word_count": 0,
                    "document_count": 0,
                    "ec2_text_len": 0,
                    "duration_ms": elapsed_ms,
                    "blocked_by": "pii_check",
                },
            }

        words = breakdown(message)
        pipeline_log.step(
            rid,
            "string_breakdown",
            "exit",
            detail=f"words={len(words)}",
            data={"words": words},
        )

        documents = filter_and_request(words)
        pipeline_log.step(
            rid,
            "request_filter",
            "exit",
            detail=f"paths={len(documents)}",
            data={"paths": documents},
        )

        ec2_text = process_ec2(request_hint=message)
        pipeline_log.step(
            rid,
            "ec2_processor",
            "exit",
            detail=f"ec2_text_len={len(ec2_text)}",
            data={"ec2_text_len": len(ec2_text)},
        )

        prompt = craft_prompt(message, documents, ec2_text)
        pipeline_log.step(
            rid,
            "prompt_crafter",
            "exit",
            detail=f"messages={len(prompt) if hasattr(prompt, '__len__') else 'n/a'}",
            data={
                "message_count": len(prompt) if isinstance(prompt, list) else None,
            },
        )

        model_json = call_llm(prompt)
        status = model_json.get("status") if isinstance(model_json, dict) else None
        path_count = (
            len(model_json.get("paths") or [])
            if isinstance(model_json, dict)
            else 0
        )
        pipeline_log.step(
            rid,
            "llm_server",
            "exit",
            detail=f"status={status} paths={path_count}",
            data={
                "status": status,
                "path_count": path_count,
                "keys": list(model_json.keys()) if isinstance(model_json, dict) else [],
            },
        )

        model_response = handle_model_response(model_json)
        readable = str(model_response.get("summary", model_response))
        pipeline_log.step(
            rid,
            "json_handler",
            "exit",
            detail=(
                f"status={model_response.get('status')} "
                f"readable_len={len(readable)}"
            ),
            data={
                "status": model_response.get("status"),
                "readable_len": len(readable),
                "path_count": len(model_response.get("paths") or []),
            },
        )

        draft_store.put(rid, model_response)
        pipeline_log.step(
            rid,
            "draft_store",
            "exit",
            detail=f"stored request_id={rid}",
            data={
                "request_id": rid,
                "status": model_response.get("status"),
                "path_count": len(model_response.get("paths") or []),
            },
        )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        pipeline_log.finish(rid, status="ok", duration_ms=elapsed_ms)

        return {
            "request_id": rid,
            "readable_response": readable,
            "model_response": model_response,
            "pii_warning": warning,
            "words": words,
            "paths": documents,
            "ec2_text": ec2_text,
            "steps": (pipeline_log.get_trace(rid) or {}).get("steps", []),
            "meta": {
                "word_count": len(words),
                "document_count": len(documents),
                "ec2_text_len": len(ec2_text),
                "duration_ms": elapsed_ms,
            },
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        pipeline_log.step(
            rid,
            "request_orchestrator",
            "error",
            detail=f"{type(exc).__name__}: {exc}",
        )
        pipeline_log.finish(rid, status="error", duration_ms=elapsed_ms)
        raise


# Backward-compatible alias used by older docs / callers
process_request = run_request_stream
