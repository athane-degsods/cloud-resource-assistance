"""
Router — Flask HTTP entry for the cloud resource assistant.

Routes:
  POST /chat   → request stream (draft only)
  POST /decide → action stream (HITL; placeholder until executor/store land)
"""

from __future__ import annotations

import logging

from flask import Flask, jsonify, render_template, request

from modules import pipeline_log
from modules.decision_handler import handle_decision
from modules.request_orchestrator import run_request_stream

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


@app.get("/")
def index():
    """Serve the HTML chat page."""
    return render_template("index.html")


@app.post("/chat")
def chat():
    """
    Request stream entry: user message → AI draft (no execution).
    Body: { "message": str }
    """
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()

    if not message:
        return jsonify({"error": "message is required"}), 400

    result = run_request_stream(message)
    return jsonify(result)


@app.post("/decide")
def decide():
    """
    Action stream entry: human approve | reject | edit.
    Body: { "request_id": str, "decision": str, "path_id"?: str }
    """
    body = request.get_json(silent=True) or {}
    request_id = (body.get("request_id") or "").strip()
    decision = (body.get("decision") or "").strip()
    path_id = body.get("path_id")
    if isinstance(path_id, str):
        path_id = path_id.strip() or None
    else:
        path_id = None

    if not request_id:
        return jsonify({"error": "request_id is required"}), 400
    if not decision:
        return jsonify({"error": "decision is required"}), 400

    result = handle_decision(request_id, decision, path_id=path_id)
    status = result.get("status")
    http_status = 501 if status == "not_implemented" else 200
    if status in {"blocked"}:
        http_status = 400
    return jsonify(result), http_status


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
