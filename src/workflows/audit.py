"""Prospect audit workflow."""


def build_audit_input(account: dict) -> dict:
    return {"account": account, "workflow": "prospect_audit"}