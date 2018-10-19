import re

import pytest
from bs4 import BeautifulSoup
from flask import url_for


@pytest.mark.parametrize(
    "query_args, result", [
        ({}, True),
        ({'govuk_banner': 'false'}, 'false')
    ]
)
def test_renders(client, mocker, query_args, result):

    mocker.patch('app.main.views.index.HTMLEmailTemplate.__str__', return_value='rendered')

    response = client.get(url_for('main.email_template', **query_args))

    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'rendered'


def test_displays_govuk_branding_by_default(client):

    response = client.get(url_for('main.email_template'))

    page = BeautifulSoup(response.data.decode("utf-8"), "html.parser")

    assert response.status_code == 200

    assert page.find("a", attrs={"href": "https://www.gov.uk"})


def test_displays_govuk_branding(client, mock_get_email_branding_with_govuk_brand_type):

    response = client.get(url_for('main.email_template', branding_style="1"))

    page = BeautifulSoup(response.data.decode("utf-8"), "html.parser")

    assert response.status_code == 200

    assert page.find("a", attrs={"href": "https://www.gov.uk"})


def test_displays_both_branding(client, mock_get_email_branding_with_both_brand_type):

    response = client.get(url_for('main.email_template', branding_style="1"))

    page = BeautifulSoup(response.data.decode("utf-8"), "html.parser")

    assert response.status_code == 200
    mock_get_email_branding_with_both_brand_type.assert_called_once_with('1')

    assert page.find("a", attrs={"href": "https://www.gov.uk"})
    assert page.find("img", attrs={"src": re.compile("example.png$")})
    assert page.select("body > table:nth-of-type(3) table > tr:nth-of-type(1) > td:nth-of-type(2)")[0]\
        .get_text().strip() == 'Organisation text'  # brand text is set


def test_displays_org_branding(client, mock_get_email_branding):

    # mock_get_email_branding has 'brand_type' of 'org'
    response = client.get(url_for('main.email_template', branding_style="1"))

    page = BeautifulSoup(response.data.decode("utf-8"), "html.parser")

    assert response.status_code == 200
    mock_get_email_branding.assert_called_once_with('1')

    assert not page.find("a", attrs={"href": "https://www.gov.uk"})
    assert page.find("img", attrs={"src": re.compile("example.png")})
    assert not page.select("body > table > tr > td[bgcolor='#f00']")  # banner colour is not set
    assert page.select("body > table:nth-of-type(1) > tr:nth-of-type(1) > td:nth-of-type(2)")[0]\
        .get_text().strip() == 'Organisation text'  # brand text is set


def test_displays_org_branding_with_banner(
        client, mock_get_email_branding_with_org_banner_brand_type):

    response = client.get(url_for('main.email_template', branding_style="1"))

    page = BeautifulSoup(response.data.decode("utf-8"), "html.parser")

    assert response.status_code == 200
    mock_get_email_branding_with_org_banner_brand_type.assert_called_once_with('1')

    assert not page.find("a", attrs={"href": "https://www.gov.uk"})
    assert page.find("img", attrs={"src": re.compile("example.png")})
    assert page.select("body > table > tr > td[bgcolor='#f00']")  # banner colour is set
    assert page.select("body > table table > tr > td > span")[0]\
        .get_text().strip() == 'Organisation text'  # brand text is set


def test_displays_org_branding_with_banner_without_brand_text(
        client, mock_get_email_branding_without_brand_text):

    # mock_get_email_branding_without_brand_text has 'brand_type' of 'org_banner'
    response = client.get(url_for('main.email_template', branding_style="1"))

    page = BeautifulSoup(response.data.decode("utf-8"), "html.parser")

    assert response.status_code == 200
    mock_get_email_branding_without_brand_text.assert_called_once_with('1')

    assert not page.find("a", attrs={"href": "https://www.gov.uk"})
    assert page.find("img", attrs={"src": re.compile("example.png")})
    assert page.select("body > table > tr > td[bgcolor='#f00']")  # banner colour is set
    assert not page.select("body > table table > tr > td > span") == 0  # brand text is not set
