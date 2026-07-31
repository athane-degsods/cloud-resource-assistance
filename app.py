"""
Processing module — Flask app that routes a chat request through downstream modules.

Pipeline:
chat request
    → string breakdown
    → runbook selection
    → EC2 processing
    → prompt crafting
    → LLM server
    → JSON validation
    → safe response
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, request

from modules.ec2_processor import process_ec2
from modules.filter_request import filter_and_request
from modules.json_handler import handle_model_response
from modules.llm_server import call_llm
from modules.prompt_crafter import craft_prompt
from modules.string_breakdown import breakdown


app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

log = logging.getLogger("processing")

# Simple in-memory action log for the hackathon prototype.
action_log: list[dict[str, Any]] = []


def _log_step(step: str, detail: str = "") -> None:
    """Add one pipeline activity to the action log."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "step": step,
        "detail": detail,
    }

    action_log.append(entry)
    log.info("%s | %s", step, detail or "-")


def _pii_warning(message: str) -> str | None:
    """Perform a lightweight private-information check."""
    markers = [
        "ssn",
        "password",
        "secret",
        "api_key",
        "api key",
        "access_key",
        "access key",
        "private key",
    ]

    lowered = message.lower()
    hits = [marker for marker in markers if marker in lowered]

    if hits:
        return (
            "Possible private information detected: "
            + ", ".join(hits)
        )

    return None


def _safe_processing_error(
    status: str,
    summary: str,
    warning: str | None = None,
) -> dict[str, Any]:
    """Create a consistent safe response when processing fails."""
    return {
        "recommendation": {
            "status": status,
            "summary": summary,
            "privacy_warning": warning,
            "paths": [],
            "requires_human_review": True,
        },
        "pii_warning": warning,
        "meta": {
            "word_count": 0,
            "document_count": 0,
            "ec2_record_count": 0,
        },
    }


def process_request(message: str) -> dict[str, Any]:
    """Route one user request through the complete pipeline."""
    _log_step("request_received", message[:200])

    warning = _pii_warning(message)

    if warning:
        _log_step("pii_warning", warning)

    # Step 1: Break the request into searchable words.
    try:
        words = breakdown(message)
    except Exception as exc:
        _log_step(
            "string_breakdown_error",
            type(exc).__name__,
        )

        return _safe_processing_error(
            status="processing_error",
            summary="The request could not be analyzed.",
            warning=warning,
        )

    _log_step(
        "string_breakdown",
        f"words={len(words)}",
    )

    # Step 2: Select relevant runbook documents.
    try:
        documents = filter_and_request(words)
    except Exception as exc:
        _log_step(
            "filter_and_request_error",
            type(exc).__name__,
        )
        documents = []

    _log_step(
        "filter_and_request",
        f"docs={len(documents)}",
    )

    # Step 3: Obtain cleaned EC2 records.
    try:
        ec2_records = process_ec2(request_hint=message)
    except Exception as exc:
        _log_step(
            "ec2_processor_error",
            type(exc).__name__,
        )
        ec2_records = []

    _log_step(
        "ec2_processor",
        f"records={len(ec2_records)}",
    )

    # Step 4: Build secure prompt messages.
    try:
        prompt_messages = craft_prompt(
            user_request=message,
            documents=documents,
            ec2_records=ec2_records,
        )
    except ValueError as exc:
        _log_step(
            "prompt_validation_error",
            str(exc),
        )

        return {
            "recommendation": {
                "status": "privacy_warning",
                "summary": str(exc),
                "privacy_warning": str(exc),
                "paths": [],
                "requires_human_review": True,
            },
            "pii_warning": str(exc),
            "meta": {
                "word_count": len(words),
                "document_count": len(documents),
                "ec2_record_count": len(ec2_records),
            },
        }
    except Exception as exc:
        _log_step(
            "prompt_crafting_error",
            type(exc).__name__,
        )

        return {
            "recommendation": {
                "status": "processing_error",
                "summary": "The LLM prompt could not be created.",
                "privacy_warning": warning,
                "paths": [],
                "requires_human_review": True,
            },
            "pii_warning": warning,
            "meta": {
                "word_count": len(words),
                "document_count": len(documents),
                "ec2_record_count": len(ec2_records),
            },
        }

    _log_step(
        "prompt_crafting",
        f"message_count={len(prompt_messages)}",
    )

    # Step 5: Call mock or live LLM.
    model_json = call_llm(prompt_messages)

    if isinstance(model_json, dict):
        _log_step(
            "llm_server",
            f"status={model_json.get('status', 'unknown')}",
        )
    else:
        _log_step(
            "llm_server",
            "invalid non-dictionary response",
        )

    # Step 6: Validate and normalize model output.
    validated_response = handle_model_response(model_json)

    _log_step(
        "json_handler",
        f"status={validated_response.get('status')}",
    )

    return {
        "recommendation": validated_response,
        "model_response": model_json,
        "pii_warning": warning,
        "meta": {
            "word_count": len(words),
            "document_count": len(documents),
            "ec2_record_count": len(ec2_records),
        },
    }


@app.post("/chat")
def chat():
    """
    Process a cloud-resource assistance request.

    JSON body:
    {
        "message": "Help me reduce cost from idle EC2 instances",
        "action": "approve | edit | reject"
    }
    """
    body = request.get_json(silent=True) or {}

    message = str(body.get("message") or "").strip()
    action = body.get("action")

    if not message:
        return jsonify(
            {
                "status": "validation_error",
                "summary": "message is required",
                "paths": [],
                "requires_human_review": True,
            }
        ), 400

    if action:
        allowed_actions = {
            "approve",
            "edit",
            "reject",
        }

        normalized_action = str(action).strip().lower()

        if normalized_action not in allowed_actions:
            return jsonify(
                {
                    "status": "validation_error",
                    "summary": (
                        "action must be approve, edit, or reject"
                    ),
                    "paths": [],
                    "requires_human_review": True,
                }
            ), 400

        _log_step(
            "human_action",
            normalized_action,
        )

    result = process_request(message)

    return jsonify(result)


@app.get("/health")
def health():
    """Health-check endpoint."""
    return jsonify(
        {
            "status": "ok",
        }
    )


@app.get("/logs")
def logs():
    """Return the in-memory action log."""
    return jsonify(
        {
            "logs": action_log,
        }
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )