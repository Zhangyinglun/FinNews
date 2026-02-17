"""Standalone test: Gmail SMTP HTML send.

Prereqs in .env:
- SMTP_USERNAME
- SMTP_PASSWORD (Google App Password)
- EMAIL_FROM
- EMAIL_TO (comma-separated)

Run:
  python -m tests.utils.test_gmail_smtp
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.config import Config
from utils.mailer import GmailSmtpMailer


def test_gmail_smtp():
    """测试 Gmail SMTP 发送功能"""
    if not Config.SMTP_USERNAME or not Config.SMTP_PASSWORD:
        raise SystemExit("Missing SMTP_USERNAME/SMTP_PASSWORD")
    if not Config.EMAIL_FROM:
        raise SystemExit("Missing EMAIL_FROM")

    to_list = [e.strip() for e in Config.EMAIL_TO.split(",") if e.strip()]
    if not to_list:
        raise SystemExit("Missing EMAIL_TO")

    mailer = GmailSmtpMailer(
        host=Config.SMTP_HOST,
        port=Config.SMTP_PORT,
        username=Config.SMTP_USERNAME,
        password=Config.SMTP_PASSWORD,
        use_tls=Config.SMTP_USE_TLS,
    )

    html_body = """
    <html>
      <body>
        <h2>FinNews SMTP Test</h2>
        <p>This is a test HTML email from FinNews.</p>
        <p>If you received this, the SMTP configuration is working correctly.</p>
      </body>
    </html>
    """.strip()

    mailer.send_html(
        subject="FinNews SMTP Test",
        html_body=html_body,
        email_from=Config.EMAIL_FROM,
        to_list=to_list,
    )

    print(f"OK: sent to {len(to_list)} recipients")
    for email in to_list:
        print(f"  - {email}")


if __name__ == "__main__":
    test_gmail_smtp()
