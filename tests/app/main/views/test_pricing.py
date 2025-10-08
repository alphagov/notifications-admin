import pytest

from tests.conftest import normalize_spaces


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_guidance_pricing_letters(client_request, mock_get_letter_rates):
    page = client_request.get(".guidance_pricing_letters")

    assert normalize_spaces(page.select_one(".content-metadata").text) == "Last updated 1 July 2024"

    pricing_rows = page.select("main table tbody tr")

    first_row = pricing_rows[0]
    assert "1 sheet" in first_row.text

    assert "59p" in first_row.text
    assert "68p" in first_row.text
    assert "£1.49" in first_row.text
    assert "£1.56" in first_row.text

    last_row = pricing_rows[-1]
    assert "5 sheets" in last_row.text

    assert "78p" in last_row.text
    assert "86p" in last_row.text
    assert "£1.67" in last_row.text
    assert "£1.76" in last_row.text


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "valid_from, expected_last_updated",
    (
        ("2040-04-01T12:00:00", "Last updated 1 April 2040"),
        ("2025-04-01T12:00:00", "Last updated 1 April 2025"),
    ),
)
@pytest.mark.parametrize(
    "rate, expected_first_paragraph, expected_second_paragraph",
    (
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
