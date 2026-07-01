"""Email notification tool - sends video completion alerts via Google SMTP.

Includes retry logic and proper error handling.
"""

import os
import smtplib
import logging
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def _send_email_with_retry(
    smtp_server: str,
    smtp_port: int,
    smtp_email: str,
    smtp_password: str,
    notify_email: str,
    msg: MIMEMultipart,
    max_retries: int = MAX_RETRIES,
) -> dict:
    """Send email with retry logic for transient failures."""
    last_error = None
    
    for attempt in range(max_retries):
        try:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                server.starttls()
                server.login(smtp_email, smtp_password)
                server.sendmail(smtp_email, notify_email, msg.as_string())
            logger.info("Email sent successfully on attempt %d", attempt + 1)
            return {"success": True, "sent_to": notify_email}
        except smtplib.SMTPAuthenticationError as e:
            # Authentication errors should not be retried
            logger.error("SMTP authentication failed: %s", e)
            return {"success": False, "error": f"Authentication failed: {e}"}
        except smtplib.SMTPException as e:
            last_error = e
            logger.warning("SMTP error on attempt %d: %s", attempt + 1, e)
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
        except Exception as e:
            last_error = e
            logger.warning("Unexpected error on attempt %d: %s", attempt + 1, e)
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
    
    return {"success": False, "error": f"Failed after {max_retries} attempts: {last_error}"}


def send_video_notification(
    topic: str,
    video_path: str | Path,
    title: str = "",
    description: str = "",
    tags: list[str] | None = None,
    pipeline_report: dict | None = None,
) -> dict:
    """Send video completion notification email with video attached."""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_email = os.getenv("SMTP_EMAIL", "")
    smtp_password = os.getenv("SMTP_APP_PASSWORD", os.getenv("SMTP_PASSWORD", "")).replace(" ", "")
    notify_email = os.getenv("NOTIFY_EMAIL", smtp_email)

    if not smtp_email or not smtp_password:
        logger.error("SMTP credentials not configured. Set SMTP_EMAIL and SMTP_APP_PASSWORD.")
        return {"success": False, "error": "SMTP credentials not configured"}

    msg = MIMEMultipart()
    msg["From"] = smtp_email
    msg["To"] = notify_email
    msg["Subject"] = f"Kids Video Ready: {title or topic}"

    tags_str = ", ".join(tags[:10]) if tags else "N/A"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2ecc71;">Video Production Complete!</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <tr><td style="padding: 8px; font-weight: bold;">Topic:</td><td style="padding: 8px;">{topic}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Title:</td><td style="padding: 8px;">{title}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Video:</td><td style="padding: 8px;">{video_path}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Tags:</td><td style="padding: 8px;">{tags_str}</td></tr>
        </table>
        <h3>Description:</h3>
        <p style="color: #555;">{description[:500]}</p>
    """

    if pipeline_report:
        agents = pipeline_report.get("agents", {})
        html += "<h3>Pipeline Status:</h3><ul>"
        for agent_name, agent_data in agents.items():
            status = "OK" if not agent_data.get("error") else f"Error: {agent_data['error']}"
            html += f"<li><b>{agent_name}:</b> {status}</li>"
        html += "</ul>"

    html += """
        <hr style="margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">Kids Video Agent - Automated Pipeline</p>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))

    video_file = Path(video_path)
    if video_path and video_file.exists():
        try:
            with open(video_file, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={video_file.name}")
                msg.attach(part)
            logger.info("Attached video file: %s", video_file.name)
        except Exception as e:
            logger.warning("Failed to attach video file: %s", e)
    else:
        logger.warning("Video file not found or path empty: %s", video_path)

    return _send_email_with_retry(smtp_server, smtp_port, smtp_email, smtp_password, notify_email, msg)


def test_email_connection() -> dict:
    """Test SMTP connection and authentication."""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_email = os.getenv("SMTP_EMAIL", "")
    smtp_password = os.getenv("SMTP_APP_PASSWORD", os.getenv("SMTP_PASSWORD", "")).replace(" ", "")

    if not smtp_email or not smtp_password:
        return {"success": False, "error": "SMTP credentials not configured"}

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
        logger.info("SMTP connection test successful for %s", smtp_email)
        return {"success": True, "message": "SMTP connection successful"}
    except smtplib.SMTPAuthenticationError as e:
        logger.error("SMTP authentication failed: %s", e)
        return {"success": False, "error": f"Authentication failed: {e}"}
    except Exception as e:
        logger.error("SMTP connection test failed: %s", e)
        return {"success": False, "error": str(e)}
