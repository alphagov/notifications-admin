

def test_should_render_two_factor_page(notifications_admin, notifications_admin_db):
    response = notifications_admin.test_client().get('/two-factor')
    assert response.status_code == 200
    assert '''We've sent you a text message with a verification code.''' in response.get_data(as_text=True)


def test_should_login_user_and_redirect_to_dashboard(notifications_admin, notifications_admin_db):
    response = notifications_admin.test_client().post('/two-factor',
                                                      data={'sms_code': '12345'})

    assert response.status_code == 302
    assert response.location == 'http://localhost/dashboard'
