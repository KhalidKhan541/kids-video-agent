"""Interactive setup for Google Vids accounts.

Usage:
    python setup_accounts.py              # Interactive prompts
    python setup_accounts.py --batch      # Non-interactive, read from stdin
"""

from __future__ import annotations

import json
import os
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Resolve project root and imports
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent
_SRC_DIR = _PROJECT_ROOT / "src"

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from tools.account_tracker import (  # noqa: E402
    add_account,
    get_all_accounts,
    load_quotas,
    save_quotas,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_ACCOUNTS_FILE = Path("output/account_quotas.json")
_ENV_FILE = _PROJECT_ROOT / ".env"


# ---------------------------------------------------------------------------
# SMTP helpers
# ---------------------------------------------------------------------------
def _load_env_value(key: str) -> str:
    """Read a single value from .env without pulling in python-dotenv."""
    if not _ENV_FILE.exists():
        return ""
    with open(_ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip().strip("'\"")
    return ""


def _get_smtp_config() -> dict[str, str]:
    return {
        "host": os.getenv("SMTP_HOST", _load_env_value("SMTP_HOST") or "smtp.gmail.com"),
        "port": os.getenv("SMTP_PORT", _load_env_value("SMTP_PORT") or "587"),
        "email": os.getenv("SMTP_EMAIL", _load_env_value("SMTP_EMAIL")),
        "password": os.getenv("SMTP_PASSWORD", _load_env_value("SMTP_PASSWORD")),
    }


def test_email_notification() -> bool:
    """Send a test email if SMTP is configured. Returns True on success."""
    cfg = _get_smtp_config()
    if not cfg["email"] or not cfg["password"]:
        print("  SMTP not configured — skipping email test.")
        print("  Set SMTP_EMAIL and SMTP_PASSWORD in .env to enable.")
        return False

    try:
        msg = MIMEText(
            "Your kids-video-agent email alerts are working!\n\n"
            "You will receive quota warnings and pipeline status updates here."
        )
        msg["Subject"] = "kids-video-agent — Email test"
        msg["From"] = cfg["email"]
        msg["To"] = cfg["email"]

        port = int(cfg["port"])
        with smtplib.SMTP(cfg["host"], port, timeout=15) as server:
            server.ehlo()
            if port != 25:
                server.starttls()
                server.ehlo()
            server.login(cfg["email"], cfg["password"])
            server.sendmail(cfg["email"], [cfg["email"]], msg.as_string())

        print(f"  Test email sent to {cfg['email']}")
        return True
    except Exception as exc:
        print(f"  Email test failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Batch helper (importable)
# ---------------------------------------------------------------------------
def setup_accounts(emails: list[str]) -> dict[str, Any]:
    """Batch-add Google accounts and return the updated tracker data.

    Parameters
    ----------
    emails : list[str]
        List of Gmail addresses to register.

    Returns
    -------
    dict
        The full account tracker data after saving.
    """
    added: list[str] = []
    skipped: list[str] = []

    for email in emails:
        email = email.strip()
        if not email:
            continue
        if add_account(email):
            added.append(email)
        else:
            skipped.append(email)

    data = load_quotas()

    if added:
        print(f"Added {len(added)} account(s):")
        for e in added:
            print(f"  + {e}")
    if skipped:
        print(f"Skipped {len(skipped)} already-tracked account(s):")
        for e in skipped:
            print(f"  ~ {e}")

    return data


# ---------------------------------------------------------------------------
# Interactive prompt
# ---------------------------------------------------------------------------
def interactive_setup() -> None:
    print("=== Google Vids Account Setup ===\n")
    print("Enter your Google account emails (one per line).")
    print("Type 'done' when finished.\n")

    emails: list[str] = []
    while True:
        idx = len(emails) + 1
        try:
            raw = input(f"Account {idx}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if raw.lower() in ("done", "quit", "exit", ""):
            break
        emails.append(raw)

    if not emails:
        print("\nNo accounts entered. Nothing to save.")
        return

    print(f"\nAdding {len(emails)} account(s)...\n")
    data = setup_accounts(emails)

    # Show summary
    print("\n" + _accounts_summary(data))

    # Next steps
    print("Next steps:")
    print("  1. Log into each account at https://vids.new to activate Veo 3.1")
    print("  2. Set SMTP_EMAIL and SMTP_PASSWORD in .env for email alerts")
    print("  3. Run: python main.py accounts status")

    # Optional email test
    print("\n--- Email notification test ---")
    test_email_notification()


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------
def _accounts_summary(data: dict[str, Any]) -> str:
    accounts = data.get("accounts", [])
    lines = ["=== Accounts Summary ===", ""]
    if not accounts:
        lines.append("  (no accounts configured)")
    for i, acct in enumerate(accounts, 1):
        status = "ACTIVE" if acct.get("is_active", False) else "INACTIVE"
        lines.append(
            f"  {i}. {acct['email']}  [{status}]"
            f"  vids={acct.get('vids_used', 0)}"
            f"  flow_d={acct.get('flow_daily_used', 0)}"
            f"  flow_m={acct.get('flow_monthly_used', 0)}"
        )
    lines.append(f"\nTotal: {len(accounts)} account(s)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> None:
    if "--batch" in sys.argv:
        # Read emails from stdin, one per line
        emails = [line.strip() for line in sys.stdin if line.strip()]
        if emails:
            data = setup_accounts(emails)
            print("\n" + _accounts_summary(data))
        else:
            print("No emails provided on stdin.")
        return

    interactive_setup()


if __name__ == "__main__":
    main()
