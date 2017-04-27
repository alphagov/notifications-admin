from datetime import datetime
from bs4 import BeautifulSoup
from unittest.mock import ANY

from flask import (
    url_for,
    session
)
from app.notify_client.models import InvitedUser


def test_render_register_returns_template_with_form(client):
    response = client.get('/register')

    assert response.status_code == 200
    assert 'Create an account' in response.get_data(as_text=True)


def test_logged_in_user_redirects_to_choose_service(
    logged_in_client,
    api_user_active,
    mock_get_user_by_email,
    mock_send_verify_code,
    mock_login,
):
    response = logged_in_client.get(url_for('main.register'))
    assert response.status_code == 302

    response = logged_in_client.get(url_for('main.sign_in', follow_redirects=True))
    assert response.location == url_for('main.choose_service', _external=True)


def test_register_creates_new_user_and_redirects_to_continue_page(
    client,
    mock_send_verify_code,
    mock_register_user,
    mock_get_user_by_email_not_found,
    mock_is_email_unique,
    mock_send_verify_email,
    mock_login,
):
    user_data = {'name': 'Some One Valid',
                 'email_address': 'notfound@example.gov.uk',
                 'mobile_number': '+4407700900460',
                 'password': 'validPassword!'
                 }

    response = client.post(url_for('main.register'), data=user_data, follow_redirects=True)
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.select('main p')[0].text == 'An email has been sent to notfound@example.gov.uk.'

    mock_send_verify_email.assert_called_with(ANY, user_data['email_address'])
    mock_register_user.assert_called_with(user_data['name'],
                                          user_data['email_address'],
                                          user_data['mobile_number'],
                                          user_data['password'])


def test_register_continue_handles_missing_session_sensibly(
    client,
):
    # session is not set
    response = client.get(url_for('main.registration_continue'))
    assert response.status_code == 302
    assert response.location == url_for('main.show_all_services_or_dashboard', _external=True)


def test_process_register_returns_200_when_mobile_number_is_invalid(
    client,
    mock_send_verify_code,
    mock_get_user_by_email_not_found,
    mock_login,
):
    response = client.post(url_for('main.register'),
                           data={'name': 'Bad Mobile',
                                 'email_address': 'bad_mobile@example.gov.uk',
                                 'mobile_number': 'not good',
                                 'password': 'validPassword!'})

    assert response.status_code == 200
    assert 'Must not contain letters or symbols' in response.get_data(as_text=True)


def test_should_return_200_when_email_is_not_gov_uk(
    client,
    mock_send_verify_code,
    mock_get_user_by_email,
    mock_login,
):
    response = client.post(url_for('main.register'),
                           data={'name': 'Bad Mobile',
                                 'email_address': 'bad_mobile@example.not.right',
                                 'mobile_number': '+44123412345',
                                 'password': 'validPassword!'})

    assert response.status_code == 200
    assert 'Enter a central government email address' in response.get_data(as_text=True)


def test_should_add_user_details_to_session(
    client,
    mock_send_verify_code,
    mock_register_user,
    mock_get_user,
    mock_get_user_by_email_not_found,
    mock_is_email_unique,
    mock_send_verify_email,
    mock_login,
):
    user_data = {
        'name': 'Test Codes',
        'email_address': 'notfound@example.gov.uk',
        'mobile_number': '+4407700900460',
        'password': 'validPassword!'
    }

    response = client.post(url_for('main.register'), data=user_data)

    assert response.status_code == 302
    assert session['user_details']['email'] == user_data['email_address']


def test_should_return_200_if_password_is_blacklisted(
    client,
    mock_get_user_by_email,
    mock_login,
):
    response = client.post(url_for('main.register'),
                           data={'name': 'Bad Mobile',
                                 'email_address': 'bad_mobile@example.not.right',
                                 'mobile_number': '+44123412345',
                                 'password': 'password'})

    response.status_code == 200
    assert 'Choose a password that’s harder to guess' in response.get_data(as_text=True)


def test_register_with_existing_email_sends_emails(
    client,
    api_user_active,
    mock_get_user_by_email,
    mock_send_already_registered_email,
):
    user_data = {
        'name': 'Already Hasaccount',
        'email_address': api_user_active.email_address,
        'mobile_number': '+4407700900460',
        'password': 'validPassword!'
    }

    response = client.post(url_for('main.register'),
                           data=user_data)
    assert response.status_code == 302
    assert response.location == url_for('main.registration_continue', _external=True)


def test_register_from_invite_(
    client,
    fake_uuid,
    mock_is_email_unique,
    mock_register_user,
    mock_send_verify_code,
    mock_accept_invite,
):
    invited_user = InvitedUser(fake_uuid, fake_uuid, "",
                               "invited@user.com",
                               ["manage_users"],
                               "pending",
                               datetime.utcnow())
    with client.session_transaction() as session:
        session['invited_user'] = invited_user.serialize()
    response = client.post(url_for('main.register_from_invite'),
                           data={'name': 'Registered in another Browser',
                                 'email_address': invited_user.email_address,
                                 'mobile_number': '+4407700900460',
                                 'service': str(invited_user.id),
                                 'password': 'somreallyhardthingtoguess'})
    assert response.status_code == 302
    assert response.location == url_for('main.verify', _external=True)


def test_register_from_invite_when_user_registers_in_another_browser(
    client,
    api_user_active,
    mock_is_email_not_unique,
    mock_get_user_by_email,
    mock_accept_invite,
):
    invited_user = InvitedUser(api_user_active.id, api_user_active.id, "",
                               api_user_active.email_address,
                               ["manage_users"],
                               "pending",
                               datetime.utcnow())
    with client.session_transaction() as session:
        session['invited_user'] = invited_user.serialize()
    response = client.post(url_for('main.register_from_invite'),
                           data={'name': 'Registered in another Browser',
                                 'email_address': api_user_active.email_address,
                                 'mobile_number': api_user_active.mobile_number,
                                 'service': str(api_user_active.id),
                                 'password': 'somreallyhardthingtoguess'})
    assert response.status_code == 302
    assert response.location == url_for('main.verify', _external=True)
