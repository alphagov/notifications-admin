import pytest
from bs4 import BeautifulSoup
from flask import url_for
from tests.conftest import active_user_with_permissions, normalize_spaces


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


def test_logged_in_user_redirects_to_choose_service(
    logged_in_client,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_login,
):
    response = logged_in_client.get(url_for('main.index'))
    assert response.status_code == 302

    response = logged_in_client.get(url_for('main.sign_in', follow_redirects=True))
    assert response.location == url_for('main.choose_service', _external=True)


@pytest.mark.parametrize('view', [
    'cookies', 'using_notify', 'pricing', 'terms', 'integration_testing', 'roadmap',
    'features', 'callbacks', 'documentation', 'security'
])
def test_static_pages(
    client_request,
    view,
):
    page = client_request.get('main.{}'.format(view))
    assert not page.select_one('meta[name=description]')


@pytest.mark.parametrize('view, expected_anchor', [
    ('delivery_and_failure', 'messagedeliveryandfailure'),
    ('trial_mode', 'trial-mode'),
])
def test_old_static_pages_redirect_to_using_notify_with_anchor(
    client,
    view,
    expected_anchor,
):
    response = client.get(url_for('main.{}'.format(view)))
    assert response.status_code == 301
    assert response.location == url_for(
        'main.using_notify',
        _anchor=expected_anchor,
        _external=True
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


def test_terms_is_generic_if_user_is_not_logged_in(
    client
):
    response = client.get(url_for('main.terms'))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(page.select('main p')[1].text) == (
        'Your organisation must also accept our data sharing and '
        'financial agreement. Contact us to get a copy.'
    )


@pytest.mark.parametrize('email_address, expected_first_paragraph', [
    (
        'test@cabinet-office.gov.uk',
        (
            'Your organisation (Cabinet Office) has already accepted '
            'the GOV.UK Notify data sharing and financial agreement.'
        ),
    ),
    (
        'test@aylesburytowncouncil.gov.uk',
        (
            'Your organisation (Aylesbury Town Council) must also '
            'accept our data sharing and financial agreement. Contact '
            'us to get a copy.'
        ),
    ),
    (
        'larry@downing-street.gov.uk',
        (
            'Your organisation must also accept our data sharing and '
            'financial agreement. Contact us to get a copy.'
        ),
    ),
])
def test_terms_tells_logged_in_users_what_we_know_about_their_agreement(
    mocker,
    fake_uuid,
    client_request,
    email_address,
    expected_first_paragraph,
):
    user = active_user_with_permissions(fake_uuid)
    user.email_address = email_address
    mocker.patch('app.user_api_client.get_user', return_value=user)
    page = client_request.get('main.terms')
    assert normalize_spaces(page.select('main p')[1].text) == expected_first_paragraph
