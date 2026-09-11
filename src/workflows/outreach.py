"""Outreach workflow."""


def build_outreach_context(account: dict) -> dict:
    return {"account": account, "workflow": "outreach"}