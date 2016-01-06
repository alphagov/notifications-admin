def test_should_return_sms_template_picker(notifications_admin):
    response = notifications_admin.test_client().get('/sms/send')

    assert response.status_code == 200
    assert 'Choose text message template' in response.get_data(as_text=True)


def test_should_redirect_to_sms_check_page(notifications_admin):
    response = notifications_admin.test_client().post('/sms/send')

    assert response.status_code == 302
    assert response.location == 'http://localhost/sms/check'


def test_should_return_check_sms_page(notifications_admin):
    response = notifications_admin.test_client().get('/sms/check')

    assert response.status_code == 200
    assert 'Check and confirm' in response.get_data(as_text=True)
    assert 'Send 10 text messages' in response.get_data(as_text=True)


def test_should_redirect_to_job(notifications_admin):
    response = notifications_admin.test_client().post('/sms/check')

    assert response.status_code == 302
    assert response.location == 'http://localhost/jobs/job'
