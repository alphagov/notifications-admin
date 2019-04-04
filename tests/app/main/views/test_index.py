from functools import partial

import pytest
from bs4 import BeautifulSoup
from flask import url_for

from app.main.forms import FieldWithNoneOption
from tests.conftest import (
    mock_get_organisation_by_domain,
    normalize_spaces,
    sample_uuid,
)


def test_non_logged_in_user_can_see_homepage(
    client,
):
    response = client.get(url_for('main.index'))
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.h1.text.strip() == (
        'Send emails, text messages and letters to your users'
    )

    assert page.select_one('meta[name=description]')['content'].strip() == (
        'GOV.UK Notify lets you send emails, text messages and letters '
        'to your users. Try it now if you work in central government, a '
        'local authority, or the NHS.'
    )


def test_logged_in_user_redirects_to_choose_account(
    client_request,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_login,
):
    client_request.get(
        'main.index',
        _expected_status=302,
    )
    client_request.get(
        'main.sign_in',
        _expected_status=302,
        _expected_redirect=url_for('main.show_accounts_or_dashboard', _external=True)
    )


def test_robots(client):
    assert url_for('main.robots') == '/robots.txt'
    response = client.get(url_for('main.robots'))
    assert response.headers['Content-Type'] == 'text/plain'
    assert response.status_code == 200
    assert response.get_data(as_text=True) == (
        'User-agent: *\n'
        'Disallow: /sign-in\n'
        'Disallow: /support\n'
        'Disallow: /support/\n'
        'Disallow: /register\n'
    )


@pytest.mark.parametrize('view', [
    'cookies', 'privacy', 'using_notify', 'pricing', 'terms', 'roadmap',
    'features', 'callbacks', 'documentation', 'security'
])
def test_static_pages(
    client_request,
    mock_get_organisation_by_domain,
    view,
):
    page = client_request.get('main.{}'.format(view))
    assert not page.select_one('meta[name=description]')


@pytest.mark.parametrize('view, expected_anchor', [
    ('delivery_and_failure', 'messagedeliveryandfailure'),
    ('trial_mode', 'trial-mode'),
])
def test_old_static_pages_redirect_to_using_notify_with_anchor(
    client_request,
    view,
    expected_anchor,
):
    client_request.get(
        'main.{}'.format(view),
        _expected_status=301,
        _expected_redirect=url_for(
            'main.using_notify',
            _anchor=expected_anchor,
            _external=True
        ),
    )


@pytest.mark.parametrize('view, expected_view', [
    ('information_risk_management', 'security'),
    ('old_integration_testing', 'integration_testing'),
    ('old_roadmap', 'roadmap'),
    ('information_risk_management', 'security'),
    ('old_terms', 'terms'),
    ('information_security', 'using_notify'),
    ('old_using_notify', 'using_notify'),
])
def test_old_static_pages_redirect(
    client,
    view,
    expected_view
):
    response = client.get(url_for('main.{}'.format(view)))
    assert response.status_code == 301
    assert response.location == url_for(
        'main.{}'.format(expected_view),
        _external=True
    )


def test_old_integration_testing_page(
    client_request,
):
    page = client_request.get(
        'main.integration_testing',
        _expected_status=410,
    )
    assert normalize_spaces(page.select_one('.grid-row').text) == (
        'Integration testing '
        'This information has moved. '
        'Refer to the documentation for the client library you are using.'
    )
    assert page.select_one('.grid-row a')['href'] == url_for(
        'main.documentation'
    )


def test_terms_is_generic_if_user_is_not_logged_in(
    client
):
    response = client.get(url_for('main.terms'))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(page.select('main p')[1].text) == (
        'Your organisation must also accept our data sharing and '
        'financial agreement. Sign in to download a copy or find out '
        'if one is already in place.'
    )


def test_pricing_is_generic_if_user_is_not_logged_in(
    client
):
    response = client.get(url_for('main.pricing'))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    last_paragraph = page.select('main p')[-1]
    assert normalize_spaces(last_paragraph.text) == (
        'Sign in to download a copy or find out if one is already '
        'in place with your organisation.'
    )
    assert last_paragraph.select_one('a')['href'] == url_for(
        'main.sign_in',
        next=url_for('main.pricing', _anchor='paying'),
    )


@pytest.mark.parametrize((
    'name,'
    'agreement_signed,'
    'expected_terms_paragraph,'
    'expected_terms_link,'
    'expected_pricing_paragraph'
), [
    (
        'Cabinet Office',
        True,
        (
            'Your organisation (Cabinet Office) has already accepted '
            'the GOV.UK Notify data sharing and financial agreement.'
        ),
        None,
        (
            'Download the agreement '
            '(Cabinet Office has already accepted it).'
        ),
    ),
    (
        'Aylesbury Town Council',
        False,
        (
            'Your organisation (Aylesbury Town Council) must also '
            'accept our data sharing and financial agreement. Download '
            'a copy.'
        ),
        partial(
            url_for,
            'main.agreement',
        ),
        (
            'Download the agreement '
            '(Aylesbury Town Council hasn’t accepted it yet).'
        ),
    ),
    (
        None,
        None,
        (
            'Your organisation must also accept our data sharing and '
            'financial agreement. Download the agreement or contact us '
            'to find out if we already have one in place with your '
            'organisation.'
        ),
        partial(
            url_for,
            'main.agreement',
        ),
        (
            'Download the agreement or contact us to find out if '
            'we already have one in place with your organisation.'
        ),
    ),
    (
        'Met Office',
        False,
        (
            'Your organisation (Met Office) must also accept our data '
            'sharing and financial agreement. Download a copy.'
        ),
        partial(
            url_for,
            'main.agreement',
        ),
        (
            'Download the agreement (Met Office hasn’t accepted it '
            'yet).'
        ),
    ),
])
def test_terms_tells_logged_in_users_what_we_know_about_their_agreement(
    mocker,
    fake_uuid,
    client_request,
    name,
    agreement_signed,
    expected_terms_paragraph,
    expected_terms_link,
    expected_pricing_paragraph,
):
    mock_get_organisation_by_domain(
        mocker,
        name=name,
        agreement_signed=agreement_signed,
    )
    terms_page = client_request.get('main.terms')
    pricing_page = client_request.get('main.pricing')
    assert normalize_spaces(terms_page.select('main p')[1].text) == expected_terms_paragraph
    if expected_terms_link:
        assert terms_page.select_one('main p a')['href'] == expected_terms_link()
    else:
        assert not terms_page.select_one('main p').select('a')
    assert normalize_spaces(pricing_page.select('main p')[-1].text) == expected_pricing_paragraph


def test_css_is_served_from_correct_path(client_request):

    page = client_request.get('main.documentation')  # easy static page

    for index, link in enumerate(
        page.select('link[rel=stylesheet]')
    ):
        assert link['href'].startswith([
            'https://static.example.com/stylesheets/govuk-template.css?',
            'https://static.example.com/stylesheets/govuk-template-print.css?',
            'https://static.example.com/stylesheets/fonts.css?',
            'https://static.example.com/stylesheets/main.css?',
        ][index])


@pytest.mark.parametrize('extra_args, email_branding_retrieved', (
    (
        {},
        False,
    ),
    (
        {'branding_style': '__NONE__'},
        False,
    ),
    (
        {'branding_style': sample_uuid()},
        True,
    ),
))
def test_email_branding_preview(
    client_request,
    mock_get_email_branding,
    extra_args,
    email_branding_retrieved,
):
    client_request.get(
        'main.email_template',
        _test_page_title=False,
        **extra_args
    )
    assert mock_get_email_branding.called is email_branding_retrieved


@pytest.mark.parametrize('branding_style, filename', [
    ('hm-government', 'hm-government'),
    (None, 'no-branding'),
    (FieldWithNoneOption.NONE_OPTION_VALUE, 'no-branding')
])
def test_letter_template_preview_links_to_the_correct_image(
    client_request,
    mocker,
    mock_get_letter_branding_by_id,
    branding_style,
    filename,
):
    page = client_request.get(
        'main.letter_template',
        _test_page_title=False,
        branding_style=branding_style
    )

    image_link = page.find('img')['src']

    assert image_link == url_for(
        'main.letter_branding_preview_image',
        filename=filename,
        page=1
    )


def test_letter_template_preview_headers(
    client,
    mock_get_letter_branding_by_id,
):
    response = client.get(
        url_for('main.letter_template', branding_style='hm-government')
    )

    assert response.headers.get('X-Frame-Options') == 'SAMEORIGIN'
