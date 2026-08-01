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


def test_delete_production_is_blocked_on_llm_route():
    messages = [
        {"role": "system", "content": "rules"},
        {
            "role": "user",
            "content": '{"user_request": "please delete production now"}',
        },
    ]

    result = generate_recommendations(messages)

    assert result["status"] == "blocked"
    assert result["paths"] == []
    assert "delete production" in result.get("summary", "").lower()


def test_plain_terminate_production_is_blocked():
    result = generate_recommendations(
        [{"role": "user", "content": "terminate production VMs"}]
    )
    assert result["status"] == "blocked"
    assert result["paths"] == []
