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


def test_displays_govuk_branding(client):

    response = client.get(url_for('main.email_template', branding_type="govuk", branding_style="1"))

    page = BeautifulSoup(response.data.decode("utf-8"), "html.parser")

    assert response.status_code == 200

    assert page.find("a", attrs={"href": "https://www.gov.uk"})


def test_displays_both_branding(client, mock_get_email_branding):

    response = client.get(url_for('main.email_template', branding_type="both", branding_style="1"))

    page = BeautifulSoup(response.data.decode("utf-8"), "html.parser")

    assert response.status_code == 200
    mock_get_email_branding.assert_called_once_with('1')

    assert page.find("a", attrs={"href": "https://www.gov.uk"})
    assert page.find("img", attrs={"src": re.compile("example.png$")})


def test_displays_org_branding(client, mock_get_email_branding):

    response = client.get(url_for('main.email_template', branding_type="org", branding_style="1"))

    page = BeautifulSoup(response.data.decode("utf-8"), "html.parser")

    assert response.status_code == 200
    mock_get_email_branding.assert_called_once_with('1')

    assert not page.find("a", attrs={"href": "https://www.gov.uk"})
    assert page.find("img", attrs={"src": re.compile("example.png")})
    assert not page.select("body > table > tr > td[bgcolor='#f00']")


def test_displays_org_branding_with_banner(client, mock_get_email_branding):

    response = client.get(url_for('main.email_template', branding_type="org_banner",
                                  branding_style="1"))

    page = BeautifulSoup(response.data.decode("utf-8"), "html.parser")

    assert response.status_code == 200
    mock_get_email_branding.assert_called_once_with('1')

    assert not page.find("a", attrs={"href": "https://www.gov.uk"})
    assert page.find("img", attrs={"src": re.compile("example.png")})
    assert page.select("body > table > tr > td[bgcolor='#f00']")
