from modules.llm_server import generate_recommendations


def test_mock_llm_returns_three_paths():
    messages = [
        {
            "role": "system",
            "content": "Test system prompt",
        },
        {
            "role": "user",
            "content": "Test user request",
        },
    ]

    result = generate_recommendations(messages)

    assert result["status"] == "success"
    assert len(result["paths"]) == 3
    assert result["requires_human_review"] is True


def test_empty_messages_are_rejected():
    result = generate_recommendations([])

    assert result["status"] == "validation_error"
    assert result["paths"] == []
    assert result["requires_human_review"] is True