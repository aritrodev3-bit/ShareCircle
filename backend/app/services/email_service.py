import resend
from app.config import get_settings

settings = get_settings()
resend.api_key = settings.resend_api_key

def send_email(to: str, subject: str, html_body: str) -> None:
    resend.Emails.send({
        "from": settings.resend_from_email,
        "to": to,
        "subject": subject,
        "html": html_body,
    })
