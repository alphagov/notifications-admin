from flask.testing import FlaskClient
from flask import url_for
from app.models import User
from app.main.dao import (users_dao, verify_codes_dao)


class TestClient(FlaskClient):
    def login(self, user):
        # Skipping authentication here and just log them in
        with self.session_transaction() as session:
            session['user_email'] = user.email_address
        verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
        response = self.post(
            url_for('main.two_factor'), data={'sms_code': '12345'})
        assert response.status_code == 302

    def logout(self, user):
        self.get(url_for("main.logout"))


def service_json(id_, name, users, limit=1000, active=False, restricted=True):
    return {
        'id': id_,
        'name': name,
        'users': users,
        'limit': limit,
        'active': active,
        'restricted': restricted
    }


def template_json(id_, name, type_, content, service_id):
    return {
        'id': id_,
        'name': name,
        'template_type': type_,
        'content': content,
        'service': service_id
    }


TEST_USER_EMAIL = 'test@user.gov.uk'


def create_test_user(state):
    user = User(name='Test User',
                password='somepassword',
                email_address=TEST_USER_EMAIL,
                mobile_number='+441234123412',
                role_id=1,
                state=state)
    users_dao.insert_user(user)
    return user


def create_another_test_user(state):
    user = User(name='Another Test User',
                password='someOtherpassword',
                email_address='another_test@user.gov.uk',
                mobile_number='+442233123412',
                role_id=1,
                state=state)
    users_dao.insert_user(user)
    return user


def get_test_user():
    return users_dao.get_user_by_email(TEST_USER_EMAIL)
