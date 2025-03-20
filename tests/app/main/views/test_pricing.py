import pytest

from tests.conftest import normalize_spaces


def test_guidance_pricing_letters(client_request, mock_get_letter_rates):
    page = client_request.get(".guidance_pricing_letters")

    assert normalize_spaces(page.select_one(".content-metadata").text) == "Last updated 1 July 2024"

    pricing_rows = page.select("main table tbody tr")

    first_row = pricing_rows[0]
    assert "1 sheet" in first_row.text

    assert "61p + VAT" in first_row.text
    assert "97p + VAT" in first_row.text
    assert "£1.44 + VAT" in first_row.text

    last_row = pricing_rows[-1]
    assert "5 sheets" in last_row.text

    assert "79p + VAT" in last_row.text
    assert "£1.15 + VAT" in last_row.text
    assert "£1.63 + VAT" in last_row.text


@pytest.mark.parametrize(
    "valid_from, expected_last_updated",
    (
        ("2040-04-01T12:00:00", "Last updated 1 April 2040"),
        ("2023-04-01T12:00:00", "Last updated 21 March 2025"),
    ),
)
@pytest.mark.parametrize(
    "rate, expected_first_paragraph, expected_second_paragraph",
    (
        (
            0.0227,
            "On 1 April 2025 the cost of sending a text message will go up to 2.33 pence (plus VAT).",
            "Each unique service you add has an annual allowance of free text messages.",
        ),
        (
            0.0233,
            "Each unique service you add has an annual allowance of free text messages.",
            (
                "When a service has used its annual allowance, it costs 2.33 pence (plus VAT) "
                "for each text message you send."
            ),
        ),
    ),
)
def test_guidance_pricing_sms(
    client_request,
    rate,
    expected_first_paragraph,
    expected_second_paragraph,
    valid_from,
    expected_last_updated,
    mocker,
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
    assert normalize_spaces(page.select("main .govuk-body")[0].text) == expected_first_paragraph
    assert normalize_spaces(page.select("main .govuk-body")[1].text) == expected_second_paragraph
