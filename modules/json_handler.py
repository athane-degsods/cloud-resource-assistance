import json
from typing import Any


ALLOWED_RISKS = {
    "low",
    "medium",
    "high",
    "critical",
}

ALLOWED_ACTIONS = {
    "stop_instance",
    "start_instance",
    "resize_instance",
    "monitor_instance",
    "no_action",
}

BLOCKED_ACTIONS = {
    "terminate_instance",
    "delete_instance",
    "delete_production",
    "delete_volume",
    "disable_logging",
    "disable_monitoring",
}


def safe_response(
    status: str,
    summary: str,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    """
    Create a consistent safe response for errors,
    blocked actions, or invalid model output.
    """
    response = {
        "status": status,
        "summary": summary,
        "privacy_warning": None,
        "paths": [],
        "requires_human_review": True,
    }

    if blocked_reason:
        response["blocked_reason"] = blocked_reason

    return response


def remove_code_fences(raw_text: str) -> str:
    """
    Remove accidental Markdown code fences from model output.
    """
    text = raw_text.strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def parse_response(
    response: dict[str, Any] | str,
) -> dict[str, Any]:
    """
    Convert the model response into a Python dictionary.
    """
    if isinstance(response, dict):
        return response

    if not isinstance(response, str):
        raise ValueError(
            "Response must be a dictionary or a JSON string."
        )

    cleaned_response = remove_code_fences(response)

    return json.loads(cleaned_response)


def validate_path(
    path: dict[str, Any],
    position: int,
) -> tuple[bool, str | None]:
    """
    Validate one recommendation path.
    """
    required_fields = [
        "id",
        "title",
        "risk",
        "reason",
        "evidence",
        "steps",
        "pros",
        "cons",
        "requires_approval",
        "mock_action",
    ]

    for field in required_fields:
        if field not in path:
            return (
                False,
                f"Path {position} is missing required field '{field}'.",
            )

    risk = str(path["risk"]).lower()

    if risk not in ALLOWED_RISKS:
        return (
            False,
            f"Path {position} contains an invalid risk level.",
        )

    if path["requires_approval"] is not True:
        return (
            False,
            f"Path {position} does not require human approval.",
        )

    if not isinstance(path["evidence"], list):
        return (
            False,
            f"Path {position} evidence must be a list.",
        )

    if not isinstance(path["steps"], list):
        return (
            False,
            f"Path {position} steps must be a list.",
        )

    if not isinstance(path["pros"], list):
        return (
            False,
            f"Path {position} pros must be a list.",
        )

    if not isinstance(path["cons"], list):
        return (
            False,
            f"Path {position} cons must be a list.",
        )

    mock_action = path["mock_action"]

    if not isinstance(mock_action, dict):
        return (
            False,
            f"Path {position} mock_action must be an object.",
        )

    action = mock_action.get("action")

    if action in BLOCKED_ACTIONS:
        return (
            False,
            f"Blocked destructive action detected: {action}.",
        )

    if action not in ALLOWED_ACTIONS:
        return (
            False,
            f"Path {position} contains an unsupported action.",
        )

    return True, None


def handle_model_response(
    response: dict[str, Any] | str,
) -> dict[str, Any]:
    """
    Parse, validate, and normalize the LLM response.
    """
    try:
        parsed = parse_response(response)
    except (ValueError, TypeError, json.JSONDecodeError):
        return safe_response(
            status="invalid_response",
            summary="The AI returned an invalid JSON response.",
        )

    status = parsed.get("status")

    error_statuses = {
    "llm_error",
    "configuration_error",
    "authentication_error",
    "timeout_error",
    "connection_error",
    "api_error",
    "invalid_json",
    "validation_error",
    "quota_error",
    "rate_limit_error",
    "empty_response",
    "model_error",
}

    if status in error_statuses:
        return safe_response(
            status=status,
            summary=parsed.get(
                "summary",
                "The recommendation service failed.",
            ),
        )

    if status == "blocked":
        return safe_response(
            status="blocked",
            summary=parsed.get(
                "summary",
                "The requested action was blocked.",
            ),
            blocked_reason=parsed.get(
                "blocked_reason",
                "Unsafe or destructive cloud action.",
            ),
        )

    if status == "insufficient_data":
        return safe_response(
            status="insufficient_data",
            summary=parsed.get(
                "summary",
                "There is not enough evidence to make a recommendation.",
            ),
        )

    if status != "success":
        return safe_response(
            status="invalid_response",
            summary="The AI returned an unsupported status.",
        )

    paths = parsed.get("paths")

    if not isinstance(paths, list):
        return safe_response(
            status="invalid_response",
            summary="The AI response does not contain valid paths.",
        )

    if len(paths) != 3:
        return safe_response(
            status="invalid_response",
            summary=(
                "The AI must return exactly three recommendation paths."
            ),
        )

    for index, path in enumerate(paths, start=1):
        if not isinstance(path, dict):
            return safe_response(
                status="invalid_response",
                summary=f"Recommendation path {index} is invalid.",
            )

        valid, error = validate_path(path, index)

        if not valid:
            if error and "Blocked destructive action" in error:
                return safe_response(
                    status="blocked",
                    summary="A destructive cloud action was blocked.",
                    blocked_reason=error,
                )

            return safe_response(
                status="invalid_response",
                summary=error or "Recommendation validation failed.",
            )

    return {
        "status": "success",
        "summary": parsed.get(
            "summary",
            "Cloud recommendations generated.",
        ),
        "privacy_warning": parsed.get("privacy_warning"),
        "paths": paths,
        "requires_human_review": True,
    }
