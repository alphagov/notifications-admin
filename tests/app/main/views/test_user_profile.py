import json
from flask import url_for


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
                                            mock_get_user,
                                            mock_get_user_by_email_not_found):
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
                                                     mock_login,
                                                     mock_get_user,
                                                     mock_verify_password):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        with client.session_transaction() as session:
            session['new-email'] = 'new_notify@notify.gov.uk'
        response = client.get(url_for('main.user_profile_email_authenticate'))

        assert 'Change your email address' in response.get_data(as_text=True)
        assert 'Confirm' in response.get_data(as_text=True)
        assert response.status_code == 200


def test_should_redirect_after_email_change_confirm(app_,
                                                    api_user_active,
                                                    mock_login,
                                                    mock_get_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        data = {'email-code': '12345'}
        with client.session_transaction() as session:
            session['new-email'] = 'new_notify@notify.gov.uk'
        response = client.post(
            url_for('main.user_profile_email_authenticate'),
            data=data)

        assert response.status_code == 302
        assert response.location == url_for(
            'main.user_profile_email_confirm', _external=True)


def test_should_show_confirm_after_email_change(app_,
                                                api_user_active,
                                                mock_login,
                                                mock_get_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        with client.session_transaction() as session:
            session['new-email-password-confirmed'] = True
        response = client.get(url_for('main.user_profile_email_confirm'))

        assert 'Change your email address' in response.get_data(as_text=True)
        assert 'Confirm' in response.get_data(as_text=True)
        assert response.status_code == 200


def test_should_redirect_after_email_change_confirm(app_,
                                                    api_user_active,
                                                    mock_login,
                                                    mock_get_user,
                                                    mock_check_verify_code):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
        with client.session_transaction() as session:
            session['new-email-password-confirmed'] = True
            session['new-email'] = 'new_notify@notify.gov.uk'
        data = {'email_code': '12345'}
        response = client.post(
            url_for('main.user_profile_email_confirm'),
            data=data)

        assert response.status_code == 302
        assert response.location == url_for(
            'main.user_profile', _external=True)


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
                                                          mock_verify_password):
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
        print(response.get_data(as_text=True))
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
            'new_password': '1234567890',
            'old_password': '4567676328'}
        response = client.post(
            url_for('main.user_profile_password'),
            data=data)

        print(response.get_data(as_text=True))
        assert response.status_code == 302
        assert response.location == url_for(
            'main.user_profile', _external=True)
