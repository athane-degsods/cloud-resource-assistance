import json

from modules.json_handler import handle_model_response


fake_response = {
    "status": "success",
    "summary": "The development instance appears idle.",
    "privacy_warning": None,
    "requires_human_review": True,
    "paths": [
        {
            "id": "path_1",
            "title": "Stop the development instance",
            "risk": "medium",
            "recommended": True,
            "reason": "CPU usage is below 5 percent.",
            "evidence": [
                "Instance i-123456 CPU average is 2.3 percent.",
                "Environment is development.",
            ],
            "steps": [
                "Confirm the application owner.",
                "Check for scheduled workloads.",
                "Approve the mock stop action.",
            ],
            "pros": ["Reduces EC2 cost."],
            "cons": ["The application becomes unavailable."],
            "requires_approval": True,
            "mock_action": {
                "action": "stop_instance",
                "instance_id": "i-123456",
            },
        },
        {
            "id": "path_2",
            "title": "Resize the instance",
            "risk": "medium",
            "recommended": False,
            "reason": "A smaller instance may reduce cost.",
            "evidence": ["CPU usage is low."],
            "steps": [
                "Review memory requirements.",
                "Select a smaller instance type.",
                "Approve the mock resize action.",
            ],
            "pros": ["Reduces cost while keeping the instance available."],
            "cons": ["The smaller instance may have insufficient capacity."],
            "requires_approval": True,
            "mock_action": {
                "action": "resize_instance",
                "instance_id": "i-123456",
            },
        },
        {
            "id": "path_3",
            "title": "Continue monitoring",
            "risk": "low",
            "recommended": False,
            "reason": "More usage history may reduce uncertainty.",
            "evidence": ["Only 24 hours of metric data is available."],
            "steps": [
                "Monitor the instance for seven days.",
                "Review CPU and network trends.",
                "Reevaluate the instance.",
            ],
            "pros": ["Avoids an immediate availability change."],
            "cons": ["Cost continues during monitoring."],
            "requires_approval": True,
            "mock_action": {
                "action": "monitor_instance",
                "instance_id": "i-123456",
            },
        },
    ],
}

result = handle_model_response(fake_response)

print(json.dumps(result, indent=2))