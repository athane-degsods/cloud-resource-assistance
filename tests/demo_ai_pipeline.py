import json

from modules.json_handler import handle_model_response
from modules.llm_server import generate_recommendations
from modules.prompt_crafter import craft_prompt


def main() -> None:
    user_request = "Help me reduce cost from idle EC2 instances."

    documents = [
        {
            "name": "idle-ec2-runbook.md",
            "path": "runbooks/idle-ec2-runbook.md",
            "content": (
                "Development EC2 instances with CPU usage below 5 percent "
                "for 24 hours may be stopped after owner approval. "
                "Production instances require change approval."
            ),
        }
    ]

    ec2_records = [
        {
            "instance_id": "i-123456789",
            "name": "development-api",
            "state": "running",
            "cpu_avg_24h": 2.3,
            "network_avg": 0.8,
            "env": "development",
        },
        {
            "instance_id": "i-987654321",
            "name": "production-api",
            "state": "running",
            "cpu_avg_24h": 35.0,
            "network_avg": 20.0,
            "env": "production",
        },
    ]

    try:
        messages = craft_prompt(
            user_request=user_request,
            documents=documents,
            ec2_records=ec2_records,
        )

        raw_response = generate_recommendations(messages)

        final_response = handle_model_response(raw_response)

    except ValueError as exc:
        final_response = {
            "status": "privacy_warning",
            "summary": str(exc),
            "privacy_warning": str(exc),
            "paths": [],
            "requires_human_review": True,
        }

    print(json.dumps(final_response, indent=2))


if __name__ == "__main__":
    main()