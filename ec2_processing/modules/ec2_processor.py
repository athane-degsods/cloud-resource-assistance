import pandas as pd

def filter_ec2_instances(metrics, parsed_request):
    """
    Filter EC2 instances based on the user's request.

    Args:
        metrics (pandas.DataFrame): AWS metrics.
        parsed_request (dict): Parsed user request.

    Returns:
        pandas.DataFrame: Filtered EC2 instances.
    """

        # Get the requested condition
    condition = parsed_request["condition"]

    # Filter idle EC2 instances
    if condition == "idle":
        filtered_data = metrics[metrics["CPUUtilization"] <= 5]

    else:
        filtered_data = metrics

    return filtered_data