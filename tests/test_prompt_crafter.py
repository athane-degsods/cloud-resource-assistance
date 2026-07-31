import pytest

from modules.prompt_crafter import craft_prompt


def test_craft_prompt_returns_two_messages():
    messages = craft_prompt(
        user_request="Find idle development EC2 instances.",
        documents=[],
        ec2_records=[],
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_empty_request_is_rejected():
    with pytest.raises(ValueError):
        craft_prompt(
            user_request="",
            documents=[],
            ec2_records=[],
        )


def test_sensitive_key_is_rejected():
    with pytest.raises(ValueError):
        craft_prompt(
            user_request="Use this key AKIA1234567890ABCDEF",
            documents=[],
            ec2_records=[],
        )