import pytest

from tests.conftest import normalize_spaces


def test_guidance_pricing_letters(client_request, mock_get_letter_rates):
    page = client_request.get(".guidance_pricing_letters")

    assert normalize_spaces(page.select_one(".content-metadata").text) == "Last updated 2 January 2024"

    first_row = page.select_one("main table tbody tr")
    assert "1 sheet" in first_row.text

    assert "54p + VAT" in first_row.text
    assert "82p + VAT" in first_row.text
    assert "£1.44 + VAT" in first_row.text


@pytest.mark.parametrize(
    "valid_from, expected_last_updated",
    (
        ("2040-04-01T12:00:00", "Last updated 1 April 2040"),
        ("2023-04-01T12:00:00", "Last updated 28 March 2024"),
    ),
)
@pytest.mark.parametrize(
    "rate, expected_paragraph",
    (
        (
            0.0197,
            (
                "When a service has used its annual allowance, it costs 1.97 pence (plus VAT)"
                " for each text message you send."
            ),
        ),
        (
            0.0227,
            (
                "When a service has used its annual allowance, it costs 2.27 pence (plus VAT)"
                " for each text message you send."
            ),
        ),
    ),
)
def test_guidance_pricing_sms(
    mocker,
    client_request,
    rate,
    expected_paragraph,
    valid_from,
    expected_last_updated,
):
    mocker.patch(
        "app.models.sms_rate.sms_rate_api_client.get_sms_rate",
        return_value={
            "rate": rate,
            "valid_from": valid_from,
        },
    )

    page = client_request.get(".guidance_pricing_text_messages")

    assert normalize_spaces(page.select_one(".content-metadata").text) == expected_last_updated
    assert normalize_spaces(page.select("main .govuk-body")[1].text) == expected_paragraph
