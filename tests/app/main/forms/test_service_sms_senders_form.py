import pytest

from app.main.forms import ServiceSmsSenderForm


@pytest.mark.parametrize(
    "sms_sender,error_expected,error_message",
    [
        ("", True, "Cannot be empty"),
        ("22", True, "Text message sender must be at least 3 characters long"),
        ("333", False, None),
        ("elevenchars", False, None),  # 11 chars
        ("twelvecharas", True, "Text message sender cannot be longer than 11 characters"),  # 12 chars
        ("###", True, "Use letters and numbers only"),
        ("00111222333", True, "Cannot start with 00"),
        ("UK_GOV", False, None),  # Underscores are allowed
        ("UK.GOV", False, None),  # Full stops are allowed
        ("'UC'", False, None),  # Straight single quotes are allowed
    ],
)
def test_sms_sender_form_validation(client_request, mock_get_user_by_email, sms_sender, error_expected, error_message):
    form = ServiceSmsSenderForm()
    form.sms_sender.data = sms_sender

    form.validate()

    if error_expected:
        assert form.errors
        assert error_message == form.errors["sms_sender"][0]
    else:
        assert not form.errors
