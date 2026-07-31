from modules.string_breakdown import parse_request
from modules.request_filter import validate_request
from modules.aws_ingestor import load_metrics
from modules.ec2_processor import filter_ec2_instances

def process_request(user_request, metrics_file):
    """
    Process the user's cloud request.

    Args:
        user_request (str): User's cloud request.
        metrics_file (str): Path to the metrics file.

    Returns:
        dict: Complete processing result.
    """

    # Parse the user request
    parsed_request = parse_request(user_request)

    # Validate the request
    validation_result = validate_request(user_request)

    # Load AWS metrics
    metrics = load_metrics(metrics_file)

    # Filter EC2 instances
    filtered_metrics = filter_ec2_instances(metrics, parsed_request)

        # Combine all results
    return {
        "parsed_request": parsed_request,
        "validation": validation_result,
        "filtered_metrics": filtered_metrics
}