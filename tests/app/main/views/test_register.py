from flask import url_for

def test_render_register_returns_template_with_form(db_, db_session):
    response = app_.test_client().get('/register')

    assert response.status_code == 200
    assert 'Create an account' in response.get_data(as_text=True)


def test_process_register_creates_new_user(db_,
                                           db_session,
                                           mock_send_sms,
                                           mock_send_email):
    response = app_.test_client().post('/register',
                                       data={'name': 'Some One Valid',
                                             'email_address': 'someone@example.gov.uk',
                                             'mobile_number': '+4407700900460',
                                             'password': 'validPassword!'})
    assert response.status_code == 302
    assert response.location == url_for('main.verify', _external=True)


def test_process_register_returns_400_when_mobile_number_is_invalid(db_,
                                                                    db_session,
                                                                    mock_send_sms,
                                                                    mock_send_email):
    response = app_.test_client().post('/register',
                                       data={'name': 'Bad Mobile',
                                             'email_address': 'bad_mobile@example.gov.uk',
                                             'mobile_number': 'not good',
                                             'password': 'validPassword!'})

    assert response.status_code == 200
    assert 'Must be a UK mobile number (eg 07700 900460)' in response.get_data(as_text=True)


def test_should_return_400_when_email_is_not_gov_uk(db_,
                                                    db_session,
                                                    mock_send_sms,
                                                    mock_send_email):
    response = app_.test_client().post('/register',
                                       data={'name': 'Bad Mobile',
                                             'email_address': 'bad_mobile@example.not.right',
                                             'mobile_number': '+44123412345',
                                             'password': 'validPassword!'})

    assert response.status_code == 200
    assert 'Enter a gov.uk email address' in response.get_data(as_text=True)


def test_should_add_verify_codes_on_session(db_,
                                            db_session,
                                            mock_send_sms,
                                            mock_send_email):
    with app_.test_client() as client:
        response = client.post('/register',
                               data={'name': 'Test Codes',
                                     'email_address': 'test_codes@example.gov.uk',
                                     'mobile_number': '+4407700900460',
                                     'password': 'validPassword!'})
        assert response.status_code == 302
        assert 'notify_admin_session' in response.headers.get('Set-Cookie')


def test_should_return_400_if_password_is_blacklisted(db_, db_session):
    response = app_.test_client().post('/register',
                                       data={'name': 'Bad Mobile',
                                             'email_address': 'bad_mobile@example.not.right',
                                             'mobile_number': '+44123412345',
                                             'password': 'password1234'})

    response.status_code == 200
    assert 'That password is blacklisted, too common' in response.get_data(as_text=True)
