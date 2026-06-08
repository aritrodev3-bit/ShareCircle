import logging
from app.worker.celery_app import celery_app
from app.services.email_service import send_email
from app.worker import email_templates

logger = logging.getLogger(__name__)


@celery_app.task(
    name="send_request_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_request_notification(
    self,
    donor_email: str,
    donor_name: str,
    requester_name: str,
    item_title: str,
    message: str = "",
) -> None:
    """Notify donor that a new request was received for their item."""
    try:
        subject = email_templates.REQUEST_RECEIVED_SUBJECT.format(item_title=item_title)
        html_body = email_templates.REQUEST_RECEIVED_TEMPLATE.format(
            donor_name=donor_name,
            item_title=item_title,
            requester_name=requester_name,
            message=message,
        )
        send_email(to=donor_email, subject=subject, html_body=html_body)
    except Exception as exc:
        logger.error(f"Error sending request notification to {donor_email}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    name="send_approval_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_approval_notification(
    self,
    requester_email: str,
    requester_name: str,
    item_title: str,
    donor_phone: str,
    pickup_instructions: str,
) -> None:
    """Notify recipient their request was approved."""
    try:
        subject = email_templates.REQUEST_APPROVED_SUBJECT.format(item_title=item_title)
        html_body = email_templates.REQUEST_APPROVED_TEMPLATE.format(
            requester_name=requester_name,
            item_title=item_title,
            donor_phone=donor_phone,
            pickup_instructions=pickup_instructions,
        )
        send_email(to=requester_email, subject=subject, html_body=html_body)
    except Exception as exc:
        logger.error(f"Error sending approval notification to {requester_email}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    name="send_rejection_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_rejection_notification(
    self,
    requester_email: str,
    requester_name: str,
    item_title: str,
) -> None:
    """Notify recipient their request was rejected."""
    try:
        subject = email_templates.REQUEST_REJECTED_SUBJECT.format(item_title=item_title)
        html_body = email_templates.REQUEST_REJECTED_TEMPLATE.format(
            requester_name=requester_name,
            item_title=item_title,
        )
        send_email(to=requester_email, subject=subject, html_body=html_body)
    except Exception as exc:
        logger.error(f"Error sending rejection notification to {requester_email}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    name="send_pickup_confirmation",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_pickup_confirmation(
    self,
    donor_email: str,
    donor_name: str,
    requester_email: str,
    requester_name: str,
    item_title: str,
) -> None:
    """Send pickup confirmation email to both donor and recipient."""
    try:
        # Send to donor
        donor_subject = email_templates.PICKUP_CONFIRMED_SUBJECT.format(item_title=item_title)
        donor_html = email_templates.PICKUP_CONFIRMED_TEMPLATE.format(
            user_name=donor_name,
            item_title=item_title,
        )
        send_email(to=donor_email, subject=donor_subject, html_body=donor_html)

        # Send to requester
        requester_subject = email_templates.PICKUP_CONFIRMED_SUBJECT.format(item_title=item_title)
        requester_html = email_templates.PICKUP_CONFIRMED_TEMPLATE.format(
            user_name=requester_name,
            item_title=item_title,
        )
        send_email(to=requester_email, subject=requester_subject, html_body=requester_html)
    except Exception as exc:
        logger.error(f"Error sending pickup confirmation for {item_title}: {exc}")
        raise self.retry(exc=exc)
