"""
Processing module — Flask app that routes a chat request through downstream modules.

Pipeline (see idea.md):
  chat → string breakdown → filter/request (runbooks)
       → EC2 processor (via AWS ingestor)
       → prompt crafting → LLM → json handler → response
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Flask, jsonify, request

from modules.ec2_processor import process_ec2
from modules.filter_request import filter_and_request
from modules.json_handler import handle_json
from modules.llm_server import call_llm
from modules.prompt_crafting import craft_prompt
from modules.string_breakdown import breakdown

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("processing")

# Simple in-memory action log (hackathon-scale)
action_log: list[dict] = []


def _log_step(step: str, detail: str = "") -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "step": step,
        "detail": detail,
    }
    action_log.append(entry)
    log.info("%s | %s", step, detail or "-")


def _pii_warning(message: str) -> str | None:
    """Lightweight private-information check on user requests."""
    # TODO: expand patterns; placeholder for safety gate
    markers = ["ssn", "password", "secret", "api_key", "access_key"]
    lowered = message.lower()
    hits = [m for m in markers if m in lowered]
    if hits:
        return f"Possible private information detected: {', '.join(hits)}"
    return None


def process_request(message: str) -> dict:
    """
    Orchestrate downstream modules for one chat turn.
    Teammates own each module body; this only routes and logs.
    """
    _log_step("request_received", message[:200])

    warning = _pii_warning(message)
    if warning:
        _log_step("pii_warning", warning)

    # 2–6: string breakdown → filter runbooks
    words = breakdown(message)
    _log_step("string_breakdown", f"words={len(words)}")

    documents = filter_and_request(words)
    _log_step("filter_and_request", f"docs={len(documents)}")

    # 7–10: EC2 data
    ec2_records = process_ec2(request_hint=message)
    _log_step("ec2_processor", f"records={len(ec2_records)}")

    # 11–12: prompt
    prompt = craft_prompt(message, documents, ec2_records)
    _log_step("prompt_crafting", f"prompt_len={len(prompt)}")

    # 13–14: LLM
    model_json = call_llm(prompt)
    _log_step("llm_server", f"keys={list(model_json.keys()) if isinstance(model_json, dict) else 'n/a'}")

    # 15–16: readable response
    readable = handle_json(model_json)
    _log_step("json_handler", f"response_len={len(readable)}")

    return {
        "readable_response": readable,
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
    User interface entry: send chat request, receive readable response.
    Body: { "message": str, "action"?: "approve" | "edit" | "reject" }
    """
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    action = body.get("action")  # approve | edit | reject (HITL; later)

    if not message:
        return jsonify({"error": "message is required"}), 400

    if action:
        _log_step("human_action", str(action))

    result = process_request(message)
    return jsonify(result)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/logs")
def logs():
    """Simple action log for the demo."""
    return jsonify({"logs": action_log})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
