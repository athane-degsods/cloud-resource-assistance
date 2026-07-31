"""
Processing module — Flask app that routes a chat request through downstream modules.

Pipeline (see idea.md):
  chat → string breakdown → filter/request (runbooks)
       → EC2 processor (via AWS ingestor)
       → prompt crafting → LLM → json handler → response
"""

from __future__ import annotations

import logging
import time

from flask import Flask, jsonify, render_template, request

from modules import pipeline_log
from modules.ec2_processor import process_ec2
from modules.json_handler import handle_json
from modules.llm_server import call_llm
from modules.prompt_crafter import craft_prompt
from modules.request_filter import filter_and_request
from modules.string_breakdown import breakdown

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def _pii_warning(message: str) -> str | None:
    """Lightweight private-information check on user requests."""
    markers = ["ssn", "password", "secret", "api_key", "access_key"]
    lowered = message.lower()
    hits = [m for m in markers if m in lowered]
    if hits:
        return f"Possible private information detected: {', '.join(hits)}"
    return None


def process_request(
    message: str,
    request_id: str | None = None,
    action: str | None = None,
) -> dict:
    """
    Orchestrate downstream modules for one chat turn.
    Phase 1 logging: spine only (enter/exit around each module call).
    """
    rid = request_id or pipeline_log.new_request_id()
    started = time.perf_counter()
    pipeline_log.start(rid, message)

    try:
        if action:
            pipeline_log.step(
                rid,
                "human_action",
                "info",
                detail=str(action),
                data={"action": action},
            )

        warning = _pii_warning(message)
        pipeline_log.step(
            rid,
            "pii_check",
            "info",
            detail=warning or "clean",
            data={"warning": warning},
        )

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

        readable = handle_json(model_json)
        pipeline_log.step(
            rid,
            "json_handler",
            "exit",
            detail=f"readable_len={len(readable)}",
            data={"readable_len": len(readable)},
        )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        pipeline_log.finish(rid, status="ok", duration_ms=elapsed_ms)

        return {
            "request_id": rid,
            "readable_response": readable,
            "model_response": model_json,
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
            "processing",
            "error",
            detail=f"{type(exc).__name__}: {exc}",
        )
        pipeline_log.finish(rid, status="error", duration_ms=elapsed_ms)
        raise


@app.get("/")
def index():
    """Serve the HTML chat page."""
    return render_template("index.html")


@app.post("/chat")
def chat():
    """
    User interface entry: send chat request, receive readable response.
    Body: { "message": str, "action"?: "approve" | "edit" | "reject" }
    """
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    action = body.get("action")  # approve | edit | reject (HITL; later)

    if not message:
        return jsonify({"error": "message is required"}), 400

    result = process_request(message, action=action)
    return jsonify(result)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/logs")
def logs_page():
    """Readable HTML view of pipeline logs (browser-friendly)."""
    return render_template(
        "logs.html",
        requests=pipeline_log.get_recent_summaries(),
        events=pipeline_log.get_recent_events(limit=50),
    )


@app.get("/logs.json")
def logs_json():
    """Machine-readable log dump."""
    return jsonify(
        {
            "requests": pipeline_log.get_recent_summaries(),
            "events": pipeline_log.get_recent_events(),
        }
    )


@app.get("/logs/<request_id>")
def logs_for_request(request_id: str):
    """Full ordered trail for one chat request (HTML in browser, JSON if asked)."""
    trace = pipeline_log.get_trace(request_id)
    if not trace:
        return jsonify({"error": "request_id not found"}), 404

    wants_json = (
        request.args.get("format") == "json"
        or request.accept_mimetypes.best_match(
            ["text/html", "application/json"]
        )
        == "application/json"
    )
    if wants_json:
        return jsonify(trace)
    return render_template("logs_detail.html", trace=trace)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
