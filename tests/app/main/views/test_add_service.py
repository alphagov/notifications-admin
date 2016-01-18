from flask import url_for
from app.main.dao import verify_codes_dao, services_dao
from tests.app.main import create_test_user


def test_get_should_render_add_service_template(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
            client.post(url_for('.two_factor'), data={'sms_code': '12345'})
            response = client.get(url_for('.add_service', first='first'))
            assert response.status_code == 200
            assert 'Set up notifications for your service' in response.get_data(as_text=True)


def test_should_add_service_and_redirect_to_next_page(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
            client.post(url_for('.two_factor'), data={'sms_code': '12345'})
            response = client.post(
                url_for('.add_service', first='first'),
                data={'service_name': 'testing the post'}
            )
            assert response.status_code == 302
            assert response.location == url_for('.dashboard', service_id=123, _external=True)
            saved_service = services_dao.find_service_by_service_name('testing the post')
            assert saved_service is not None


def test_should_return_form_errors_when_service_name_is_empty(notifications_admin,
                                                              notifications_admin_db,
                                                              notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
            client.post(url_for('.two_factor'), data={'sms_code': '12345'})
            response = client.post(url_for('.add_service', first='first'), data={})
            assert response.status_code == 200
            assert 'Service name can not be empty' in response.get_data(as_text=True)


def test_should_show_page_for_adding_another_service(notifications_admin,
                                                     notifications_admin_db,
                                                     notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get(url_for('.add_service'))
            assert response.status_code == 200
            assert 'Add a new service' in response.get_data(as_text=True)
