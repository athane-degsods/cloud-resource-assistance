import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

load_dotenv(override=True)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4.1-mini"

# Keep this True to run without paid OpenAI API usage.
# Change it to False later when API billing is available.
USE_MOCK_LLM = False


def llm_error_response(
    message: str,
    error_type: str = "llm_error",
) -> dict[str, Any]:
    """
    Return a consistent and safe response when the LLM request fails.
    """
    return {
        "status": error_type,
        "summary": message,
        "privacy_warning": None,
        "paths": [],
        "requires_human_review": True,
    }


def mock_recommendation_response() -> dict[str, Any]:
    """
    Return a realistic mock LLM response for the hackathon demo.

    This lets the complete application run without purchasing API credits.
    """
    return {
        "status": "success",
        "summary": (
            "One development EC2 instance appears idle and may be "
            "optimized after human review."
        ),
        "privacy_warning": None,
        "requires_human_review": True,
        "paths": [
            {
                "id": "path_1",
                "title": "Stop the idle development instance",
                "risk": "medium",
                "recommended": True,
                "reason": (
                    "The development instance has low CPU utilization "
                    "and appears underused."
                ),
                "evidence": [
                    "CPU average is below 5 percent.",
                    "The resource belongs to the development environment.",
                ],
                "steps": [
                    "Confirm that there are no scheduled workloads.",
                    "Verify the application owner.",
                    "Review the selected instance ID.",
                    "Approve the mock stop action.",
                ],
                "pros": [
                    "Reduces EC2 compute cost.",
                    "The instance can be started again later.",
                ],
                "cons": [
                    "The application will be unavailable while stopped.",
                    "A startup delay may occur when service is restored.",
                ],
                "requires_approval": True,
                "mock_action": {
                    "action": "stop_instance",
                    "instance_id": "i-123456789",
                },
            },
            {
                "id": "path_2",
                "title": "Resize the EC2 instance",
                "risk": "medium",
                "recommended": False,
                "reason": (
                    "A smaller instance may reduce cost while keeping "
                    "the service available."
                ),
                "evidence": [
                    "CPU utilization is consistently low.",
                    "The current workload may not require the existing capacity.",
                ],
                "steps": [
                    "Review memory and disk utilization.",
                    "Check the runbook for approved instance types.",
                    "Select a smaller instance type.",
                    "Schedule a maintenance period.",
                    "Approve the mock resize action.",
                ],
                "pros": [
                    "Reduces cost without permanently stopping the service.",
                    "Maintains a running compute resource.",
                ],
                "cons": [
                    "The smaller instance may have insufficient capacity.",
                    "Resizing may require a restart.",
                ],
                "requires_approval": True,
                "mock_action": {
                    "action": "resize_instance",
                    "instance_id": "i-123456789",
                },
            },
            {
                "id": "path_3",
                "title": "Continue monitoring before making a change",
                "risk": "low",
                "recommended": False,
                "reason": (
                    "Additional metric history can reduce uncertainty "
                    "before changing the resource."
                ),
                "evidence": [
                    "Only 24 hours of average metric data is currently available.",
                ],
                "steps": [
                    "Collect CPU and network metrics for seven days.",
                    "Check for scheduled or periodic workloads.",
                    "Review weekday and weekend usage.",
                    "Reevaluate the instance after collecting more evidence.",
                ],
                "pros": [
                    "Avoids an immediate operational change.",
                    "Provides more evidence for the final decision.",
                ],
                "cons": [
                    "The existing cost continues during monitoring.",
                    "Cost savings are delayed.",
                ],
                "requires_approval": True,
                "mock_action": {
                    "action": "monitor_instance",
                    "instance_id": "i-123456789",
                },
            },
        ],
    }


def call_llm(prompt: str | list[dict[str, str]]) -> dict[str, Any]:
    """Adapter for app.py — accept a prompt string or chat messages."""
    if isinstance(prompt, str):
        messages = [{"role": "user", "content": prompt}]
    else:
        messages = prompt
    return generate_recommendations(messages)


def generate_recommendations(
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    """
    Generate cloud-resource recommendations.

    In mock mode, this function returns a predefined response.

    In live mode, it sends the crafted messages to the OpenAI API and
    returns the model response as a Python dictionary.
    """

    if not messages:
        return llm_error_response(
            "No messages were supplied to the LLM.",
            "validation_error",
        )

    if USE_MOCK_LLM:
        logger.info("Using mock LLM response")
        return mock_recommendation_response()

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("LLM_MODEL", DEFAULT_MODEL)

    if not api_key:
        return llm_error_response(
            "OPENAI_API_KEY is not configured.",
            "configuration_error",
        )

    client = OpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=1,
    )

    try:
        logger.info(
            "Sending cloud recommendation request to model %s",
            model,
        )

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content

        if not content:
            return llm_error_response(
                "The model returned an empty response.",
                "empty_response",
            )

        return json.loads(content)

    except AuthenticationError:
        logger.error("LLM authentication failed")

        return llm_error_response(
            "The recommendation service authentication failed.",
            "authentication_error",
        )

    except APITimeoutError:
        logger.error("LLM request timed out")

        return llm_error_response(
            "The recommendation service timed out. Please try again.",
            "timeout_error",
        )

    except APIConnectionError:
        logger.error("Could not connect to the LLM service")

        return llm_error_response(
            "The recommendation service is temporarily unavailable.",
            "connection_error",
        )

    except RateLimitError as exc:
        logger.warning("LLM quota or rate limit reached")

        error_code = getattr(exc, "code", None)

        if error_code == "insufficient_quota":
            return llm_error_response(
                (
                    "OpenAI API quota is unavailable. "
                    "Enable mock mode or configure API billing."
                ),
                "quota_error",
            )

        return llm_error_response(
            "The recommendation service is temporarily rate limited.",
            "rate_limit_error",
        )

    except APIStatusError as exc:
        logger.error(
            "LLM API returned status code %s",
            exc.status_code,
        )

        return llm_error_response(
            (
                "The recommendation service returned an error: "
                f"{exc.status_code}."
            ),
            "api_error",
        )

    except json.JSONDecodeError:
        logger.error("The LLM response was not valid JSON")

        return llm_error_response(
            "The recommendation service returned invalid JSON.",
            "invalid_json",
        )

    except Exception as exc:
        logger.error(
            "Unexpected LLM error: %s",
            type(exc).__name__,
        )

        return llm_error_response(
            "An unexpected recommendation service error occurred.",
            "llm_error",
        )
