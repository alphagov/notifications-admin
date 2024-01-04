def test_guidance_pricing_letters(client_request, mock_get_letter_rates):
    page = client_request.get(".guidance_pricing_letters")

    first_row = page.select_one("main table tbody tr")
    assert "1 sheet" in first_row.text

    assert "54p + VAT" in first_row.text
    assert "82p + VAT" in first_row.text
    assert "£1.44 + VAT" in first_row.text
