"""Email notification module for quota alerts.

Sends HTML-formatted emails when account quotas are low or exhausted.
Uses Python's built-in smtplib and email.mime (no external dependencies).

Environment variables:
    SMTP_EMAIL: Gmail address (sender)
    SMTP_PASSWORD: Gmail App Password (NOT regular password)
    NOTIFY_EMAIL: Where to send notifications (can be same as SMTP_EMAIL)
"""

import os
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def _get_config():
    """Read SMTP configuration from environment variables."""
    return {
        "email": os.environ.get("SMTP_EMAIL", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "notify": os.environ.get("NOTIFY_EMAIL", ""),
    }


def _is_configured():
    """Check if SMTP is properly configured."""
    config = _get_config()
    return bool(config["email"] and config["password"] and config["notify"])


def _send_email(subject, html_body):
    """Send an HTML email via Gmail SMTP.

    Args:
        subject: Email subject line.
        html_body: HTML content for the email body.

    Returns:
        True if sent successfully, False otherwise.
    """
    config = _get_config()

    if not _is_configured():
        logger.warning(
            "SMTP not configured. Set SMTP_EMAIL, SMTP_PASSWORD, and NOTIFY_EMAIL "
            "environment variables to enable email notifications."
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config["email"]
    msg["To"] = config["notify"]
    msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config["email"], config["password"])
            server.sendmail(config["email"], config["notify"], msg.as_string())
        logger.info("Email sent: %s", subject)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP authentication failed. Verify your Gmail App Password "
            "(regular passwords are not accepted)."
        )
        return False
    except smtplib.SMTPException as e:
        logger.error("SMTP error sending email: %s", e)
        return False
    except Exception as e:
        logger.error("Unexpected error sending email: %s", e)
        return False


def _html_wrapper(content):
    """Wrap HTML content in a styled email template."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f4f4f7; margin: 0; padding: 20px; }}
    .container {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
    .header {{ background: #1a1a2e; color: #ffffff; padding: 20px 24px; }}
    .header h2 {{ margin: 0; font-size: 18px; font-weight: 600; }}
    .body {{ padding: 24px; color: #333333; line-height: 1.6; }}
    .account {{ background: #f8f9fa; border-left: 4px solid #4a90d9; padding: 12px 16px; margin: 12px 0; border-radius: 0 4px 4px 0; }}
    .account.warning {{ border-left-color: #f0ad4e; }}
    .account.critical {{ border-left-color: #d9534f; }}
    .account.ok {{ border-left-color: #5cb85c; }}
    .label {{ font-size: 12px; color: #888888; text-transform: uppercase; letter-spacing: 0.5px; }}
    .value {{ font-size: 22px; font-weight: 700; margin: 4px 0; }}
    .value.warning {{ color: #f0ad4e; }}
    .value.critical {{ color: #d9534f; }}
    .value.ok {{ color: #5cb85c; }}
    .meta {{ font-size: 12px; color: #999999; margin-top: 16px; padding-top: 16px; border-top: 1px solid #eee; }}
    .footer {{ padding: 16px 24px; background: #f8f9fa; font-size: 11px; color: #999999; text-align: center; }}
</style>
</head>
<body>
<div class="container">
    <div class="header"><h2>{content}</h2></div>
    <div class="body">
        {content}
    </div>
    <div class="footer">Kids Video Agent &mdash; Quota Monitor &bull; {now}</div>
</div>
</body>
</html>"""


def _account_card(email, platform, remaining, limit):
    """Generate an HTML card for a single account."""
    used = limit - remaining
    pct = (used / limit * 100) if limit else 0

    if pct >= 90:
        severity = "critical"
    elif pct >= 70:
        severity = "warning"
    else:
        severity = "ok"

    return f"""<div class="account {severity}">
    <div class="label">Account</div>
    <div style="font-weight:600; font-size:14px;">{email}</div>
    <div class="label" style="margin-top:8px;">Platform</div>
    <div>{platform}</div>
    <div class="label" style="margin-top:8px;">Quota</div>
    <div class="value {severity}">{remaining} / {limit} remaining</div>
    <div style="font-size:13px; color:#666;">{pct:.0f}% used ({used} of {limit} consumed)</div>
</div>"""


def send_quota_low_notification(account_email, platform, remaining, limit):
    """Send an alert when an account's quota is running low.

    Args:
        account_email: The email of the account with low quota.
        platform: Platform name (e.g., "Google Vids", "Google Flow").
        remaining: Number of remaining quota units.
        limit: Total quota limit.

    Returns:
        True if email sent successfully, False otherwise.
    """
    subject = f"\u26a0\ufe0f Quota Low: {account_email} - {platform} ({remaining}/{limit} remaining)"
    body = f"""
    <h2>\u26a0\ufe0f Quota Running Low</h2>
    <p>The following account is approaching its quota limit:</p>
    {_account_card(account_email, platform, remaining, limit)}
    <p style="margin-top:16px; padding:12px; background:#fff3cd; border-radius:4px; font-size:13px;">
        <strong>Recommendation:</strong> Consider switching to another account to avoid service interruption.
    </p>
    """
    return _send_email(subject, _html_wrapper(body))


def send_quota_exhausted_notification(account_email, platform):
    """Send an alert when an account's quota is fully depleted.

    Args:
        account_email: The email of the exhausted account.
        platform: Platform name (e.g., "Google Vids", "Google Flow").

    Returns:
        True if email sent successfully, False otherwise.
    """
    subject = f"\ud83d\udeab Quota Exhausted: {account_email} - {platform}"
    body = f"""
    <h2>\ud83d\udeab Quota Exhausted</h2>
    <p>The following account has <strong>no remaining quota</strong>:</p>
    {_account_card(account_email, platform, 0, 1)}
    <p style="margin-top:16px; padding:12px; background:#f8d7da; border-radius:4px; font-size:13px;">
        <strong>Action Required:</strong> Switch to another account immediately. This account cannot be used until quota resets.
    </p>
    """
    return _send_email(subject, _html_wrapper(body))


def send_monthly_reset_notification(accounts):
    """Send a summary when monthly quotas reset.

    Args:
        accounts: List of dicts with keys: email, platform, limit.

    Returns:
        True if email sent successfully, False otherwise.
    """
    now = datetime.now(timezone.utc)
    subject = f"\ud83d\udd04 Monthly Quota Reset - {now.strftime('%B %Y')}"

    cards = ""
    for acct in accounts:
        cards += _account_card(acct["email"], acct["platform"], acct["limit"], acct["limit"])

    body = f"""
    <h2>\ud83d\udd04 Monthly Quota Reset</h2>
    <p>All account quotas have been reset for <strong>{now.strftime("%B %Y")}</strong>.</p>
    <p><strong>{len(accounts)}</strong> account(s) available:</p>
    {cards}
    <p style="margin-top:16px; font-size:13px; color:#666;">
        Quotas reset on the 1st of each month. Plan usage accordingly.
    </p>
    """
    return _send_email(subject, _html_wrapper(body))


def send_status_report(accounts_summary):
    """Send a full status report of all managed accounts.

    Args:
        accounts_summary: List of dicts with keys:
            email, platform, remaining, limit.

    Returns:
        True if email sent successfully, False otherwise.
    """
    now = datetime.now(timezone.utc)
    subject = f"\ud83d\udcca Account Status Report - {now.strftime('%Y-%m-%d %H:%M UTC')}"

    total_remaining = sum(a["remaining"] for a in accounts_summary)
    total_limit = sum(a["limit"] for a in accounts_summary)
    overall_pct = (total_limit - total_remaining) / total_limit * 100 if total_limit else 0

    cards = ""
    for acct in accounts_summary:
        cards += _account_card(acct["email"], acct["platform"], acct["remaining"], acct["limit"])

    body = f"""
    <h2>\ud83d\udcca Account Status Report</h2>
    <div class="account {'ok' if overall_pct < 70 else 'warning' if overall_pct < 90 else 'critical'}">
        <div class="label">Overall Usage</div>
        <div class="value {'ok' if overall_pct < 70 else 'warning' if overall_pct < 90 else 'critical'}">{total_remaining} / {total_limit} remaining</div>
        <div style="font-size:13px; color:#666;">{overall_pct:.1f}% of total quota used across {len(accounts_summary)} account(s)</div>
    </div>
    <h3 style="margin-top:20px; font-size:14px; color:#555;">Individual Accounts</h3>
    {cards}
    """
    return _send_email(subject, _html_wrapper(body))


def test_connection():
    """Test SMTP connection and authentication.

    Returns:
        True if connection and login succeed, False otherwise.
    """
    config = _get_config()

    if not _is_configured():
        logger.warning(
            "SMTP not configured. Set SMTP_EMAIL, SMTP_PASSWORD, and NOTIFY_EMAIL "
            "environment variables."
        )
        return False

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config["email"], config["password"])
        logger.info("SMTP connection test successful for %s", config["email"])
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP authentication failed. Ensure you are using a Gmail App Password."
        )
        return False
    except smtplib.SMTPException as e:
        logger.error("SMTP connection test failed: %s", e)
        return False
    except Exception as e:
        logger.error("Unexpected error during SMTP test: %s", e)
        return False
