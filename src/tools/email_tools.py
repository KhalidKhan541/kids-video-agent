"""Email notification tool - sends video completion alerts via Google SMTP."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional


def send_video_notification(
    topic: str,
    video_path: str | Path,
    title: str = "",
    description: str = "",
    tags: list[str] | None = None,
    pipeline_report: dict | None = None,
) -> dict:
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_email = os.getenv("SMTP_EMAIL", "")
    smtp_password = os.getenv("SMTP_APP_PASSWORD", "").replace(" ", "")
    notify_email = os.getenv("NOTIFY_EMAIL", smtp_email)

    if not smtp_email or not smtp_password:
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
    if video_file.exists():
        with open(video_file, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={video_file.name}")
            msg.attach(part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, notify_email, msg.as_string())
        return {"success": True, "sent_to": notify_email}
    except Exception as e:
        return {"success": False, "error": str(e)}
