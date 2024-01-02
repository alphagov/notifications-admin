def test_guidance_pricing_letters(client_request):
    page = client_request.get(".guidance_pricing_letters")

    first_row = page.select_one("main table tbody tr")
    assert "1 sheet" in first_row.text

    # Update these values if letter prices change
    assert "54p + VAT" in first_row.text
    assert "82p + VAT" in first_row.text
    assert "£1.44 + VAT" in first_row.text
