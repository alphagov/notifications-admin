from tests.app.main import create_test_user


def test_should_render_forgot_password(notifications_admin, notifications_admin_db, notify_db_session):
    response = notifications_admin.test_client().get('/forgot-password')
    assert response.status_code == 200
    assert 'If you have forgotten your password, we can send you an email to create a new password.' \
           in response.get_data(as_text=True)


def test_should_redirect_to_password_reset_sent(notifications_admin,
                                                notifications_admin_db,
                                                mocker,
                                                notify_db_session):
    _set_up_mocker(mocker)
    create_test_user('active')
    response = notifications_admin.test_client().post('/forgot-password',
                                                      data={'email_address': 'test@user.gov.uk'})

    assert response.status_code == 200
    assert 'You have been sent an email containing a url to reset your password.' in response.get_data(as_text=True)


def _set_up_mocker(mocker):
    mocker.patch("app.admin_api_client.send_email")
