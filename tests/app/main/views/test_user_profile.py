import json
from flask import url_for
from notifications_utils.url_safe_token import generate_token


def test_should_show_overview_page(app_,
                                   api_user_active,
                                   mock_login,
                                   mock_get_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.user_profile'))

        assert 'Your profile' in response.get_data(as_text=True)
        assert response.status_code == 200


def test_should_show_name_page(app_,
                               api_user_active,
                               mock_login,
                               mock_get_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.user_profile_name'))

        assert 'Change your name' in response.get_data(as_text=True)
        assert response.status_code == 200


def test_should_redirect_after_name_change(app_,
                                           api_user_active,
                                           mock_login,
                                           mock_update_user,
                                           mock_get_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            new_name = 'New Name'
            data = {'new_name': new_name}
            response = client.post(url_for(
                'main.user_profile_name'), data=data)

        assert response.status_code == 302
        assert response.location == url_for(
            'main.user_profile', _external=True)
        api_user_active.name = new_name
        assert mock_update_user.called


def test_should_show_email_page(app_,
                                api_user_active,
                                mock_login,
                                mock_get_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for(
                'main.user_profile_email'))

        assert 'Change your email address' in response.get_data(as_text=True)
        assert response.status_code == 200


def test_should_redirect_after_email_change(app_,
                                            api_user_active,
                                            mock_login,
                                            mock_is_email_unique):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        data = {'email_address': 'new_notify@notify.gov.uk'}
        response = client.post(
            url_for('main.user_profile_email'),
            data=data)

        assert response.status_code == 302
        assert response.location == url_for(
            'main.user_profile_email_authenticate', _external=True)


def test_should_show_authenticate_after_email_change(app_,
                                                     api_user_active,
                                                     mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        with client.session_transaction() as session:
            session['new-email'] = 'new_notify@notify.gov.uk'
        response = client.get(url_for('main.user_profile_email_authenticate'))

        assert response.status_code == 200
        assert 'Change your email address' in response.get_data(as_text=True)
        assert 'Confirm' in response.get_data(as_text=True)


def test_should_render_change_email_continue_after_authenticate_email(app_,
                                                                      api_user_active,
                                                                      mock_login,
                                                                      mock_verify_password,
                                                                      mock_send_change_email_verification):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        data = {'password': '12345'}
        with client.session_transaction() as session:
            session['new-email'] = 'new_notify@notify.gov.uk'
        response = client.post(
            url_for('main.user_profile_email_authenticate'),
            data=data)
        assert response.status_code == 200
        assert 'Click the link in the email to confirm the change to your email address.' \
               in response.get_data(as_text=True)


def test_should_redirect_to_user_profile_when_user_confirms_email_link(app_,
                                                                       api_user_active,
                                                                       mock_login
                                                                       ):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)

        token = generate_token(payload=json.dumps({'user_id': api_user_active.id, 'email': 'new_email@gov.uk'}),
                               secret=app_.config['SECRET_KEY'], salt=app_.config['DANGEROUS_SALT'])
        response = client.get(url_for('main.user_profile_email_confirm', token=token))

        assert response.status_code == 302
        assert response.location == url_for('main.user_profile', _external=True)


def test_should_show_mobile_number_page(app_,
                                        api_user_active,
                                        mock_login,
                                        mock_get_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        response = client.get(url_for('main.user_profile_mobile_number'))

        assert 'Change your mobile number' in response.get_data(as_text=True)
        assert response.status_code == 200


def test_should_redirect_after_mobile_number_change(app_,
                                                    api_user_active,
                                                    mock_login,
                                                    mock_get_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        data = {'mobile_number': '07121231234'}
        response = client.post(
            url_for('main.user_profile_mobile_number'),
            data=data)
        assert response.status_code == 302
        assert response.location == url_for(
            'main.user_profile_mobile_number_authenticate', _external=True)


def test_should_show_authenticate_after_mobile_number_change(app_,
                                                             api_user_active,
                                                             mock_login,
                                                             mock_get_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        with client.session_transaction() as session:
            session['new-mob'] = '+441234123123'
        response = client.get(
            url_for('main.user_profile_mobile_number_authenticate'))

        assert 'Change your mobile number' in response.get_data(as_text=True)
        assert 'Confirm' in response.get_data(as_text=True)
        assert response.status_code == 200


def test_should_redirect_after_mobile_number_authenticate(app_,
                                                          api_user_active,
                                                          mock_login,
                                                          mock_get_user,
                                                          mock_verify_password,
                                                          mock_send_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        with client.session_transaction() as session:
            session['new-mob'] = '+441234123123'
        data = {'password': '12345667'}
        response = client.post(
            url_for('main.user_profile_mobile_number_authenticate'),
            data=data)

        assert response.status_code == 302
        assert response.location == url_for(
            'main.user_profile_mobile_number_confirm', _external=True)


def test_should_show_confirm_after_mobile_number_change(app_,
                                                        api_user_active,
                                                        mock_login,
                                                        mock_get_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        with client.session_transaction() as session:
            session['new-mob-password-confirmed'] = True
        response = client.get(
            url_for('main.user_profile_mobile_number_confirm'))

        assert 'Change your mobile number' in response.get_data(as_text=True)
        assert 'Confirm' in response.get_data(as_text=True)
        assert response.status_code == 200


def test_should_redirect_after_mobile_number_confirm(app_,
                                                     api_user_active,
                                                     mock_login,
                                                     mock_get_user,
                                                     mock_check_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        with client.session_transaction() as session:
            session['new-mob-password-confirmed'] = True
            session['new-mob'] = '+441234123123'
        data = {'sms_code': '12345'}
        response = client.post(
            url_for('main.user_profile_mobile_number_confirm'),
            data=data)
        assert response.status_code == 302
        assert response.location == url_for(
            'main.user_profile', _external=True)


def test_should_show_password_page(app_,
                                   api_user_active,
                                   mock_login,
                                   mock_get_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        response = client.get(url_for('main.user_profile_password'))

        assert 'Change your password' in response.get_data(as_text=True)
        assert response.status_code == 200


def test_should_redirect_after_password_change(app_,
                                               api_user_active,
                                               mock_login,
                                               mock_get_user,
                                               mock_update_user,
                                               mock_verify_password):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        data = {
            'new_password': 'the new password',
            'old_password': 'the old password'}
        response = client.post(
            url_for('main.user_profile_password'),
            data=data)

        assert response.status_code == 302
        assert response.location == url_for(
            'main.user_profile', _external=True)


def test_non_gov_user_cannot_see_change_email_link(client,
                                                   api_nongov_user_active,
                                                   mock_login,
                                                   mock_get_non_govuser):
    client.login(api_nongov_user_active)
    response = client.get(url_for('main.user_profile'))
    assert '<a href="/user-profile/email">' not in response.get_data(as_text=True)
    assert 'Your profile' in response.get_data(as_text=True)
    assert response.status_code == 200


def test_non_gov_user_cannot_access_change_email_page(client,
                                                      api_nongov_user_active,
                                                      mock_login,
                                                      mock_get_non_govuser):
    client.login(api_nongov_user_active)
    response = client.get(url_for('main.user_profile_email'))
    assert response.status_code == 403
