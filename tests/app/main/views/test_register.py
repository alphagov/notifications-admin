

def test_render_register_returns_template_with_form(notifications_admin, notifications_admin_db, notify_db_session):
    response = notifications_admin.test_client().get('/register')

    assert response.status_code == 200
    assert 'Create an account' in response.get_data(as_text=True)


def test_process_register_creates_new_user(notifications_admin, notifications_admin_db, mocker, notify_db_session):
    _set_up_mocker(mocker)

    response = notifications_admin.test_client().post('/register',
                                                      data={'name': 'Some One Valid',
                                                            'email_address': 'someone@example.gov.uk',
                                                            'mobile_number': '+441231231231',
                                                            'password': 'validPassword!'})
    assert response.status_code == 302
    assert response.location == 'http://localhost/verify'


def test_process_register_returns_400_when_mobile_number_is_invalid(notifications_admin,
                                                                    notifications_admin_db,
                                                                    mocker,
                                                                    notify_db_session):
    _set_up_mocker(mocker)
    response = notifications_admin.test_client().post('/register',
                                                      data={'name': 'Bad Mobile',
                                                            'email_address': 'bad_mobile@example.gov.uk',
                                                            'mobile_number': 'not good',
                                                            'password': 'validPassword!'})

    assert response.status_code == 200
    assert 'Enter a +44 mobile number' in response.get_data(as_text=True)


def test_should_return_400_when_email_is_not_gov_uk(notifications_admin,
                                                    notifications_admin_db,
                                                    mocker,
                                                    notify_db_session):
    _set_up_mocker(mocker)
    response = notifications_admin.test_client().post('/register',
                                                      data={'name': 'Bad Mobile',
                                                            'email_address': 'bad_mobile@example.not.right',
                                                            'mobile_number': '+44123412345',
                                                            'password': 'validPassword!'})

    assert response.status_code == 200
    assert 'Enter a gov.uk email address' in response.get_data(as_text=True)


def test_should_add_verify_codes_on_session(notifications_admin, notifications_admin_db, mocker, notify_db_session):
    _set_up_mocker(mocker)
    with notifications_admin.test_client() as client:
        response = client.post('/register',
                               data={'name': 'Test Codes',
                                     'email_address': 'test_codes@example.gov.uk',
                                     'mobile_number': '+441234567890',
                                     'password': 'validPassword!'})
        assert response.status_code == 302
        assert 'notify_admin_session' in response.headers.get('Set-Cookie')


def _set_up_mocker(mocker):
    mocker.patch("app.admin_api_client.send_sms")
    mocker.patch("app.admin_api_client.send_email")


def test_should_return_400_if_password_is_blacklisted(notifications_admin, notifications_admin_db, notify_db_session):
    response = notifications_admin.test_client().post('/register',
                                                      data={'name': 'Bad Mobile',
                                                            'email_address': 'bad_mobile@example.not.right',
                                                            'mobile_number': '+44123412345',
                                                            'password': 'password1234'})

    response.status_code == 200
    assert 'That password is blacklisted, too common' in response.get_data(as_text=True)
