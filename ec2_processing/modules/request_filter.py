import re

def validate_request(user_request):
    """
    Validate the user's cloud request.

    Args:
        user_request (str): User's request.

    Returns:
        dict: Validation result.
    """

    request = user_request.lower()

    # Check for email addresses
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    if re.search(email_pattern, user_request):
        return {
            "status": "Warning",
            "risk": "Medium",
            "message": "Private information detected. Please review before proceeding."
        }

    result = {
        "status": "",
        "risk": "",
        "message": ""
    }

    # Check for high-risk keywords
    if (
        "delete" in request
        or "terminate" in request
        or "production" in request
    ):
        result["status"] = "High Risk"
        result["risk"] = "High"
        result["message"] = "Human approval required."

    else:
        result["status"] = "Safe"
        result["risk"] = "Low"
        result["message"] = "Request approved."

    return result