from flask import url_for, session
from unittest.mock import ANY
import app
from app.utils import user_in_whitelist
from tests.conftest import api_user_active as create_active_user


def test_get_should_render_add_service_template(app_,
                                                api_user_active,
                                                mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active, mocker)
            response = client.get(url_for('main.add_service'))
            assert response.status_code == 200
            assert 'Which service do you want to set up notifications for?' in response.get_data(as_text=True)


def test_should_add_service_and_redirect_to_tour_when_no_services(app_,
                                                                  mocker,
                                                                  mock_create_service,
                                                                  mock_create_service_template,
                                                                  mock_get_services_with_no_services,
                                                                  api_user_active):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active, mocker)
            response = client.post(
                url_for('main.add_service'),
                data={'name': 'testing the post'})
            assert mock_get_services_with_no_services.called
            mock_create_service.assert_called_once_with(
                service_name='testing the post',
                active=False,
                message_limit=app_.config['DEFAULT_SERVICE_LIMIT'],
                restricted=True,
                user_id=api_user_active.id,
                email_from='testing.the.post'
            )
            assert len(mock_create_service_template.call_args_list) == 1
            assert session['service_id'] == 101
            assert response.status_code == 302
            assert response.location == url_for(
                'main.send_test',
                service_id=101,
                template_id="Example text message template",
                help=1,
                _external=True
            )


def test_should_add_service_and_redirect_to_dashboard_when_existing_service(app_,
                                                                            mocker,
                                                                            mock_create_service,
                                                                            mock_create_service_template,
                                                                            mock_get_services,
                                                                            api_user_active):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active, mocker)
            response = client.post(
                url_for('main.add_service'),
                data={'name': 'testing the post'})
            assert mock_get_services.called
            mock_create_service.assert_called_once_with(
                service_name='testing the post',
                active=False,
                message_limit=app_.config['DEFAULT_SERVICE_LIMIT'],
                restricted=True,
                user_id=api_user_active.id,
                email_from='testing.the.post'
            )
            assert len(mock_create_service_template.call_args_list) == 0
            assert session['service_id'] == 101
            assert response.status_code == 302
            assert response.location == url_for('main.service_dashboard', service_id=101, _external=True)


def test_should_return_form_errors_when_service_name_is_empty(app_,
                                                              mocker,
                                                              api_user_active):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active, mocker)
            response = client.post(url_for('main.add_service'), data={})
            assert response.status_code == 200
            assert 'Can’t be empty' in response.get_data(as_text=True)


def test_should_return_form_errors_with_duplicate_service_name_regardless_of_case(app_,
                                                                                  mocker,
                                                                                  service_one,
                                                                                  api_user_active,
                                                                                  mock_create_service):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active, mocker, service_one)
            mocker.patch('app.service_api_client.find_all_service_email_from',
                         return_value=['service_one', 'service.two'])
            response = client.post(url_for('main.add_service'), data={'name': 'SERVICE TWO'})

            assert response.status_code == 200
            assert 'This service name is already in use' in response.get_data(as_text=True)
            app.service_api_client.find_all_service_email_from.assert_called_once_with()
            assert not mock_create_service.called


def test_non_whitelist_user_cannot_add_service(app_, mocker, client, fake_uuid):
    non_whitelist_user = create_active_user(fake_uuid, 'someuser@notonwhitelist.com')
    client.login(non_whitelist_user, mocker)
    assert not user_in_whitelist(non_whitelist_user.email_address)
    response = client.get(url_for('main.add_service'))
    assert response.status_code == 403
