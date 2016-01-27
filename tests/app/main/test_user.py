from app.notify_client.user_api_client import User


def test_user():
    user_data = {'id': 1,
                 'name': 'Test User',
                 'email_address': 'test@user.gov.uk',
                 'mobile_number': '+4412341234',
                 'state': 'pending',
                 'failed_login_count': 0
                 }
    user = User(user_data)

    assert user.id == 1
    assert user.name == 'Test User'
    assert user.email_address == 'test@user.gov.uk'
    assert user.mobile_number == '+4412341234'
    assert user.state == 'pending'

    # user has three failed logins before being locked
    assert user.max_failed_login_count == 3
    assert user.failed_login_count == 0
    assert not user.is_locked()

    # set failed logins to threshold
    user.failed_login_count = 3
    assert user.is_locked()
