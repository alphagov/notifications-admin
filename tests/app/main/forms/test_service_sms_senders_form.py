import logging

import pytest

from app.main.forms import ServiceSmsSenderForm


@pytest.mark.parametrize(
    "sms_sender,error_expected,error_message,sends_zendesk_ticket",
    [
        ("", True, "Enter a text message sender ID", False),
        ("22", True, "Text message sender ID must be at least 3 characters long", False),
        ("333", True, "A numeric sender id should be a valid mobile number or short code", False),
        ("70000", False, None, False),
        ("07000000000", False, None, False),
        (
            "Info",
            True,
            "Text message sender ID cannot be Alert, Info or Verify as those are prohibited due to usage by spam",
            False,
        ),
        ("Inform Uk", False, None, False),
        ("elevenchars", False, None, False),  # 11 chars
        ("twelvecharas", True, "Text message sender ID cannot be longer than 11 characters", False),  # 12 chars
        (
            "###",
            True,
            "Text message sender ID can only include letters, numbers, spaces, and the following characters: & . - _",
            False,
        ),
        ("00111222333", True, "Text message sender ID cannot start with 00", False),
        ("UK_GOV", False, None, False),  # Underscores are allowed
        ("UK-GOV", False, None, False),  # Simple dashes are allowed
        ("UK.GOV", False, None, False),  # Full stops are allowed
        ("UK&GOV", False, None, False),  # Ampersands are allowed
        (
            "Evri",
            True,
            "Text message sender ID cannot be ‘Evri’ - this is to protect recipients from phishing scams",
            True,
        ),
        pytest.param("'UC'", False, None, False, marks=pytest.mark.xfail),  # Apostrophes can cause SMS delivery issues
    ],
)
def test_sms_sender_form_validation(
    client_request, mock_get_user_by_email, sms_sender, error_expected, error_message, sends_zendesk_ticket, mocker
):
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
        mock_create_phishing_zendesk_ticket.assert_called_once()


@pytest.mark.parametrize(
    "sms_sender,log_expected,log_message,sends_zendesk_ticket",
    [
        ("UK&GOV", False, None, False),  # No warning log on valid senderID
        (
            "Evri",
            True,
            "User tried to set sender id to potentially malicious one: Evri",
            True,
        ),
    ],
)
def test_sms_validation_logs(caplog, sms_sender, log_expected, log_message, sends_zendesk_ticket, mocker):

    form = ServiceSmsSenderForm()
    form.sms_sender.data = sms_sender
    mock_create_phishing_zendesk_ticket = mocker.patch(
        "app.main.validators.create_phishing_senderid_zendesk_ticket",
        autospec=True,
    )
    with caplog.at_level(logging.WARNING):
        form.validate()

    if log_expected:
        assert log_message in caplog.messages

    else:
        assert len(caplog.messages) == 0

    if sends_zendesk_ticket:
        mock_create_phishing_zendesk_ticket.assert_called_once_with(senderID=sms_sender)
