import pytest

from app.main.forms import ServiceSmsSenderForm


@pytest.mark.parametrize(
    "sms_sender,error_expected,error_message",
    [
        ("", True, "Enter a text message sender ID"),
        ("22", True, "Text message sender ID must be at least 3 characters long"),
        ("333", True, "A numeric sender id should be a valid mobile number or short code"),
        ("70000", False, None),
        ("07000000000", False, None),
        (
            "Info",
            True,
            "Text message sender ID cannot be Alert, Info or Verify as those are prohibited due to usage by spam",
        ),
        ("Inform Uk", False, None),
        ("elevenchars", False, None),  # 11 chars
        ("twelvecharas", True, "Text message sender ID cannot be longer than 11 characters"),  # 12 chars
        (
            "###",
            True,
            "Text message sender ID can only include letters, numbers, spaces, and the following characters: & . - _",
        ),
        ("00111222333", True, "Text message sender ID cannot start with 00"),
        ("UK_GOV", False, None),  # Underscores are allowed
        ("UK-GOV", False, None),  # Simple dashes are allowed
        ("UK.GOV", False, None),  # Full stops are allowed
        ("UK&GOV", False, None),  # Ampersands are allowed
        pytest.param("'UC'", False, None, marks=pytest.mark.xfail),  # Apostrophes can cause SMS delivery issues
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
