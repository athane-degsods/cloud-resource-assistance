def parse_request(user_request):
    """
    Parse the user's request.

    Args:
        user_request (str): User's cloud request.

    Returns:
        dict: Parsed request information.
    """

    request = user_request.lower()

    parsed_data = {
        "intent": "",
        "service": "",
        "condition": ""
    }

    # Detect user's intent
    if "cost" in request or "save" in request:
        parsed_data["intent"] = "cost_optimization"

    elif "stop" in request:
        parsed_data["intent"] = "stop_instance"

    elif "start" in request:
        parsed_data["intent"] = "start_instance"

    elif "restart" in request:
        parsed_data["intent"] = "restart_instance"

    elif "show" in request or "list" in request:
        parsed_data["intent"] = "view_metrics"

    elif "show" in request or "list" in request:
        parsed_data["intent"] = "view_metrics"

    # Detect AWS service
    if "ec2" in request:
        parsed_data["service"] = "EC2"

    elif "s3" in request:
        parsed_data["service"] = "S3"

    elif "lambda" in request:
        parsed_data["service"] = "Lambda"

    elif "rds" in request:
        parsed_data["service"] = "RDS"

        # Detect condition
    if "idle" in request:
        parsed_data["condition"] = "idle"

    elif "high cpu" in request:
        parsed_data["condition"] = "high_cpu"

    elif "stopped" in request:
        parsed_data["condition"] = "stopped"

    elif "running" in request:
        parsed_data["condition"] = "running"

    return parsed_data