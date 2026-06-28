"""Tracks Google account quotas for video generation."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

QUOTAS_FILE = Path("output/account_quotas.json")

GOOGLE_VIDS_MONTHLY_LIMIT = 10
GOOGLE_FLOW_DAILY_LIMIT = 50
GOOGLE_FLOW_MONTHLY_LIMIT = 1500


def _default_config() -> dict[str, int]:
    return {
        "vids_limit": GOOGLE_VIDS_MONTHLY_LIMIT,
        "flow_daily_limit": GOOGLE_FLOW_DAILY_LIMIT,
        "flow_monthly_limit": GOOGLE_FLOW_MONTHLY_LIMIT,
    }


def _new_account(email: str) -> dict[str, Any]:
    today = date.today().isoformat()
    return {
        "email": email,
        "vids_used": 0,
        "flow_daily_used": 0,
        "flow_monthly_used": 0,
        "last_daily_reset": today,
        "last_monthly_reset": today,
        "is_active": True,
        "notes": "",
    }


def load_quotas() -> dict[str, Any]:
    if QUOTAS_FILE.exists():
        with open(QUOTAS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("accounts", [])
        data.setdefault("config", _default_config())
        return data
    return {"accounts": [], "config": _default_config()}


def save_quotas(data: dict[str, Any]) -> None:
    QUOTAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUOTAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _daily_reset_if_needed(account: dict[str, Any], today: str) -> None:
    if account.get("last_daily_reset", "") != today:
        account["flow_daily_used"] = 0
        account["last_daily_reset"] = today


def _monthly_reset_if_needed(account: dict[str, Any], today: str) -> None:
    current_month = today[:7]  # YYYY-MM
    last_month = account.get("last_monthly_reset", "")[:7]
    if last_month != current_month:
        account["vids_used"] = 0
        account["flow_monthly_used"] = 0
        account["last_monthly_reset"] = today


def _auto_reset(account: dict[str, Any]) -> None:
    today = date.today().isoformat()
    _daily_reset_if_needed(account, today)
    _monthly_reset_if_needed(account, today)


def _is_available(account: dict[str, Any], config: dict[str, int]) -> bool:
    if not account.get("is_active", False):
        return False
    _auto_reset(account)
    return (
        account["vids_used"] < config["vids_limit"]
        or account["flow_daily_used"] < config["flow_daily_limit"]
        or account["flow_monthly_used"] < config["flow_monthly_limit"]
    )


def get_next_account() -> dict[str, Any] | None:
    data = load_quotas()
    config = data["config"]
    for account in data["accounts"]:
        if _is_available(account, config):
            save_quotas(data)
            return account
    save_quotas(data)
    return None


def update_usage(account_email: str, platform: str, amount: int = 1) -> bool:
    """Increment usage for the given platform.

    platform: "vids" | "flow_daily" | "flow_monthly"
    Returns True on success.
    """
    data = load_quotas()
    for account in data["accounts"]:
        if account["email"] == account_email:
            _auto_reset(account)
            key = {
                "vids": "vids_used",
                "flow_daily": "flow_daily_used",
                "flow_monthly": "flow_monthly_used",
            }.get(platform)
            if key is None:
                return False
            account[key] += amount
            save_quotas(data)
            return True
    return False


def check_quota_low(account_email: str, threshold: int = 2) -> bool:
    data = load_quotas()
    config = data["config"]
    for account in data["accounts"]:
        if account["email"] == account_email:
            _auto_reset(account)
            vids_remaining = config["vids_limit"] - account["vids_used"]
            daily_remaining = config["flow_daily_limit"] - account["flow_daily_used"]
            monthly_remaining = config["flow_monthly_limit"] - account["flow_monthly_used"]
            return vids_remaining <= threshold or daily_remaining <= threshold or monthly_remaining <= threshold
    return True


def get_all_accounts() -> list[dict[str, Any]]:
    data = load_quotas()
    for account in data["accounts"]:
        _auto_reset(account)
    save_quotas(data)
    return data["accounts"]


def add_account(email: str) -> bool:
    data = load_quotas()
    if any(a["email"] == email for a in data["accounts"]):
        return False
    data["accounts"].append(_new_account(email))
    save_quotas(data)
    return True


def remove_account(email: str) -> bool:
    data = load_quotas()
    before = len(data["accounts"])
    data["accounts"] = [a for a in data["accounts"] if a["email"] != email]
    if len(data["accounts"]) < before:
        save_quotas(data)
        return True
    return False


def reset_monthly_quotas() -> None:
    today = date.today().isoformat()
    data = load_quotas()
    for account in data["accounts"]:
        account["vids_used"] = 0
        account["flow_monthly_used"] = 0
        account["last_monthly_reset"] = today
    save_quotas(data)


def get_status_summary() -> str:
    data = load_quotas()
    config = data["config"]
    lines: list[str] = []
    lines.append("=== Account Quota Status ===")
    lines.append(f"Vids limit: {config['vids_limit']}/mo | Flow daily: {config['flow_daily_limit']}/d | Flow monthly: {config['flow_monthly_limit']}/mo")
    lines.append("")
    if not data["accounts"]:
        lines.append("No accounts configured.")
        return "\n".join(lines)
    for acct in data["accounts"]:
        _auto_reset(acct)
        status = "ACTIVE" if acct["is_active"] else "INACTIVE"
        vids = acct["vids_used"]
        flow_d = acct["flow_daily_used"]
        flow_m = acct["flow_monthly_used"]
        lines.append(f"  {acct['email']} [{status}]")
        lines.append(f"    Vids:        {vids}/{config['vids_limit']}")
        lines.append(f"    Flow daily:  {flow_d}/{config['flow_daily_limit']}")
        lines.append(f"    Flow monthly:{flow_m}/{config['flow_monthly_limit']}")
        if acct.get("notes"):
            lines.append(f"    Notes: {acct['notes']}")
    lines.append("")
    lines.append(f"Total accounts: {len(data['accounts'])}")
    lines.append(f"Active: {sum(1 for a in data['accounts'] if a['is_active'])}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_status_summary())
