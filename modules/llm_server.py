import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

# Do not override environment variables supplied by tests or the shell.
load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

USE_MOCK_LLM = (
    os.getenv("USE_MOCK_LLM", "true").strip().lower() == "true"
)

LLM_PROVIDER = os.getenv(
    "LLM_PROVIDER",
    "gemini",
).strip().lower()


def llm_error_response(
    message: str,
    error_type: str = "llm_error",
) -> dict[str, Any]:
    """Return a consistent safe error response."""
    return {
        "status": error_type,
        "summary": message,
        "privacy_warning": None,
        "paths": [],
        "requires_human_review": True,
    }


def mock_recommendation_response() -> dict[str, Any]:
    """Return a fixed response for local development and tests."""
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
                ],
                "steps": [
                    "Review memory and disk utilization.",
                    "Select a smaller instance type.",
                    "Approve the mock resize action.",
                ],
                "pros": [
                    "Reduces cost without stopping the service.",
                ],
                "cons": [
                    "The smaller instance may have insufficient capacity.",
                ],
                "requires_approval": True,
                "mock_action": {
                    "action": "resize_instance",
                    "instance_id": "i-123456789",
                },
            },
            {
                "id": "path_3",
                "title": "Continue monitoring",
                "risk": "low",
                "recommended": False,
                "reason": (
                    "Additional metric history can reduce uncertainty."
                ),
                "evidence": [
                    "Only 24 hours of metric data is currently available.",
                ],
                "steps": [
                    "Collect metrics for seven days.",
                    "Review CPU and network trends.",
                    "Reevaluate the resource.",
                ],
                "pros": [
                    "Avoids an immediate operational change.",
                ],
                "cons": [
                    "The current cost continues.",
                ],
                "requires_approval": True,
                "mock_action": {
                    "action": "monitor_instance",
                    "instance_id": "i-123456789",
                },
            },
        ],
    }


def _messages_to_gemini_prompt(
    messages: list[dict[str, str]],
) -> tuple[str, str]:
    """Separate system instructions from user content."""
    system_parts: list[str] = []
    user_parts: list[str] = []

    for message in messages:
        role = str(message.get("role", "")).strip().lower()
        content = str(message.get("content", "")).strip()

        if not content:
            continue

        if role == "system":
            system_parts.append(content)
        else:
            user_parts.append(content)

    return (
        "\n\n".join(system_parts),
        "\n\n".join(user_parts),
    )


def _remove_code_fences(text: str) -> str:
    """Remove accidental Markdown fences before JSON parsing."""
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return cleaned.strip()


def _parse_json_response(
    content: str,
    provider_name: str,
) -> dict[str, Any]:
    """Parse and validate a provider response as a JSON object."""
    if not content or not content.strip():
        return llm_error_response(
            f"The {provider_name} model returned an empty response.",
            "empty_response",
        )

    try:
        parsed = json.loads(_remove_code_fences(content))
    except json.JSONDecodeError:
        logger.error("%s returned invalid JSON", provider_name)

        return llm_error_response(
            f"The {provider_name} service returned invalid JSON.",
            "invalid_json",
        )

    if not isinstance(parsed, dict):
        return llm_error_response(
            f"The {provider_name} response was not a JSON object.",
            "invalid_json",
        )

    return parsed


def _call_gemini(
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    """Send crafted messages to Gemini and return parsed JSON."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv(
        "GEMINI_MODEL",
        os.getenv("LLM_MODEL", DEFAULT_GEMINI_MODEL),
    ).strip()

    if not api_key:
        return llm_error_response(
            "GEMINI_API_KEY is not configured.",
            "configuration_error",
        )

    system_instruction, user_content = _messages_to_gemini_prompt(
        messages
    )

    if not user_content:
        return llm_error_response(
            "No user content was supplied to Gemini.",
            "validation_error",
        )

    try:
        client = genai.Client(api_key=api_key)

        config_arguments: dict[str, Any] = {
            "temperature": 0.1,
            "response_mime_type": "application/json",
        }

        if system_instruction:
            config_arguments["system_instruction"] = system_instruction

        response = client.models.generate_content(
            model=model,
            contents=user_content,
            config=types.GenerateContentConfig(
                **config_arguments
            ),
        )

        return _parse_json_response(
            response.text or "",
            "Gemini",
        )

    except Exception as exc:
        # This logs the useful error in the server terminal.
        # It does not return credentials to the user.
        logger.exception(
            "Gemini request failed: %s",
            str(exc),
        )

        error_text = str(exc).lower()

        if (
            "api key not valid" in error_text
            or "invalid api key" in error_text
            or "unauthenticated" in error_text
        ):
            return llm_error_response(
                "The Gemini recommendation service authentication failed.",
                "authentication_error",
            )

        if "quota" in error_text or "resource_exhausted" in error_text:
            return llm_error_response(
                "The Gemini API quota is unavailable or exhausted.",
                "quota_error",
            )

        if "429" in error_text or "rate limit" in error_text:
            return llm_error_response(
                "The Gemini service is temporarily rate limited.",
                "rate_limit_error",
            )

        if "not found" in error_text or "404" in error_text:
            return llm_error_response(
                (
                    f"The configured Gemini model '{model}' "
                    "was not found or is unavailable."
                ),
                "model_error",
            )

        return llm_error_response(
            (
                "The Gemini recommendation service request failed. "
                "Check the server logs for details."
            ),
            "api_error",
        )


def _call_openai(
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    """Send crafted messages to OpenAI and return parsed JSON."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv(
        "OPENAI_MODEL",
        os.getenv("LLM_MODEL", DEFAULT_OPENAI_MODEL),
    ).strip()

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
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            response_format={
                "type": "json_object",
            },
        )

        content = response.choices[0].message.content or ""

        return _parse_json_response(
            content,
            "OpenAI",
        )

    except AuthenticationError:
        logger.error("OpenAI authentication failed")

        return llm_error_response(
            "The OpenAI recommendation service authentication failed.",
            "authentication_error",
        )

    except APITimeoutError:
        logger.error("OpenAI request timed out")

        return llm_error_response(
            "The OpenAI recommendation service timed out.",
            "timeout_error",
        )

    except APIConnectionError:
        logger.error("OpenAI connection failed")

        return llm_error_response(
            "The OpenAI recommendation service is unavailable.",
            "connection_error",
        )

    except RateLimitError as exc:
        logger.warning("OpenAI quota or rate limit reached")

        error_code = getattr(exc, "code", None)

        if error_code == "insufficient_quota":
            return llm_error_response(
                "OpenAI API quota is unavailable.",
                "quota_error",
            )

        return llm_error_response(
            "The OpenAI service is temporarily rate limited.",
            "rate_limit_error",
        )

    except APIStatusError as exc:
        logger.error(
            "OpenAI returned status code %s",
            exc.status_code,
        )

        return llm_error_response(
            (
                "The OpenAI recommendation service returned "
                f"error {exc.status_code}."
            ),
            "api_error",
        )

    except Exception as exc:
        logger.exception(
            "Unexpected OpenAI error: %s",
            str(exc),
        )

        return llm_error_response(
            "An unexpected OpenAI service error occurred.",
            "llm_error",
        )


def generate_recommendations(
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    """Use mock, Gemini, or OpenAI to generate recommendations."""
    if not messages:
        return llm_error_response(
            "No messages were supplied to the LLM.",
            "validation_error",
        )

    if USE_MOCK_LLM:
        logger.info("Using mock LLM response")
        return mock_recommendation_response()

    if LLM_PROVIDER == "gemini":
        logger.info("Using live Gemini model")
        return _call_gemini(messages)

    if LLM_PROVIDER == "openai":
        logger.info("Using live OpenAI model")
        return _call_openai(messages)

    return llm_error_response(
        f"Unsupported LLM provider: {LLM_PROVIDER}",
        "configuration_error",
    )


def call_llm(
    prompt: str | list[dict[str, str]],
) -> dict[str, Any]:
    """
    Compatibility wrapper for app.py.

    Accept either a plain string or the message list returned by
    craft_prompt().
    """
    if isinstance(prompt, str):
        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]
    elif isinstance(prompt, list):
        messages = prompt
    else:
        return llm_error_response(
            "The LLM prompt must be a string or message list.",
            "validation_error",
        )

    return generate_recommendations(messages)