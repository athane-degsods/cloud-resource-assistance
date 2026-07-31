"""Prompt crafting — assemble one LLM prompt from request + runbooks + EC2."""

from modules.ec2_processor import EC2Record
from modules.filter_request import RunbookDoc


def craft_prompt(
    user_request: str,
    documents: list[RunbookDoc],
    ec2_records: list[EC2Record],
) -> str:
    """
    params:
      user_request: str
      documents: list[RunbookDoc]
      ec2_records: list[EC2Record]
    return: prompt: str
    """
    # TODO: Mrunali — assemble system/user prompt from bundled context
    return ""
