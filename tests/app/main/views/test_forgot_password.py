import pytest
from flask import Response, url_for
from notifications_python_client.errors import HTTPError

import app
from tests import user_json
from tests.conftest import SERVICE_ONE_ID


def test_should_render_forgot_password(client_request):
    client_request.logout()
    page = client_request.get('.forgot_password')
    assert 'We’ll send you an email to create a new password.' in page.text


@pytest.mark.parametrize('email_address', [
    'test@user.gov.uk',
    'someuser@notgovernment.com'
])
def test_should_redirect_to_password_reset_sent_for_valid_email(
    client_request,
    fake_uuid,
    email_address,
    mocker,
):
    client_request.logout()
    sample_user = user_json(email_address=email_address)
    mocker.patch('app.user_api_client.send_reset_password_url', return_value=None)
    page = client_request.post(
        '.forgot_password',
        _data={'email_address': sample_user['email_address']},
        _expected_status=200,
    )
    assert 'Click the link in the email to reset your password.' in page.text
    app.user_api_client.send_reset_password_url.assert_called_once_with(sample_user['email_address'], next_string=None)


def test_forgot_password_sends_next_link_with_reset_password_email_request(
    client_request,
    fake_uuid,
    mocker,
):
    client_request.logout()
    sample_user = user_json(email_address='test@user.gov.uk')
    mocker.patch('app.user_api_client.send_reset_password_url', return_value=None)
    client_request.post_url(
        url_for('.forgot_password') + f"?next=/services/{SERVICE_ONE_ID}/templates",
        _data={'email_address': sample_user['email_address']},
        _expected_status=200,
    )
    app.user_api_client.send_reset_password_url.assert_called_once_with(
        sample_user['email_address'], next_string=f'/services/{SERVICE_ONE_ID}/templates'
    )


def test_should_redirect_to_password_reset_sent_for_missing_email(
    client_request,
    api_user_active,
    mocker,
):
    client_request.logout()
    mocker.patch('app.user_api_client.send_reset_password_url', side_effect=HTTPError(Response(status=404),
                                                                                      'Not found'))
    page = client_request.post(
        '.forgot_password',
        _data={'email_address': api_user_active['email_address']},
        _expected_status=200,
    )
    assert 'Click the link in the email to reset your password.' in page.text
    app.user_api_client.send_reset_password_url.assert_called_once_with(
        api_user_active['email_address'], next_string=None
    )
