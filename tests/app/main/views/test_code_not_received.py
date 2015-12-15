def test_should_render_email_code_not_received_template(notifications_admin):
    response = notifications_admin.test_client().get('/email-not-received')
    assert response.status_code == 200
    assert 'Check your email address is correct and then resend the confirmation code' \
           in response.get_data(as_text=True)


# def test_should_check_and_resend_email_code(notifications_admin, notifications_admin_db, notify_db_session):
#     response = notifications_admin.test_client().post('/email-not-received',
#                                                       data={'email_adddress': 'test@user.gov.uk'})
#     assert response is None


def test_should_render_text_code_not_received_template(notifications_admin):
    response = notifications_admin.test_client().get('/text-not-received')
    assert response.status_code == 200
    assert 'Check your mobile phone number is correct and then resend the confirmation code.' \
           in response.get_data(as_text=True)
