from app.main.encryption import hashpw


def test_should_return_verify_template(notifications_admin, notifications_admin_db):
    response = notifications_admin.test_client().get('/verify')

    assert response.status_code == 200
    assert 'Activate your account' in response.get_data(as_text=True)


def test_should_redirect_to_add_service_when_code_are_correct(notifications_admin, notifications_admin_db):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            session['sms_code'] = hashpw('12345')
            session['email_code'] = hashpw('23456')
        response = client.post('/verify',
                               data={'sms_code': '12345',
                                     'email_code': '23456'})
        assert response.status_code == 302
        assert response.location == 'http://localhost/add-service'


def test_should_return_400_when_sms_code_is_wrong(notifications_admin, notifications_admin_db):
     with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            session['sms_code'] = hashpw('12345')
            session['email_code'] = hashpw('23456')
        response = client.post('/verify',
                               data={'sms_code': '98765',
                                     'email_code': '23456'})
        assert response.status_code == 400
        assert 'sms_code' in response.get_data(as_text=True)
