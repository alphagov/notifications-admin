

def test_render_sign_in_returns_sign_in_template(notifications_admin):
    response = notifications_admin.test_client().get('/sign-in')
    assert response.status_code == 200
    assert 'Sign in' in response.get_data(as_text=True)
    assert 'Email address' in response.get_data(as_text=True)
    assert 'Password' in response.get_data(as_text=True)
    assert 'Forgotten password?' in response.get_data(as_text=True)


def test_process_sign_in_return_2fa_template(notifications_admin):
    response = notifications_admin.test_client().post('/sign-in',
                                                      data={'email_address': 'valid@example.gov.uk',
                                                            'password': 'val1dPassw0rd!'})
    assert response.status_code == 302
    assert response.location == 'http://localhost/two-factor'
