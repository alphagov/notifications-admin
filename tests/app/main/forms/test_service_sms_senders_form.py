import logging

import pytest
from flask import g
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket, NotifyTicketType

from app.main.forms import ServiceSmsSenderForm
from app.models.service import Service


@pytest.mark.parametrize(
    "sms_sender,error_expected,error_message,sends_zendesk_ticket,protected_sender_id_return",
    [
        ("", True, "Enter a text message sender ID", False, False),
        ("22", True, "Text message sender ID must be at least 3 characters long", False, False),
        ("333", True, "A numeric sender id should be a valid mobile number or short code", False, False),
        ("70000", False, None, False, False),
        ("07000000000", False, None, False, False),
        (
            "Info",
            True,
            "Text message sender ID cannot be Alert, Info or Verify as those are prohibited due to usage by spam",
            False,
            False,
        ),
        ("Inform Uk", False, None, False, False),
        ("elevenchars", False, None, False, False),  # 11 chars
        ("twelvecharas", True, "Text message sender ID cannot be longer than 11 characters", False, False),  # 12 chars
        (
            "###",
            True,
            "Text message sender ID can only include letters, numbers, spaces, and the following characters: & . - _",
            False,
            False,
        ),
        ("00111222333", True, "Text message sender ID cannot start with 00", False, False),
        ("UK_GOV", False, None, False, False),  # Underscores are allowed
        ("UK-GOV", False, None, False, False),  # Simple dashes are allowed
        ("UK.GOV", False, None, False, False),  # Full stops are allowed
        ("UK&GOV", False, None, False, False),  # Ampersands are allowed
        (
            "Evri",
            True,
            "Text message sender ID cannot be ‘Evri’ - this is to protect recipients from phishing scams",
            True,
            True,
        ),  # Evri is a user id that will be set in the
        ("NHSNoReply", False, None, False, False),  # NHSNoReply is allowed
        (
            "NHSno Reply",
            True,
            "Text message sender ID must match other NHS services - change it to ‘NHSNoReply’",
            False,
            False,
        ),  # NHS-No Reply and variants are not allowed
        pytest.param(
            "'UC'", False, None, False, False, marks=pytest.mark.xfail
        ),  # Apostrophes can cause SMS delivery issues
    ],
)
def test_sms_sender_form_validation(
    notify_admin,
    sms_sender,
    error_expected,
    error_message,
    sends_zendesk_ticket,
    protected_sender_id_return,
    mocker,
):
    mocker.patch(
        "app.protected_sender_id_api_client.get_check_sender_id",
        return_value=protected_sender_id_return,
    )

    form = ServiceSmsSenderForm()
    form.sms_sender.data = sms_sender
    mock_create_phishing_zendesk_ticket = mocker.patch(
        "app.main.validators.create_phishing_senderid_zendesk_ticket",
        autospec=True,
    )
    form.validate()
    if error_expected:
        assert form.errors
        assert error_message == form.errors["sms_sender"][0]
    else:
        assert not form.errors

    if sends_zendesk_ticket:
        mock_create_phishing_zendesk_ticket.assert_called_once_with(senderID=sms_sender)


def test_sms_validation_logs_and_creates_ticket_for_phishing_sender(client_request, service_one, caplog, mocker):
    mocker.patch("app.protected_sender_id_api_client.get_check_sender_id", return_value=True)
    form = ServiceSmsSenderForm(sms_sender="Evri")
    g.current_service = Service(service_one)

    mock_create_ticket = mocker.spy(NotifySupportTicket, "__init__")
    mock_send_zendesk_ticket = mocker.patch("app.main.validators.zendesk_client.send_ticket_to_zendesk", autospec=True)

    with caplog.at_level(logging.WARNING):
        form.validate()

    assert "User tried to set sender id to potentially malicious one: Evri" in caplog.messages

    mock_create_ticket.assert_called_once_with(
        mocker.ANY,
        subject="Possible Phishing sender ID - service one",
        message=mocker.ANY,
        ticket_type="task",
        notify_ticket_type=NotifyTicketType.TECHNICAL,
        notify_task_type="notify_task_blocked_sender",
    )
    mock_send_zendesk_ticket.assert_called_once()


def test_sms_validation_does_not_log_or_create_ticket_for_safe_sender(notify_admin, caplog, mocker):
    mocker.patch("app.protected_sender_id_api_client.get_check_sender_id", return_value=False)
    form = ServiceSmsSenderForm(sms_sender="UK&GOV")

    mock_create_phishing_zendesk_ticket = mocker.patch(
        "app.main.validators.create_phishing_senderid_zendesk_ticket",
        autospec=True,
    )
    with caplog.at_level(logging.WARNING):
        form.validate()

    assert len(caplog.messages) == 0
    assert not mock_create_phishing_zendesk_ticket.called
