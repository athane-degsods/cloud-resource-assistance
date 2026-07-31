import json
import re
from typing import Any


SENSITIVE_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ASIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"(?i)(password|secret|token|api[_-]?key)\s*[:=]\s*[^\s,;]+"
    ),
]


def contains_sensitive_data(text: str) -> bool:
    """
    Detect obvious credentials or private information.
    """
    if not text:
        return False

    return any(pattern.search(text) for pattern in SENSITIVE_PATTERNS)


def craft_prompt(
    user_request: str,
    documents: list[Any] | None,
    ec2_records: Any,
) -> list[dict[str, str]]:
    """
    Create the system and user messages sent to the LLM.
    documents: runbook paths (or doc dicts)
    ec2_records: EC2 text document (str) or structured records
    """

    if not user_request or not user_request.strip():
        raise ValueError("User request cannot be empty.")

    if contains_sensitive_data(user_request):
        raise ValueError(
            "Possible credential or private information detected."
        )

    safe_documents = documents or []
    safe_ec2_records = ec2_records or []

    system_prompt = """
You are a secure cloud-resource recommendation assistant.

You analyze the supplied user request, EC2 records, and runbook documents.
You provide recommendations only. You never execute cloud actions.

Rules:

1. Use only the supplied EC2 records and runbook documents.
2. Do not invent metrics, instance details, policies, or evidence.
3. Return exactly three recommendation paths when sufficient data exists.
4. Every recommendation must require human approval.
5. Include evidence from the supplied EC2 data or runbook.
6. If required information is missing, return status "insufficient_data".
7. Destructive production actions must be blocked.
8. Never recommend deleting or terminating production resources.
9. Include risks, benefits, drawbacks, and step-by-step actions.
10. Return valid JSON only.
11. Do not include Markdown or extra text outside the JSON.

Required JSON structure:

{
  "status": "success | insufficient_data | blocked",
  "summary": "short summary",
  "privacy_warning": null,
  "requires_human_review": true,
  "paths": [
    {
      "id": "path_1",
      "title": "recommendation title",
      "risk": "low | medium | high | critical",
      "recommended": true,
      "reason": "reason for recommendation",
      "evidence": ["specific evidence"],
      "steps": ["step 1", "step 2"],
      "pros": ["benefit"],
      "cons": ["drawback"],
      "requires_approval": true,
      "mock_action": {
        "action": "stop_instance | start_instance | resize_instance | monitor_instance | no_action",
        "instance_id": "instance ID or null"
      }
    }
  ]
}

For status "success", return exactly three paths.
For status "blocked" or "insufficient_data", paths may be empty.
"""

    user_payload = {
        "user_request": user_request.strip(),
        "runbook_documents": safe_documents,
        "ec2_records": safe_ec2_records,
    }

    return [
        {
            "role": "system",
            "content": system_prompt.strip(),
        },
        {
            "role": "user",
            "content": json.dumps(user_payload, indent=2),
        },
    ]