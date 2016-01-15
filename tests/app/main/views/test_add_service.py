from flask import url_for
from app.main.dao import verify_codes_dao, services_dao
from tests import create_test_user
from app.models import User


def test_get_should_render_add_service_template(app_, db_, db_session):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
            client.post(url_for('main.two_factor'), data={'sms_code': '12345'})
            response = client.get('/add-service')
            assert response.status_code == 200
            assert 'Set up notifications for your service' in response.get_data(as_text=True)


def test_should_add_service_and_redirect_to_next_page(app_,
                                                      db_,
                                                      db_session,
                                                      mock_create_service,
                                                      mock_get_services):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = User.query.first()
            client.login(user)
            response = client.post(
                url_for('main.add_service'),
                data={'service_name': 'testing the post'})
            assert response.status_code == 302
            assert response.location == url_for('main.dashboard', service_id=123, _external=True)
            assert mock_create_service.called
            assert mock_get_services.called


def test_should_return_form_errors_when_service_name_is_empty(app_,
                                                              db_,
                                                              db_session,
                                                              active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.post('/add-service', data={})
            assert response.status_code == 200
            assert 'Service name can not be empty' in response.get_data(as_text=True)


def test_should_return_form_errors_with_duplicate_service_name(app_,
                                                               db_,
                                                               db_session,
                                                               mock_get_services):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = User.query.first()
            client.login(user)
            response = client.post('/add-service', data={'service_name': 'service_one'})
            assert response.status_code == 200
            assert 'Service name already exists' in response.get_data(as_text=True)
            assert mock_get_services.called
