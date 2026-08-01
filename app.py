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
import time
from typing import Any

from flask import Flask, jsonify, render_template, request

from modules import pipeline_log
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

logger = logging.getLogger("processing")


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
    request_id: str | None = None,
    duration_ms: int = 0,
) -> dict[str, Any]:
    """Create a consistent safe response when processing fails."""
    result: dict[str, Any] = {
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
            "duration_ms": duration_ms,
        },
    }

    if request_id:
        result["request_id"] = request_id
        result["steps"] = (
            pipeline_log.get_trace(request_id) or {}
        ).get("steps", [])

    return result


def process_request(
    message: str,
    request_id: str | None = None,
    action: str | None = None,
) -> dict[str, Any]:
    """Route one user request through the complete pipeline."""
    rid = request_id or pipeline_log.new_request_id()
    started = time.perf_counter()

    pipeline_log.start(rid, message)

    warning = _pii_warning(message)

    try:
        if action:
            pipeline_log.step(
                rid,
                "human_action",
                "info",
                detail=action,
                data={"action": action},
            )

        pipeline_log.step(
            rid,
            "pii_check",
            "info",
            detail=warning or "clean",
            data={"warning": warning},
        )

        # Step 1: Break the request into searchable words.
        try:
            words = breakdown(message)
        except Exception as exc:
            pipeline_log.step(
                rid,
                "string_breakdown",
                "error",
                detail=type(exc).__name__,
            )

            elapsed_ms = int(
                (time.perf_counter() - started) * 1000
            )

            pipeline_log.finish(
                rid,
                status="error",
                duration_ms=elapsed_ms,
            )

            return _safe_processing_error(
                status="processing_error",
                summary="The request could not be analyzed.",
                warning=warning,
                request_id=rid,
                duration_ms=elapsed_ms,
            )

        pipeline_log.step(
            rid,
            "string_breakdown",
            "exit",
            detail=f"words={len(words)}",
            data={"words": words},
        )

        # Step 2: Select relevant runbook documents.
        try:
            documents = filter_and_request(words)
        except Exception as exc:
            pipeline_log.step(
                rid,
                "filter_and_request",
                "error",
                detail=type(exc).__name__,
            )
            documents = []

        pipeline_log.step(
            rid,
            "filter_and_request",
            "exit",
            detail=f"documents={len(documents)}",
            data={"document_count": len(documents)},
        )

        # Step 3: Obtain cleaned EC2 records.
        try:
            ec2_records = process_ec2(request_hint=message)
        except Exception as exc:
            pipeline_log.step(
                rid,
                "ec2_processor",
                "error",
                detail=type(exc).__name__,
            )
            ec2_records = []

        pipeline_log.step(
            rid,
            "ec2_processor",
            "exit",
            detail=f"records={len(ec2_records)}",
            data={"ec2_record_count": len(ec2_records)},
        )

        # Step 4: Build secure prompt messages.
        try:
            prompt_messages = craft_prompt(
                user_request=message,
                documents=documents,
                ec2_records=ec2_records,
            )
        except ValueError as exc:
            pipeline_log.step(
                rid,
                "prompt_crafter",
                "error",
                detail=str(exc),
            )

            elapsed_ms = int(
                (time.perf_counter() - started) * 1000
            )

            pipeline_log.finish(
                rid,
                status="blocked",
                duration_ms=elapsed_ms,
            )

            return {
                "request_id": rid,
                "recommendation": {
                    "status": "privacy_warning",
                    "summary": str(exc),
                    "privacy_warning": str(exc),
                    "paths": [],
                    "requires_human_review": True,
                },
                "pii_warning": str(exc),
                "steps": (
                    pipeline_log.get_trace(rid) or {}
                ).get("steps", []),
                "meta": {
                    "word_count": len(words),
                    "document_count": len(documents),
                    "ec2_record_count": len(ec2_records),
                    "duration_ms": elapsed_ms,
                },
            }
        except Exception as exc:
            pipeline_log.step(
                rid,
                "prompt_crafter",
                "error",
                detail=type(exc).__name__,
            )

            elapsed_ms = int(
                (time.perf_counter() - started) * 1000
            )

            pipeline_log.finish(
                rid,
                status="error",
                duration_ms=elapsed_ms,
            )

            return {
                "request_id": rid,
                "recommendation": {
                    "status": "processing_error",
                    "summary": (
                        "The LLM prompt could not be created."
                    ),
                    "privacy_warning": warning,
                    "paths": [],