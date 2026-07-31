"""LLM server — model inference (external API)."""


def call_llm(prompt: str) -> dict:
    """
    params: prompt: str (or chat messages)
    return: model_response_json: dict
            (summary + 3 paths with steps, risk, pros/cons, evidence)
    """
    # TODO: Mrunali — call external LLM API
    return {
        "summary": "",
        "paths": [],
    }
