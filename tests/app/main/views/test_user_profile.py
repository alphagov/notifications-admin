def test_should_show_overview_page(app_, db_, db_session):
    response = app_.test_client().get('/user-profile')

    assert 'Your profile' in response.get_data(as_text=True)
    assert response.status_code == 200


def test_should_show_name_page(app_, db_, db_session):
    response = app_.test_client().get('/user-profile/name')

    assert 'Change your name' in response.get_data(as_text=True)
    assert response.status_code == 200


def test_should_redirect_after_name_change(app_, db_, db_session):
    response = app_.test_client().post('/user-profile/name')

    assert response.status_code == 302
    assert response.location == 'http://localhost/user-profile'


def test_should_show_email_page(app_, db_, db_session):
    response = app_.test_client().get('/user-profile/email')

    assert 'Change your email address' in response.get_data(as_text=True)
    assert response.status_code == 200


def test_should_redirect_after_email_change(app_, db_, db_session):
    response = app_.test_client().post('/user-profile/email')

    assert response.status_code == 302
    assert response.location == 'http://localhost/user-profile/email/authenticate'


def test_should_show_authenticate_after_email_change(app_, db_, db_session):
    response = app_.test_client().get('/user-profile/email/authenticate')

    assert 'Change your email address' in response.get_data(as_text=True)
    assert 'Confirm' in response.get_data(as_text=True)
    assert response.status_code == 200


def test_should_redirect_after_email_change_confirm(app_, db_, db_session):
    response = app_.test_client().post('/user-profile/email/authenticate')

    assert response.status_code == 302
    assert response.location == 'http://localhost/user-profile/email/confirm'


def test_should_show_confirm_after_email_change(app_, db_, db_session):
    response = app_.test_client().get('/user-profile/email/confirm')

    assert 'Change your email address' in response.get_data(as_text=True)
    assert 'Confirm' in response.get_data(as_text=True)
    assert response.status_code == 200


def test_should_redirect_after_email_change_confirm(app_, db_, db_session):
    response = app_.test_client().post('/user-profile/email/confirm')

    assert response.status_code == 302
    assert response.location == 'http://localhost/user-profile'


def test_should_show_mobile_number_page(app_, db_, db_session):
    response = app_.test_client().get('/user-profile/mobile-number')

    assert 'Change your mobile number' in response.get_data(as_text=True)
    assert response.status_code == 200


def test_should_redirect_after_mobile_number_change(app_, db_, db_session):
    response = app_.test_client().post('/user-profile/email')

    assert response.status_code == 302
    assert response.location == 'http://localhost/user-profile/email/authenticate'


def test_should_show_authenticate_after_mobile_number_change(app_, db_, db_session):
    response = app_.test_client().get('/user-profile/mobile-number/authenticate')

    assert 'Change your mobile number' in response.get_data(as_text=True)
    assert 'Confirm' in response.get_data(as_text=True)
    assert response.status_code == 200


def test_should_redirect_after_mobile_number_authenticate(app_, db_, db_session):
    response = app_.test_client().post('/user-profile/mobile-number/authenticate')

    assert response.status_code == 302
    assert response.location == 'http://localhost/user-profile/mobile-number/confirm'


def test_should_show_confirm_after_mobile_number_change(app_, db_, db_session):
    response = app_.test_client().get('/user-profile/mobile-number/confirm')

    assert 'Change your mobile number' in response.get_data(as_text=True)
    assert 'Confirm' in response.get_data(as_text=True)
    assert response.status_code == 200


def test_should_redirect_after_mobile_number_confirm(app_, db_, db_session):
    response = app_.test_client().post('/user-profile/mobile-number/confirm')

    assert response.status_code == 302
    assert response.location == 'http://localhost/user-profile'


def test_should_show_password_page(app_, db_, db_session):
    response = app_.test_client().get('/user-profile/password')

    assert 'Change your password' in response.get_data(as_text=True)
    assert response.status_code == 200


def test_should_redirect_after_password_change(app_, db_, db_session):
    response = app_.test_client().post('/user-profile/password')

    assert response.status_code == 302
    assert response.location == 'http://localhost/user-profile'
