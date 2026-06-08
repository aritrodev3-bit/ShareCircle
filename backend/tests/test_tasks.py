from unittest.mock import patch
import pytest
from app.worker.tasks import (
    send_request_notification,
    send_approval_notification,
    send_rejection_notification,
    send_pickup_confirmation,
)


@patch("app.services.email_service.resend.Emails.send")
def test_send_request_notification(mock_send):
    send_request_notification(
        donor_email="donor@example.com",
        donor_name="Donor Name",
        requester_name="Requester Name",
        item_title="Books",
        message="I need books",
    )
    mock_send.assert_called_once()
    args = mock_send.call_args[0][0]
    assert args["to"] == "donor@example.com"
    assert "Books" in args["subject"]
    assert "Donor Name" in args["html"]
    assert "Requester Name" in args["html"]
    assert "I need books" in args["html"]


@patch("app.services.email_service.resend.Emails.send")
def test_send_approval_notification(mock_send):
    send_approval_notification(
        requester_email="req@example.com",
        requester_name="Req Name",
        item_title="Furniture",
        donor_phone="1234567890",
        pickup_instructions="Call me",
    )
    mock_send.assert_called_once()
    args = mock_send.call_args[0][0]
    assert args["to"] == "req@example.com"
    assert "Furniture" in args["subject"]
    assert "Req Name" in args["html"]
    assert "1234567890" in args["html"]
    assert "Call me" in args["html"]


@patch("app.services.email_service.resend.Emails.send")
def test_send_rejection_notification(mock_send):
    send_rejection_notification(
        requester_email="req@example.com",
        requester_name="Req Name",
        item_title="Toys",
    )
    mock_send.assert_called_once()
    args = mock_send.call_args[0][0]
    assert args["to"] == "req@example.com"
    assert "Toys" in args["subject"]
    assert "Req Name" in args["html"]


@patch("app.services.email_service.resend.Emails.send")
def test_send_pickup_confirmation(mock_send):
    send_pickup_confirmation(
        donor_email="donor@example.com",
        donor_name="Donor Name",
        requester_email="req@example.com",
        requester_name="Req Name",
        item_title="Kitchenware",
    )
    assert mock_send.call_count == 2
    
    # First call to donor
    call1_args = mock_send.call_args_list[0][0][0]
    assert call1_args["to"] == "donor@example.com"
    assert "Kitchenware" in call1_args["subject"]
    assert "Donor Name" in call1_args["html"]
    
    # Second call to requester
    call2_args = mock_send.call_args_list[1][0][0]
    assert call2_args["to"] == "req@example.com"
    assert "Kitchenware" in call2_args["subject"]
    assert "Req Name" in call2_args["html"]
