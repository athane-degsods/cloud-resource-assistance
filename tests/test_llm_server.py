import modules.llm_server as llm_server


def test_mock_llm_returns_three_paths(monkeypatch):
    monkeypatch.setattr(llm_server, "USE_MOCK_LLM", True)

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

    result = llm_server.generate_recommendations(messages)

    assert result["status"] == "success"
    assert len(result["paths"]) == 3
    assert result["requires_human_review"] is True


def test_empty_messages_are_rejected(monkeypatch):
    monkeypatch.setattr(llm_server, "USE_MOCK_LLM", True)

    result = llm_server.generate_recommendations([])

    assert result["status"] == "validation_error"
    assert result["paths"] == []
    assert result["requires_human_review"] is True