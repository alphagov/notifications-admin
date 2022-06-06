from datetime import datetime, timedelta
from unittest.mock import ANY

import pytest
from flask import url_for
from freezegun import freeze_time

from app.models.user import InvitedOrgUser
from tests.conftest import ORGANISATION_ID, normalize_spaces


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
    assert 'You cannot send an invitation to yourself' in normalize_spaces(page.select_one('.govuk-error-message').text)


def test_cancel_invited_org_user_cancels_user_invitations(
    client_request,
    mock_get_invites_for_organisation,
    sample_org_invite,
    mock_get_organisation,
    mock_get_users_for_organisation,
    mocker,
):
    mock_cancel = mocker.patch('app.org_invite_api_client.cancel_invited_user')
    mocker.patch('app.org_invite_api_client.get_invited_user_for_org', return_value=sample_org_invite)

    page = client_request.get(
        'main.cancel_invited_org_user',
        org_id=ORGANISATION_ID,
        invited_user_id=sample_org_invite['id'],
        _follow_redirects=True
    )
    assert normalize_spaces(page.h1.text) == 'Team members'
    flash_banner = normalize_spaces(
        page.find('div', class_='banner-default-with-tick').text
    )
    assert flash_banner == f"Invitation cancelled for {sample_org_invite['email_address']}"
    mock_cancel.assert_called_once_with(
        org_id=ORGANISATION_ID,
        invited_user_id=sample_org_invite['id'],
    )


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
    mocker,
    client_request,
    api_user_active,
    mock_check_org_cancelled_invite_token,
    mock_get_organisation,
    fake_uuid
):
    client_request.logout()
    mock_get_user = mocker.patch('app.user_api_client.get_user', return_value=api_user_active)

    page = client_request.get(
        'main.accept_org_invite',
        token='thisisnotarealtoken',
        _follow_redirects=True,
    )

    assert normalize_spaces(
        page.select_one('h1').text
    ) == 'The invitation you were sent has been cancelled'
    assert normalize_spaces(
        page.select('main p')[0].text
    ) == 'Test User decided to cancel this invitation.'
    assert normalize_spaces(
        page.select('main p')[1].text
    ) == 'If you need access to Test organisation, you’ll have to ask them to invite you again.'

    mock_get_user.assert_called_once_with(fake_uuid)
    mock_get_organisation.assert_called_once_with(ORGANISATION_ID)


def test_user_invite_already_accepted(
    client_request,
    mock_check_org_accepted_invite_token
):
    client_request.logout()
    client_request.get(
        'main.accept_org_invite',
        token='thisisnotarealtoken',
        _expected_redirect=url_for(
            'main.organisation_dashboard',
            org_id=ORGANISATION_ID,
        ),
    )


@freeze_time('2021-12-12 12:12:12')
def test_existing_user_invite_already_is_member_of_organisation(
    client_request,
    mock_check_org_invite_token,
    mock_get_user,
    mock_get_user_by_email,
    api_user_active,
    mock_get_users_for_organisation,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
    mock_update_user_attribute,
):
    client_request.logout()
    mock_update_user_attribute.reset_mock()
    client_request.get(
        'main.accept_org_invite',
        token='thisisnotarealtoken',
        _expected_redirect=url_for(
            'main.organisation_dashboard',
            org_id=ORGANISATION_ID,
        ),
    )

    mock_check_org_invite_token.assert_called_once_with('thisisnotarealtoken')
    mock_accept_org_invite.assert_called_once_with(ORGANISATION_ID, ANY)
    mock_get_user_by_email.assert_called_once_with('invited_user@test.gov.uk')
    mock_get_users_for_organisation.assert_called_once_with(ORGANISATION_ID)
    mock_update_user_attribute.assert_called_once_with(
        api_user_active['id'],
        email_access_validated_at='2021-12-12T12:12:12',
    )


@freeze_time('2021-12-12 12:12:12')
def test_existing_user_invite_not_a_member_of_organisation(
    client_request,
    api_user_active,
    mock_check_org_invite_token,
    mock_get_user_by_email,
    mock_get_users_for_organisation,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
    mock_update_user_attribute,
):
    client_request.logout()
    mock_update_user_attribute.reset_mock()
    client_request.get(
        'main.accept_org_invite',
        token='thisisnotarealtoken',
        _expected_redirect=url_for(
            'main.organisation_dashboard',
            org_id=ORGANISATION_ID,
        ),
    )

    mock_check_org_invite_token.assert_called_once_with('thisisnotarealtoken')
    mock_accept_org_invite.assert_called_once_with(ORGANISATION_ID, ANY)
    mock_get_user_by_email.assert_called_once_with('invited_user@test.gov.uk')
    mock_get_users_for_organisation.assert_called_once_with(ORGANISATION_ID)
    mock_add_user_to_organisation.assert_called_once_with(
        ORGANISATION_ID,
        api_user_active['id'],
    )
    mock_update_user_attribute.assert_called_once_with(
        mock_get_user_by_email.side_effect(None)['id'],
        email_access_validated_at='2021-12-12T12:12:12',
    )


def test_user_accepts_invite(
    client_request,
    mock_check_org_invite_token,
    mock_dont_get_user_by_email,
    mock_get_users_for_organisation,
):
    client_request.logout()
    client_request.get(
        'main.accept_org_invite',
        token='thisisnotarealtoken',
        _expected_redirect=url_for('main.register_from_org_invite')
    )

    mock_check_org_invite_token.assert_called_once_with('thisisnotarealtoken')
    mock_dont_get_user_by_email.assert_called_once_with('invited_user@test.gov.uk')
    mock_get_users_for_organisation.assert_called_once_with(ORGANISATION_ID)


def test_registration_from_org_invite_404s_if_user_not_in_session(
    client_request,
):
    client_request.logout()
    client_request.get(
        'main.register_from_org_invite',
        _expected_status=404,
    )


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
    client_request,
    sample_org_invite,
    data,
    error,
    mock_get_invited_org_user_by_id,
):
    client_request.logout()

    with client_request.session_transaction() as session:
        session['invited_org_user_id'] = sample_org_invite['id']

    page = client_request.post(
        'main.register_from_org_invite',
        _data=data,
        _expected_status=200,
    )

    assert error in page.text


@pytest.mark.parametrize('diff_data', [
    ['email_address'],
    ['organisation'],
    ['email_address', 'organisation']
])
def test_registration_from_org_invite_has_different_email_or_organisation(
    client_request,
    sample_org_invite,
    diff_data,
    mock_get_invited_org_user_by_id,
):
    client_request.logout()
    with client_request.session_transaction() as session:
        session['invited_org_user_id'] = sample_org_invite['id']

    data = {
        'name': 'Test User',
        'mobile_number': '+4407700900460',
        'password': 'validPassword!',
        'email_address': sample_org_invite['email_address'],
        'organisation': sample_org_invite['organisation']
    }
    for field in diff_data:
        data[field] = 'different'

    client_request.post(
        'main.register_from_org_invite',
        _data=data,
        _expected_status=400,
    )


def test_org_user_registers_with_email_already_in_use(
    client_request,
    sample_org_invite,
    mock_get_user_by_email,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
    mock_send_already_registered_email,
    mock_register_user,
    mock_get_invited_org_user_by_id,
):
    client_request.logout()
    with client_request.session_transaction() as session:
        session['invited_org_user_id'] = sample_org_invite['id']

    client_request.post(
        'main.register_from_org_invite',
        _data={
            'name': 'Test User',
            'mobile_number': '+4407700900460',
            'password': 'validPassword!',
            'email_address': sample_org_invite['email_address'],
            'organisation': sample_org_invite['organisation'],
        },
        _expected_redirect=url_for('main.verify'),
    )

    mock_get_user_by_email.assert_called_once_with(
        sample_org_invite['email_address']
    )
    assert mock_register_user.called is False
    assert mock_send_already_registered_email.called is False


def test_org_user_registration(
    client_request,
    sample_org_invite,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_send_verify_code,
    mock_get_user_by_email,
    mock_send_verify_email,
    mock_accept_org_invite,
    mock_add_user_to_organisation,
    mock_get_invited_org_user_by_id,
):
    client_request.logout()
    with client_request.session_transaction() as session:
        session['invited_org_user_id'] = sample_org_invite['id']

    client_request.post(
        'main.register_from_org_invite',
        _data={
            'name': 'Test User',
            'email_address': sample_org_invite['email_address'],
            'mobile_number': '+4407700900460',
            'password': 'validPassword!',
            'organisation': sample_org_invite['organisation'],
        },
        _expected_redirect=url_for('main.verify')
    )

    assert mock_get_user_by_email.called is False
    mock_register_user.assert_called_once_with(
        'Test User',
        sample_org_invite['email_address'],
        '+4407700900460',
        'validPassword!',
        'sms_auth'
    )
    mock_send_verify_code.assert_called_once_with(
        '6ce466d0-fd6a-11e5-82f5-e0accb9d11a6',
        'sms',
        '+4407700900460',
    )
    mock_get_invited_org_user_by_id.assert_called_once_with(sample_org_invite['id'])


def test_verified_org_user_redirects_to_dashboard(
    client_request,
    sample_org_invite,
    mock_check_verify_code,
    mock_get_user,
    mock_activate_user,
    mock_login,
):
    client_request.logout()
    invited_org_user = InvitedOrgUser(sample_org_invite).serialize()
    with client_request.session_transaction() as session:
        session['expiry_date'] = str(datetime.utcnow() + timedelta(hours=1))
        session['user_details'] = {"email": invited_org_user['email_address'], "id": invited_org_user['id']}
        session['organisation_id'] = invited_org_user['organisation']

    client_request.post(
        'main.verify',
        _data={'sms_code': '12345'},
        _expected_redirect=url_for(
            'main.organisation_dashboard',
            org_id=invited_org_user['organisation'],
        ),
    )
