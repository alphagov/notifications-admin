from datetime import datetime, timedelta
from unittest.mock import ANY

import pytest
from bs4 import BeautifulSoup
from flask import url_for

from app.models.user import InvitedOrgUser
from tests.conftest import ORGANISATION_ID, normalize_spaces


def test_view_team_members(
    client_request,
    mocker,
    mock_get_organisation,
    mock_get_users_for_organisation,
    mock_get_invited_users_for_organisation,
    fake_uuid
):
    page = client_request.get(
        '.manage_org_users',
        org_id=ORGANISATION_ID,
    )

    for i in range(0, 2):
        assert normalize_spaces(
            page.select('.user-list-item .heading-small')[i].text
        ) == 'Test User {}'.format(i + 1)

    assert normalize_spaces(
        page.select('.tick-cross-list-edit-link')[0].text
    ) == 'Cancel invitation'


def test_invite_org_user(
    client_request,
    mocker,
    mock_get_organisation,
    sample_org_invite,
):

    mock_invite_org_user = mocker.patch(
        'app.org_invite_api_client.create_invite',
        return_value=sample_org_invite,
    )

    client_request.post(
        '.invite_org_user',
        org_id=ORGANISATION_ID,
        _data={'email_address': 'test@example.gov.uk'}
    )

    mock_invite_org_user.assert_called_once_with(
        sample_org_invite['invited_by'],
        '{}'.format(ORGANISATION_ID),
        'test@example.gov.uk',
    )


def test_invite_org_user_errors_when_same_email_as_inviter(
    client_request,
    mocker,
    mock_get_organisation,
    sample_org_invite,
):
    new_org_user_data = {
        'email_address': 'test@user.gov.uk',
    }

    mock_invite_org_user = mocker.patch(
        'app.org_invite_api_client.create_invite',
        return_value=sample_org_invite,
    )

    page = client_request.post(
        '.invite_org_user',
        org_id=ORGANISATION_ID,
        _data=new_org_user_data,
        _follow_redirects=True
    )

    assert mock_invite_org_user.called is False
    assert normalize_spaces(page.select_one('.error-message').text) == 'You cannot send an invitation to yourself'


def test_accepted_invite_when_other_user_already_logged_in(
    client_request,
    mock_check_org_invite_token
):
    page = client_request.get(
        'main.accept_org_invite',
        token='thisisnotarealtoken',
        follow_redirects=True,
        _expected_status=403,
    )
    assert 'This invite is for another email address.' in normalize_spaces(
        page.select_one('.banner-dangerous').text
    )


def test_cancelled_invite_opened_by_user(
    client,
    mock_check_org_cancelled_invite_token,
    mock_get_organisation,
    mock_get_user,
    fake_uuid
):
    response = client.get(url_for('main.accept_org_invite', token='thisisnotarealtoken'), follow_redirects=True)

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(
        page.select_one('h1').text
    ) == 'The invitation you were sent has been cancelled'
    assert normalize_spaces(
        page.select('main p')[0].text
    ) == 'Test User decided to cancel this invitation.'
    assert normalize_spaces(
        page.select('main p')[1].text
    ) == 'If you need access to Org 1, you’ll have to ask them to invite you again.'

    mock_get_user.assert_called_once_with(fake_uuid)
    mock_get_organisation.assert_called_once_with(ORGANISATION_ID)


def test_user_invite_already_accepted(
    client,
    mock_check_org_accepted_invite_token
):
    response = client.get(url_for('main.accept_org_invite', token='thisisnotarealtoken'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.organisation_dashboard',
        org_id=ORGANISATION_ID,
        _external=True
    )


def test_existing_user_invite_already_is_member_of_organisation(
    client,
    mock_check_org_invite_token,
    mock_get_user,
    mock_get_user_by_email,
    mock_get_users_for_organisation,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
):
    response = client.get(url_for('main.accept_org_invite', token='thisisnotarealtoken'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.organisation_dashboard',
        org_id=ORGANISATION_ID,
        _external=True
    )

    mock_check_org_invite_token.assert_called_once_with('thisisnotarealtoken')
    mock_accept_org_invite.assert_called_once_with(ORGANISATION_ID, ANY)
    mock_get_user_by_email.assert_called_once_with('invited_user@test.gov.uk')
    mock_get_users_for_organisation.assert_called_once_with(ORGANISATION_ID)


def test_existing_user_invite_not_a_member_of_organisation(
    client,
    api_user_active,
    mock_check_org_invite_token,
    mock_get_user_by_email,
    mock_get_users_for_organisation,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
):
    response = client.get(url_for('main.accept_org_invite', token='thisisnotarealtoken'))

    assert response.status_code == 302
    assert response.location == url_for(
        'main.organisation_dashboard',
        org_id=ORGANISATION_ID,
        _external=True
    )

    mock_check_org_invite_token.assert_called_once_with('thisisnotarealtoken')
    mock_accept_org_invite.assert_called_once_with(ORGANISATION_ID, ANY)
    mock_get_user_by_email.assert_called_once_with('invited_user@test.gov.uk')
    mock_get_users_for_organisation.assert_called_once_with(ORGANISATION_ID)
    mock_add_user_to_organisation.assert_called_once_with(
        ORGANISATION_ID,
        api_user_active['id'],
    )


def test_user_accepts_invite(
    client,
    mock_check_org_invite_token,
    mock_dont_get_user_by_email,
    mock_get_users_for_organisation,
):
    response = client.get(url_for('main.accept_org_invite', token='thisisnotarealtoken'))

    assert response.status_code == 302
    assert response.location == url_for('main.register_from_org_invite', _external=True)

    mock_check_org_invite_token.assert_called_once_with('thisisnotarealtoken')
    mock_dont_get_user_by_email.assert_called_once_with('invited_user@test.gov.uk')
    mock_get_users_for_organisation.assert_called_once_with(ORGANISATION_ID)


def test_registration_from_org_invite_404s_if_user_not_in_session(
    client,
):
    response = client.get(url_for('main.register_from_org_invite'))
    assert response.status_code == 404


@pytest.mark.parametrize('data, error', [
    [{
        'name': 'Bad Mobile',
        'mobile_number': 'not good',
        'password': 'validPassword!'
    }, 'Must not contain letters or symbols'],
    [{
        'name': 'Bad Password',
        'mobile_number': '+44123412345',
        'password': 'password'
    }, 'Choose a password that’s harder to guess'],
])
def test_registration_from_org_invite_has_bad_data(
    client,
    sample_org_invite,
    data,
    error
):
    invited_org_user = InvitedOrgUser(sample_org_invite)
    with client.session_transaction() as session:
        session['invited_org_user'] = invited_org_user.serialize()

    response = client.post(url_for('main.register_from_org_invite'), data=data)

    assert response.status_code == 200
    assert error in response.get_data(as_text=True)


@pytest.mark.parametrize('diff_data', [
    ['email_address'],
    ['organisation'],
    ['email_address', 'organisation']
])
def test_registration_from_org_invite_has_different_email_or_organisation(
    client,
    sample_org_invite,
    diff_data
):
    invited_org_user = InvitedOrgUser(sample_org_invite)
    with client.session_transaction() as session:
        session['invited_org_user'] = invited_org_user.serialize()

    for data in diff_data:
        session['invited_org_user'][data] = 'different'

    response = client.post(url_for('main.register_from_org_invite'), data={
        'name': 'Test User',
        'mobile_number': '+4407700900460',
        'password': 'validPassword!',
        'email_address': session['invited_org_user']['email_address'],
        'organisation': session['invited_org_user']['organisation']
    })

    assert response.status_code == 400


def test_org_user_registers_with_email_already_in_use(
    client,
    sample_org_invite,
    mock_get_user_by_email,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
    mock_send_already_registered_email,
    mock_register_user
):
    invited_org_user = InvitedOrgUser(sample_org_invite)
    with client.session_transaction() as session:
        session['invited_org_user'] = invited_org_user.serialize()

    response = client.post(url_for('main.register_from_org_invite'), data={
        'name': 'Test User',
        'mobile_number': '+4407700900460',
        'password': 'validPassword!',
        'email_address': session['invited_org_user']['email_address'],
        'organisation': session['invited_org_user']['organisation']
    })

    assert response.status_code == 302
    assert response.location == url_for('main.verify', _external=True)

    mock_get_user_by_email.assert_called_once_with(
        session['invited_org_user']['email_address']
    )
    assert mock_register_user.called is False
    assert mock_send_already_registered_email.called is False


def test_org_user_registration(
    client,
    sample_org_invite,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_send_verify_code,
    mock_get_user_by_email,
    mock_send_verify_email,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
):
    invited_org_user = InvitedOrgUser(sample_org_invite)
    with client.session_transaction() as session:
        session['invited_org_user'] = invited_org_user.serialize()

    response = client.post(url_for('main.register_from_org_invite'), data={
        'name': 'Test User',
        'email_address': session['invited_org_user']['email_address'],
        'mobile_number': '+4407700900460',
        'password': 'validPassword!',
        'organisation': session['invited_org_user']['organisation']
    })

    assert response.status_code == 302
    assert response.location == url_for('main.verify', _external=True)

    mock_get_user_by_email.called is False
    mock_register_user.assert_called_once_with(
        'Test User',
        session['invited_org_user']['email_address'],
        '+4407700900460',
        'validPassword!',
        'sms_auth'
    )
    mock_send_verify_code.assert_called_once_with(
        '6ce466d0-fd6a-11e5-82f5-e0accb9d11a6',
        'sms',
        '+4407700900460',
    )


def test_verified_org_user_redirects_to_dashboard(
    client,
    sample_org_invite,
    mock_check_verify_code,
    mock_get_user,
    mock_activate_user,
    mock_login,
):
    invited_org_user = InvitedOrgUser(sample_org_invite).serialize()
    with client.session_transaction() as session:
        session['expiry_date'] = str(datetime.utcnow() + timedelta(hours=1))
        session['user_details'] = {"email": invited_org_user['email_address'], "id": invited_org_user['id']}
        session['organisation_id'] = invited_org_user['organisation']

    response = client.post(url_for('main.verify'), data={'sms_code': '12345'})

    assert response.status_code == 302
    assert response.location == url_for(
        'main.organisation_dashboard',
        org_id=invited_org_user['organisation'],
        _external=True
    )
