"""EC2 data processor — for now, pass through text from the AWS ingestor."""

from modules.aws_ingestor import ingest


def process_ec2(request_hint: str = "") -> str:
    """
    params: request_hint: str (unused for now; filtering comes later)
    return: ec2 text document from the CloudWatch sample
    """
    return ingest()
