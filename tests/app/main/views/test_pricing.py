import pytest

from tests.conftest import normalize_spaces


def test_guidance_pricing_letters(client_request, mock_get_letter_rates):
    page = client_request.get(".guidance_pricing_letters")

    first_row = page.select_one("main table tbody tr")
    assert "1 sheet" in first_row.text

    assert "54p + VAT" in first_row.text
    assert "82p + VAT" in first_row.text
    assert "£1.44 + VAT" in first_row.text


@pytest.mark.parametrize(
    "rate, expected_current_paragraph, expected_new_paragraph",
    (
        (
            1.97,
            (
                "When a service has used its annual allowance, it costs 1.97 pence (plus VAT)"
                " for each text message you send."
            ),
            "On 1 April 2024 the cost of sending a text message will go up to 2.27 pence (plus VAT).",
        ),
        (
            2.27,
            (
                "When a service has used its annual allowance, it costs 2.27 pence (plus VAT)"
                " for each text message you send."
            ),
            "From 1 April 2024 the free allowance will be:",
        ),
    ),
)
def test_guidance_pricing_sms(mocker, client_request, rate, expected_current_paragraph, expected_new_paragraph):
    mocker.patch("app.models.sms_rate.sms_rate_api_client.get_sms_rate", return_value={"rate": rate})

    page = client_request.get(".guidance_pricing_text_messages")

    assert normalize_spaces(page.select("main .govuk-body")[1].text) == expected_current_paragraph
    assert normalize_spaces(page.select_one(".govuk-inset-text .govuk-body").text) == expected_new_paragraph
