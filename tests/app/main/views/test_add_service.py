from app.main.dao import verify_codes_dao
from tests.app.main import create_test_user


def test_get_should_render_add_service_template(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
        client.post('/two-factor', data={'sms_code': '12345'})
        response = client.get('/add-service')
        assert response.status_code == 200
        assert 'Set up notifications for your service' in response.get_data(as_text=True)


def test_should_add_service_and_redirect_to_next_page(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_client() as client:
        with client.session_transaction() as session:
            user = create_test_user()
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
        client.post('/two-factor', data={'sms_code': '12345'})
        response = client.post('/add-service', data={'service_name': 'testing the post'})
        assert response.status_code == 302
        assert response.location == 'http://localhost/dashboard'
