from flask import current_app


def test_should_render_forgot_password(notifications_admin, notifications_admin_db, notify_db_session):
    response = notifications_admin.test_client().get('/forgot-password')
    assert response.status_code == 200
    assert 'If you have forgotten your password, we can send you an email to create a new password.' \
           in response.get_data(as_text=True)


def test_should_return_400_when_email_is_invalid(notifications_admin, notifications_admin_db, notify_db_session):
    response = notifications_admin.test_client().post('/forgot-password',
                                                      data={'email_address': 'not_a_valid_email'})
    x = current_app._get_current_object()
    assert response.status_code == 400
    assert 'Please enter a valid email address' in response.get_data(as_text=True)
