from modules.request_processor import process_request

# User request
user_request = "Show idle EC2 instances"

# Path to metrics file
metrics_file = "data/metrics.csv"

# Process the request
result = process_request(user_request, metrics_file)

# Display parsed request
print("Parsed Request:")
print(result["parsed_request"])

# Display validation result
print("\nValidation:")
print(result["validation"])

# Display filtered EC2 instances
print("\nFiltered EC2 Instances:")
print(result["filtered_metrics"])