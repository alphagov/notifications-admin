import pytest


def test_BeautifulSoup_methods_are_overridden(
    client_request,
    mock_get_service_and_organisation_counts,
):
    client_request.logout()
    page = client_request.get("main.index", _test_page_title=False)

    with pytest.raises(AttributeError) as exception:
        page.find("h1")

    assert str(exception.value) == "Don’t use BeautifulSoup.find – try BeautifulSoup.select_one instead"

    with pytest.raises(AttributeError) as exception:
        page.find_all("h1")

    assert str(exception.value) == "Don’t use BeautifulSoup.find_all – try BeautifulSoup.select instead"
