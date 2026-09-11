"""Meeting preparation workflow."""


def build_meeting_context(account: dict) -> dict:
    return {"account": account, "workflow": "meeting_prep"}