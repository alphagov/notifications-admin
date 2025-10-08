import pytest


@pytest.mark.parametrize("query_args", [{}, {"govuk_banner": "false"}])
def test_renders(client_request, mocker, query_args):
    mocker.patch("app.main.views_nl.index.HTMLEmailTemplate.__str__", return_value="rendered")

    response = client_request.get_response("main.email_template", **query_args)

    assert response.get_data(as_text=True) == "rendered"


def test_displays_govuk_branding_by_default(client_request):
    page = client_request.get("main.email_template", _test_page_title=False)

    assert page.select_one("a")["href"] == "https://www.gov.uk"


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"branding_style": None},
        {"branding_style": "govuk"},
        {"branding_style": "__NONE__"},
        {"branding_style": ""},
    ],
)
def test_displays_govuk_branding(client_request, params):
    page = client_request.get("main.email_template", **params, _test_page_title=False)
    assert page.select_one("a")["href"] == "https://www.gov.uk"


def test_displays_both_branding(client_request, mock_get_email_branding_with_both_brand_type):
    page = client_request.get("main.email_template", branding_style="1", _test_page_title=False)

    mock_get_email_branding_with_both_brand_type.assert_called_once_with("1")

    assert page.select_one("a")["href"] == "https://www.gov.uk"
    assert page.select("img")[0]["src"] == (
        "https://static.notifications.service.gov.uk/images/govuk-logotype-tudor-crown.png"
    )
    assert page.select("img")[1]["src"] == "https://static-logos.test.com/example.png"
    assert (
        page.select("body > table:nth-of-type(2) table:nth-of-type(1) table td:nth-of-type(2)")[0].get_text().strip()
        == "Organisation text"
    )  # brand text is set


def test_displays_org_branding(client_request, mock_get_email_branding):
    # mock_get_email_branding has 'brand_type' of 'org'
    page = client_request.get("main.email_template", branding_style="1", _test_page_title=False)

    mock_get_email_branding.assert_called_once_with("1")

    assert not any(a["href"] == "https://www.gov.uk" for a in page.select("a"))
    assert page.select_one("img")["src"] == "https://static-logos.test.com/example.png"
    assert page.select_one("img")["alt"] == ""  # no alt text cos brand text is present
    assert not page.select("body > table > tr > td[bgcolor='#f00']")  # banner colour is not set
    assert (
        page.select("body > table:nth-of-type(1) > tr:nth-of-type(1) > td:nth-of-type(2)")[0].get_text().strip()
        == "Organisation text"
    )  # brand text is set


def test_displays_org_branding_with_banner(client_request, mock_get_email_branding_with_org_banner_brand_type):
    page = client_request.get("main.email_template", branding_style="1", _test_page_title=False)

    mock_get_email_branding_with_org_banner_brand_type.assert_called_once_with("1")

    assert not any(a["href"] == "https://www.gov.uk" for a in page.select("a"))
    assert page.select_one("img")["src"] == "https://static-logos.test.com/example.png"
    assert page.select("body > table > tr > td[bgcolor='#f00']")  # banner colour is set
    assert (
        page.select("body > table table > tr > td > span")[0].get_text().strip() == "Organisation text"
    )  # brand text is set


def test_displays_org_branding_with_banner_without_brand_text(
    client_request, mock_get_email_branding_without_brand_text
):
    # mock_get_email_branding_without_brand_text has 'brand_type' of 'org_banner'
    page = client_request.get("main.email_template", branding_style="1", _test_page_title=False)

    mock_get_email_branding_without_brand_text.assert_called_once_with("1")

    assert not any(a["href"] == "https://www.gov.uk" for a in page.select("a"))
    assert page.select_one("img")["src"] == "https://static-logos.test.com/example.png"
    assert page.select_one("img")["alt"] == "Alt text"
    assert page.select("body > table > tr > td[bgcolor='#f00']")  # banner colour is set
    assert not page.select("body > table table > tr > td > span") == 0  # brand text is not set


def test_displays_custom_brand_through_query_params(client_request, mocker):
    mock_get_email_branding = mocker.patch("app.email_branding_client.get_email_branding")

    page = client_request.get(
        "main.email_template",
        _test_page_title=False,
        branding_style="custom",
        text="Some text",
        colour="#abcdef",
        logo="example.png",
        brand_type="org",
    )

    assert mock_get_email_branding.called is False
    assert not any(a["href"] == "https://www.gov.uk" for a in page.select("a"))
    assert page.select_one("img")["src"] == "https://static-logos.test.com/example.png"
    assert not page.select("body > table > tr > td[bgcolor='#abcdef']")
    assert (
        page.select("body > table:nth-of-type(1) > tr:nth-of-type(1) > td:nth-of-type(2)")[0].get_text().strip()
        == "Some text"
    )
