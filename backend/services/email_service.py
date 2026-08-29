import os
import smtplib
import logging
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = (os.getenv("SMTP_PASSWORD") or "").replace(" ", "") or None
SMTP_FROM = os.getenv("SMTP_FROM") or SMTP_USER
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Kalorie")

FRONTEND_URL = os.getenv(
    "FRONTEND_URL", "https://kalorie-app-sage.vercel.app"
).rstrip("/")

LOG_RESET_LINKS = os.getenv("LOG_RESET_LINKS", "false").lower() == "true"


def email_is_configured():
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD and SMTP_FROM)


def send_email(to_address, subject, body):
    if not email_is_configured():
        logger.warning(
            "Email not sent to %s: SMTP is not configured "
            "(set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_FROM).",
            to_address
        )
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = "%s <%s>" % (SMTP_FROM_NAME, SMTP_FROM)
    message["To"] = to_address
    message.set_content(body)

    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(message)

        logger.info("Password reset email sent to %s", to_address)
        return True

    except Exception as exc:
        logger.warning(
            "Could not send email to %s: %s: %s",
            to_address, type(exc).__name__, exc
        )
        return False


def send_password_reset_email(to_address, full_name, token, expiry_minutes):
    reset_link = "%s/reset-password?token=%s" % (FRONTEND_URL, token)

    if LOG_RESET_LINKS:
        logger.warning("[LOG_RESET_LINKS] reset link for %s: %s",
                       to_address, reset_link)

    first_name = (full_name or "").strip().split(" ")[0] or "there"

    body = (
        "Hi %s,\n\n"
        "We received a request to reset your Kalorie password.\n\n"
        "Open this link to choose a new password:\n"
        "%s\n\n"
        "This link expires in %d minutes and can only be used once.\n\n"
        "If you didn't ask for a password reset, you can ignore this "
        "email, your password will stay the same.\n\n"
        " Kalorie"
    ) % (first_name, reset_link, expiry_minutes)

    return send_email(to_address, "Reset your Kalorie password", body)
