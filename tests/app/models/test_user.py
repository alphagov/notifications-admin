import pytest

from app.models.user import User


def test_user(app_):
    user_data = {'id': 1,
                 'name': 'Test User',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '+4412341234',
                 'state': 'pending',
                 'failed_login_count': 0,
                 'platform_admin': False,
                 }
    user = User(user_data)

    assert user.id == 1
    assert user.name == 'Test User'
    assert user.email_address == 'test@user.gov.uk'
    assert user.mobile_number == '+4412341234'
    assert user.state == 'pending'

    # user has ten failed logins before being locked
    assert user.max_failed_login_count == app_.config['MAX_FAILED_LOGIN_COUNT'] == 10
    assert user.failed_login_count == 0
    assert user.locked is False

    # set failed logins to threshold
    user.failed_login_count = app_.config['MAX_FAILED_LOGIN_COUNT']
    assert user.locked is True

    with pytest.raises(TypeError):
        user.has_permissions('to_do_bad_things')


def test_activate_user(app_, api_user_pending, mock_activate_user):
    assert User(api_user_pending).activate() == User(api_user_pending)
    mock_activate_user.assert_called_once_with(api_user_pending['id'])


def test_activate_user_already_active(app_, api_user_active, mock_activate_user):
    assert User(api_user_active).activate() == User(api_user_active)
    assert mock_activate_user.called is False


@pytest.mark.parametrize('is_platform_admin, value_in_session, expected_result', [
    (True, True, False),
    (True, False, True),
    (True, None, True),
    (False, True, False),
    (False, False, False),
    (False, None, False),
])
def test_platform_admin_flag_set_in_session(client, mocker, is_platform_admin, value_in_session, expected_result):
    session_dict = {}
    if value_in_session is not None:
        session_dict['disable_platform_admin_view'] = value_in_session

    mocker.patch.dict('app.models.user.session', values=session_dict, clear=True)

    assert User({'platform_admin': is_platform_admin}).platform_admin == expected_result
