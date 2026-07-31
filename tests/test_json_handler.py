from modules.json_handler import handle_model_response


def make_path(action="monitor_instance"):
    return {
        "id": "path_1",
        "title": "Test recommendation",
        "risk": "low",
        "recommended": False,
        "reason": "Test reason",
        "evidence": ["Test evidence"],
        "steps": ["Test step"],
        "pros": ["Test benefit"],
        "cons": ["Test drawback"],
        "requires_approval": True,
        "mock_action": {
            "action": action,
            "instance_id": "i-123456",
        },
    }


def test_invalid_json_returns_safe_response():
    result = handle_model_response("not valid json")

    assert result["status"] == "invalid_response"
    assert result["paths"] == []
    assert result["requires_human_review"] is True


def test_success_response_with_three_paths():
    response = {
        "status": "success",
        "summary": "Test success",
        "paths": [
            make_path(),
            make_path(),
            make_path(),
        ],
    }

    result = handle_model_response(response)

    assert result["status"] == "success"
    assert len(result["paths"]) == 3
    assert result["requires_human_review"] is True


def test_two_paths_are_rejected():
    response = {
        "status": "success",
        "summary": "Test",
        "paths": [
            make_path(),
            make_path(),
        ],
    }

    result = handle_model_response(response)

    assert result["status"] == "invalid_response"


def test_destructive_action_is_blocked():
    response = {
        "status": "success",
        "summary": "Dangerous test",
        "paths": [
            make_path("terminate_instance"),
            make_path(),
            make_path(),
        ],
    }

    result = handle_model_response(response)

    assert result["status"] == "blocked"
    assert result["requires_human_review"] is True