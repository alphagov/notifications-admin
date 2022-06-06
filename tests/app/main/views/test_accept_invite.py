from unittest.mock import ANY, Mock, call

import pytest
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError

import app
from tests import service_json
from tests.conftest import (
    SERVICE_ONE_ID,
    create_active_caseworking_user,
    create_active_user_with_permissions,
    normalize_spaces,
)


@pytest.fixture()
def mock_no_users_for_service(mocker):
    mocker.patch('app.models.user.Users.client_method', return_value=[])


@pytest.fixture(scope='function')
def mock_get_existing_user_by_email(mocker, api_user_active):
    return mocker.patch('app.user_api_client.get_user_by_email', return_value=api_user_active)


@pytest.fixture(scope='function')
def mock_check_invite_token(mocker, sample_invite):
    return mocker.patch('app.invite_api_client.check_token', return_value=sample_invite)


@freeze_time('2021-12-12 12:12:12')
def test_existing_user_accept_invite_calls_api_and_redirects_to_dashboard(
    client_request,
    service_one,
    api_user_active,
    mock_check_invite_token,
    mock_get_existing_user_by_email,
    mock_no_users_for_service,
    mock_accept_invite,
    mock_add_user_to_service,
    mock_get_service,
    mocker,
    mock_events,
    mock_get_user,
    mock_update_user_attribute,
):
    client_request.logout()
    expected_service = service_one['id']
    expected_permissions = {'view_activity', 'send_messages', 'manage_service', 'manage_api_keys'}

    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_redirect=url_for('main.service_dashboard', service_id=expected_service),
    )

    mock_check_invite_token.assert_called_with('thisisnotarealtoken')
    mock_get_existing_user_by_email.assert_called_with('invited_user@test.gov.uk')
    assert mock_accept_invite.call_count == 1
    mock_add_user_to_service.assert_called_with(
        expected_service,
        api_user_active['id'],
        expected_permissions,
        [],
    )


@pytest.mark.parametrize('trial_mode, expected_endpoint', (
    (True, '.broadcast_tour'),
    (False, '.broadcast_tour_live'),
))
def test_broadcast_service_shows_tour(
    client_request,
    service_one,
    mock_check_invite_token,
    mock_get_existing_user_by_email,
    mock_no_users_for_service,
    mock_accept_invite,
    mock_add_user_to_service,
    mock_update_user_attribute,
    mocker,
    mock_events,
    mock_get_user,
    trial_mode,
    expected_endpoint,
):
    client_request.logout()
    service_one['permissions'] = ['broadcast']
    service_one['restricted'] = trial_mode

    mocker.patch('app.service_api_client.get_service', return_value={
        'data': service_one,
    })

    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_redirect=url_for(
            expected_endpoint,
            service_id=SERVICE_ONE_ID,
            step_index=1,
        ),
    )


def test_existing_user_with_no_permissions_or_folder_permissions_accept_invite(
    client_request,
    mocker,
    service_one,
    api_user_active,
    sample_invite,
    mock_check_invite_token,
    mock_get_existing_user_by_email,
    mock_no_users_for_service,
    mock_add_user_to_service,
    mock_get_service,
    mock_events,
    mock_get_user,
    mock_update_user_attribute,
):
    client_request.logout()

    expected_service = service_one['id']
    sample_invite['permissions'] = ''
    expected_permissions = set()
    expected_folder_permissions = []
    mocker.patch('app.invite_api_client.accept_invite', return_value=sample_invite)

    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_status=302,
    )
    mock_add_user_to_service.assert_called_with(expected_service,
                                                api_user_active['id'],
                                                expected_permissions,
                                                expected_folder_permissions)


def test_if_existing_user_accepts_twice_they_redirect_to_sign_in(
    client_request,
    mocker,
    sample_invite,
    mock_check_invite_token,
    mock_get_service,
    mock_update_user_attribute,
):
    client_request.logout()
    # Logging out updates the current session ID to `None`
    mock_update_user_attribute.reset_mock()
    sample_invite['status'] = 'accepted'

    page = client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _follow_redirects=True,
    )

    assert (
        page.h1.string,
        page.select('main p')[0].text.strip(),
    ) == (
        'You need to sign in again',
        'We signed you out because you have not used Notify for a while.',
    )
    # We don’t let people update `email_access_validated_at` using an
    # already-accepted invite
    assert mock_update_user_attribute.called is False


def test_invite_goes_in_session(
    client_request,
    mocker,
    sample_invite,
    mock_get_service,
    api_user_active,
    mock_check_invite_token,
    mock_get_user_by_email,
    mock_no_users_for_service,
    mock_add_user_to_service,
    mock_accept_invite,
):
    sample_invite['email_address'] = 'test@user.gov.uk'

    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_dashboard',
            service_id=SERVICE_ONE_ID,
        ),
        _follow_redirects=False,
    )

    with client_request.session_transaction() as session:
        assert session['invited_user_id'] == sample_invite['id']


@pytest.mark.parametrize('user, landing_page_title', [
    (create_active_user_with_permissions(), 'Dashboard'),
    (create_active_caseworking_user(), 'Templates'),
])
def test_accepting_invite_removes_invite_from_session(
    client_request,
    mocker,
    sample_invite,
    mock_get_service,
    service_one,
    mock_check_invite_token,
    mock_get_user_by_email,
    mock_no_users_for_service,
    mock_add_user_to_service,
    mock_accept_invite,
    mock_get_service_templates,
    mock_get_template_statistics,
    mock_has_no_jobs,
    mock_get_service_statistics,
    mock_get_template_folders,
    mock_get_annual_usage_for_service,
    mock_get_monthly_usage_for_service,
    mock_get_free_sms_fragment_limit,
    mock_get_inbound_sms_summary,
    mock_get_returned_letter_statistics_with_no_returned_letters,
    mock_get_api_keys,
    fake_uuid,
    user,
    landing_page_title,
):
    sample_invite['email_address'] = user['email_address']

    client_request.login(user)

    page = client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one('h1').text) == landing_page_title

    with client_request.session_transaction() as session:
        assert 'invited_user_id' not in session


@freeze_time('2021-12-12T12:12:12')
def test_existing_user_of_service_get_redirected_to_signin(
    client_request,
    mocker,
    api_user_active,
    sample_invite,
    mock_get_service,
    mock_get_user_by_email,
    mock_check_invite_token,
    mock_accept_invite,
    mock_update_user_attribute,
):
    client_request.logout()
    sample_invite['email_address'] = api_user_active['email_address']
    mocker.patch('app.models.user.Users.client_method', return_value=[api_user_active])

    page = client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _follow_redirects=True,
    )

    assert (
        page.h1.string,
        page.select('main p')[0].text.strip(),
    ) == (
        'You need to sign in again',
        'We signed you out because you have not used Notify for a while.',
    )
    assert mock_accept_invite.call_count == 1


def test_accept_invite_redirects_if_api_raises_an_error_that_they_are_already_part_of_the_service(
    client_request,
    mocker,
    api_user_active,
    sample_invite,
    mock_get_existing_user_by_email,
    mock_check_invite_token,
    mock_accept_invite,
    mock_get_service,
    mock_no_users_for_service,
    mock_get_user,
    mock_update_user_attribute,
):
    client_request.logout()

    mocker.patch('app.user_api_client.add_user_to_service', side_effect=HTTPError(
        response=Mock(
            status_code=400,
            json={
                "result": "error",
                "message": {f"User id: {api_user_active['id']} already part of service id: {SERVICE_ONE_ID}"}
            },
        ),
        message=f"User id: {api_user_active['id']} already part of service id: {SERVICE_ONE_ID}"
    ))

    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _follow_redirects=False,
        _expected_redirect=url_for('main.service_dashboard', service_id=SERVICE_ONE_ID)
    )


def test_existing_signed_out_user_accept_invite_redirects_to_sign_in(
    client_request,
    service_one,
    api_user_active,
    sample_invite,
    mock_check_invite_token,
    mock_get_existing_user_by_email,
    mock_no_users_for_service,
    mock_add_user_to_service,
    mock_accept_invite,
    mock_get_service,
    mocker,
    mock_events,
    mock_get_user,
    mock_update_user_attribute,
):
    client_request.logout()
    expected_service = service_one['id']
    expected_permissions = {'view_activity', 'send_messages', 'manage_service', 'manage_api_keys'}

    page = client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _follow_redirects=True,
    )

    mock_check_invite_token.assert_called_with('thisisnotarealtoken')
    mock_get_existing_user_by_email.assert_called_with('invited_user@test.gov.uk')
    mock_add_user_to_service.assert_called_with(expected_service,
                                                api_user_active['id'],
                                                expected_permissions,
                                                sample_invite['folder_permissions'])
    assert mock_accept_invite.call_count == 1
    assert (
        page.h1.string,
        page.select('main p')[0].text.strip(),
    ) == (
        'You need to sign in again',
        'We signed you out because you have not used Notify for a while.',
    )


def test_new_user_accept_invite_calls_api_and_redirects_to_registration(
    client_request,
    service_one,
    mock_check_invite_token,
    mock_dont_get_user_by_email,
    mock_add_user_to_service,
    mock_no_users_for_service,
    mock_get_service,
    mocker,
):
    client_request.logout()
    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_redirect='/register-from-invite',
    )

    mock_check_invite_token.assert_called_with('thisisnotarealtoken')
    mock_dont_get_user_by_email.assert_called_with('invited_user@test.gov.uk')


def test_new_user_accept_invite_calls_api_and_views_registration_page(
    client_request,
    service_one,
    sample_invite,
    mock_check_invite_token,
    mock_dont_get_user_by_email,
    mock_get_invited_user_by_id,
    mock_add_user_to_service,
    mock_no_users_for_service,
    mock_get_service,
    mocker,
):
    client_request.logout()
    page = client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _follow_redirects=True,
    )

    mock_check_invite_token.assert_called_with('thisisnotarealtoken')
    mock_dont_get_user_by_email.assert_called_with('invited_user@test.gov.uk')
    mock_get_invited_user_by_id.assert_called_once_with(sample_invite['id'])

    assert page.h1.string.strip() == 'Create an account'

    assert normalize_spaces(page.select_one('main p').text) == (
        'Your account will be created with this email address: '
        'invited_user@test.gov.uk'
    )

    form = page.find('form')
    name = form.find('input', id='name')
    password = form.find('input', id='password')
    service = form.find('input', type='hidden', id='service')
    email = form.find('input', type='hidden', id='email_address')

    assert email
    assert email.attrs['value'] == 'invited_user@test.gov.uk'
    assert name
    assert password
    assert service
    assert service.attrs['value'] == service_one['id']


def test_cancelled_invited_user_accepts_invited_redirect_to_cancelled_invitation(
    client_request,
    mock_get_user,
    mock_get_service,
    sample_invite,
    mock_check_invite_token,
    mock_update_user_attribute,
):
    client_request.logout()
    mock_update_user_attribute.reset_mock()
    sample_invite['status'] = 'cancelled'
    page = client_request.get('main.accept_invite', token='thisisnotarealtoken')

    app.invite_api_client.check_token.assert_called_with('thisisnotarealtoken')

    assert page.h1.string.strip() == 'The invitation you were sent has been cancelled'
    # We don’t let people update `email_access_validated_at` using an
    # cancelled invite
    assert mock_update_user_attribute.called is False


@pytest.mark.parametrize('admin_endpoint, api_endpoint', [
    ('main.accept_invite', 'app.invite_api_client.check_token'),
    ('main.accept_org_invite', 'app.org_invite_api_client.check_token'),
])
def test_new_user_accept_invite_with_malformed_token(
    admin_endpoint,
    api_endpoint,
    client_request,
    service_one,
    mocker,
):
    client_request.logout()
    mocker.patch(api_endpoint, side_effect=HTTPError(
        response=Mock(
            status_code=400,
            json={
                'result': 'error',
                'message': {
                    'invitation': {
                        'Something’s wrong with this link. Make sure you’ve copied the whole thing.'
                    }
                }
            }
        ),
        message={'invitation': 'Something’s wrong with this link. Make sure you’ve copied the whole thing.'}
    ))

    page = client_request.get(admin_endpoint, token='thisisnotarealtoken', _follow_redirects=True)

    assert normalize_spaces(
        page.select_one('.banner-dangerous').text
    ) == 'Something’s wrong with this link. Make sure you’ve copied the whole thing.'


def test_new_user_accept_invite_completes_new_registration_redirects_to_verify(
    client_request,
    service_one,
    sample_invite,
    api_user_active,
    mock_check_invite_token,
    mock_dont_get_user_by_email,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_send_verify_code,
    mock_get_invited_user_by_id,
    mock_accept_invite,
    mock_no_users_for_service,
    mock_add_user_to_service,
    mock_get_service,
    mocker,
):
    client_request.logout()
    expected_redirect_location = '/register-from-invite'

    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_redirect=expected_redirect_location,
    )
    with client_request.session_transaction() as session:
        assert session.get('invited_user_id') == sample_invite['id']

    data = {'service': sample_invite['service'],
            'email_address': sample_invite['email_address'],
            'from_user': sample_invite['from_user'],
            'password': 'longpassword',
            'mobile_number': '+447890123456',
            'name': 'Invited User',
            'auth_type': 'email_auth'
            }

    expected_redirect_location = '/verify'
    client_request.post(
        'main.register_from_invite',
        _data=data,
        _expected_redirect=expected_redirect_location,
    )

    mock_send_verify_code.assert_called_once_with(ANY, 'sms', data['mobile_number'])
    mock_get_invited_user_by_id.assert_called_once_with(sample_invite['id'])

    mock_register_user.assert_called_with(data['name'],
                                          data['email_address'],
                                          data['mobile_number'],
                                          data['password'],
                                          data['auth_type'])

    assert mock_accept_invite.call_count == 1


def test_signed_in_existing_user_cannot_use_anothers_invite(
    client_request,
    mocker,
    api_user_active,
    mock_check_invite_token,
    sample_invite,
    mock_get_user,
    mock_accept_invite,
    mock_get_service,
):
    mocker.patch('app.user_api_client.get_users_for_service', return_value=[api_user_active])

    page = client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _follow_redirects=True,
        _expected_status=403,
    )
    assert page.h1.string.strip() == 'You’re not allowed to see this page'
    flash_banners = page.find_all('div', class_='banner-dangerous')
    assert len(flash_banners) == 1
    banner_contents = normalize_spaces(flash_banners[0].text)
    assert "You’re signed in as test@user.gov.uk." in banner_contents
    assert "This invite is for another email address." in banner_contents
    assert "Sign out and click the link again to accept this invite." in banner_contents
    assert mock_accept_invite.call_count == 0


def test_accept_invite_does_not_treat_email_addresses_as_case_sensitive(
    client_request,
    mocker,
    api_user_active,
    sample_invite,
    mock_accept_invite,
    mock_check_invite_token,
    mock_get_user_by_email
):
    # the email address of api_user_active is 'test@user.gov.uk'
    sample_invite['email_address'] = 'TEST@user.gov.uk'
    mocker.patch('app.models.user.Users.client_method', return_value=[api_user_active])

    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_dashboard',
            service_id=SERVICE_ONE_ID,
        )
    )


def test_new_invited_user_verifies_and_added_to_service(
    client_request,
    service_one,
    sample_invite,
    api_user_active,
    mock_check_invite_token,
    mock_dont_get_user_by_email,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_send_verify_code,
    mock_check_verify_code,
    mock_get_user,
    mock_update_user_attribute,
    mock_add_user_to_service,
    mock_accept_invite,
    mock_get_service,
    mock_get_invited_user_by_id,
    mock_get_service_templates,
    mock_get_template_statistics,
    mock_has_no_jobs,
    mock_has_permissions,
    mock_no_users_for_service,
    mock_get_service_statistics,
    mock_get_annual_usage_for_service,
    mock_get_free_sms_fragment_limit,
    mock_get_returned_letter_statistics_with_no_returned_letters,
    mock_create_event,
    mocker,
):
    client_request.logout()

    # visit accept token page
    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_redirect=url_for('main.register_from_invite'),
    )

    # get redirected to register from invite
    data = {
        'service': sample_invite['service'],
        'email_address': sample_invite['email_address'],
        'from_user': sample_invite['from_user'],
        'password': 'longpassword',
        'mobile_number': '+447890123456',
        'name': 'Invited User',
        'auth_type': 'sms_auth'
    }
    client_request.post(
        'main.register_from_invite',
        _data=data,
        _expected_redirect=url_for('main.verify'),
    )

    # that sends user on to verify
    page = client_request.post(
        'main.verify',
        _data={'sms_code': '12345'},
        _follow_redirects=True,
    )

    # when they post codes back to admin user should be added to
    # service and sent on to dash board
    expected_permissions = {'view_activity', 'send_messages', 'manage_service', 'manage_api_keys'}

    with client_request.session_transaction() as session:
        assert 'invited_user_id' not in session
        new_user_id = session['user_id']
        mock_add_user_to_service.assert_called_with(data['service'], new_user_id, expected_permissions, [])
        mock_accept_invite.assert_called_with(data['service'], sample_invite['id'])
        mock_check_verify_code.assert_called_once_with(new_user_id, '12345', 'sms')
        assert service_one['id'] == session['service_id']

    assert page.find('h1').text == 'Dashboard'


@pytest.mark.parametrize('service_permissions, trial_mode, expected_endpoint, extra_args', (
    ([], True, 'main.service_dashboard', {}),
    ([], False, 'main.service_dashboard', {}),
    (['broadcast'], True, 'main.broadcast_tour', {'step_index': 1}),
    (['broadcast'], False, 'main.broadcast_tour_live', {'step_index': 1}),
))
def test_new_invited_user_is_redirected_to_correct_place(
    mocker,
    client_request,
    sample_invite,
    mock_check_invite_token,
    mock_check_verify_code,
    mock_get_user,
    mock_dont_get_user_by_email,
    mock_add_user_to_service,
    mock_get_invited_user_by_id,
    mock_events,
    mock_get_service,
    service_permissions,
    trial_mode,
    expected_endpoint,
    extra_args,
):
    client_request.logout()
    mocker.patch('app.service_api_client.get_service', return_value={
        'data': service_json(
            sample_invite['service'],
            restricted=trial_mode,
            permissions=service_permissions,
        )
    })
    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_status=302,
    )

    with client_request.session_transaction() as session:
        session['user_details'] = {
            'email': sample_invite['email_address'],
            'id': sample_invite['id'],
        }

    client_request.post(
        'main.verify',
        _data={'sms_code': '12345'},
        _expected_redirect=url_for(
            expected_endpoint,
            service_id=sample_invite['service'],
            **extra_args
        )
    )


@freeze_time('2021-12-12 12:12:12')
def test_existing_user_accepts_and_sets_email_auth(
    client_request,
    api_user_active,
    service_one,
    sample_invite,
    mock_get_existing_user_by_email,
    mock_no_users_for_service,
    mock_accept_invite,
    mock_check_invite_token,
    mock_update_user_attribute,
    mock_add_user_to_service,
    mocker
):
    sample_invite['email_address'] = api_user_active['email_address']

    service_one['permissions'].append('email_auth')
    sample_invite['auth_type'] = 'email_auth'

    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_status=302,
        _expected_redirect=url_for('main.service_dashboard', service_id=service_one['id']),
    )

    mock_get_existing_user_by_email.assert_called_once_with('test@user.gov.uk')
    assert mock_update_user_attribute.call_args_list == [
        call(api_user_active['id'], email_access_validated_at='2021-12-12T12:12:12'),
        call(api_user_active['id'], auth_type='email_auth'),
    ]
    mock_add_user_to_service.assert_called_once_with(ANY, api_user_active['id'], ANY, ANY)


@freeze_time('2021-12-12 12:12:12')
def test_platform_admin_user_accepts_and_preserves_auth(
    client_request,
    platform_admin_user,
    service_one,
    sample_invite,
    mock_check_invite_token,
    mock_no_users_for_service,
    mock_accept_invite,
    mock_add_user_to_service,
    mocker
):
    sample_invite['email_address'] = platform_admin_user['email_address']
    sample_invite['auth_type'] = 'email_auth'
    service_one['permissions'].append('email_auth')

    mocker.patch('app.user_api_client.get_user_by_email', return_value=platform_admin_user)
    mock_update_user_attribute = mocker.patch(
        'app.user_api_client.update_user_attribute',
        return_value=platform_admin_user,
    )

    client_request.login(platform_admin_user)

    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_status=302,
        _expected_redirect=url_for('main.service_dashboard', service_id=service_one['id']),
    )

    mock_update_user_attribute.assert_called_once_with(
        platform_admin_user['id'],
        email_access_validated_at='2021-12-12T12:12:12',
    )
    assert mock_add_user_to_service.called


@freeze_time('2021-12-12 12:12:12')
def test_existing_user_doesnt_get_auth_changed_by_service_without_permission(
    client_request,
    api_user_active,
    service_one,
    sample_invite,
    mock_get_user_by_email,
    mock_no_users_for_service,
    mock_check_invite_token,
    mock_accept_invite,
    mock_update_user_attribute,
    mock_add_user_to_service,
    mocker
):
    sample_invite['email_address'] = api_user_active['email_address']

    assert 'email_auth' not in service_one['permissions']

    sample_invite['auth_type'] = 'email_auth'

    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_status=302,
        _expected_redirect=url_for('main.service_dashboard', service_id=service_one['id']),
    )

    mock_update_user_attribute.assert_called_once_with(
        api_user_active['id'],
        email_access_validated_at='2021-12-12T12:12:12',
    )


@freeze_time('2021-12-12 12:12:12')
def test_existing_email_auth_user_without_phone_cannot_set_sms_auth(
    client_request,
    api_user_active,
    service_one,
    sample_invite,
    mock_no_users_for_service,
    mock_check_invite_token,
    mock_accept_invite,
    mock_update_user_attribute,
    mock_add_user_to_service,
    mocker
):
    sample_invite['email_address'] = api_user_active['email_address']

    service_one['permissions'].append('email_auth')

    api_user_active['auth_type'] = 'email_auth'
    api_user_active['mobile_number'] = None
    sample_invite['auth_type'] = 'sms_auth'

    mocker.patch('app.user_api_client.get_user_by_email', return_value=api_user_active)

    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_status=302,
        _expected_redirect=url_for('main.service_dashboard', service_id=service_one['id']),
    )

    mock_update_user_attribute.assert_called_once_with(
        api_user_active['id'],
        email_access_validated_at='2021-12-12T12:12:12',
    )


@freeze_time('2021-12-12 12:12:12')
def test_existing_email_auth_user_with_phone_can_set_sms_auth(
    client_request,
    api_user_active,
    service_one,
    sample_invite,
    mock_no_users_for_service,
    mock_get_existing_user_by_email,
    mock_check_invite_token,
    mock_accept_invite,
    mock_update_user_attribute,
    mock_add_user_to_service,
    mocker
):
    sample_invite['email_address'] = api_user_active['email_address']
    service_one['permissions'].append('email_auth')
    sample_invite['auth_type'] = 'sms_auth'

    client_request.get(
        'main.accept_invite',
        token='thisisnotarealtoken',
        _expected_status=302,
        _expected_redirect=url_for('main.service_dashboard', service_id=service_one['id']),
    )

    mock_get_existing_user_by_email.assert_called_once_with(sample_invite['email_address'])
    assert mock_update_user_attribute.call_args_list == [
        call(api_user_active['id'], email_access_validated_at='2021-12-12T12:12:12'),
        call(api_user_active['id'], auth_type='sms_auth'),
    ]
