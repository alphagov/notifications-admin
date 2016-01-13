from datetime import datetime
from flask import url_for
from app.main.dao import users_dao
from app.models import User

from .test_sign_in import _set_up_mocker


def test_render_sign_out_redirects_to_sign_in(notifications_admin):
    with notifications_admin.test_request_context():
        response = notifications_admin.test_client().get(
            url_for('main.sign_out'))
        assert response.status_code == 302
        assert response.location == url_for(
            'main.sign_in', _external=True, next=url_for('main.sign_out'))


def test_sign_out_user(notifications_admin,
                       notifications_admin_db,
                       notify_db_session,
                       mocker):
    with notifications_admin.test_request_context():
        _set_up_mocker(mocker)
        email = 'valid@example.gov.uk'
        password = 'val1dPassw0rd!'
        user = User(email_address=email,
                    password=password,
                    mobile_number='+441234123123',
                    name='valid',
                    created_at=datetime.now(),
                    role_id=1,
                    state='active')
        users_dao.insert_user(user)
        with notifications_admin.test_client() as client:
            client.login(user)
            # Check we are logged in
            response = client.get('/123/dashboard')
            assert response.status_code == 200
            response = client.get(url_for('main.sign_out'))
            assert response.status_code == 302
            assert response.location == url_for(
                'main.index', _external=True)
