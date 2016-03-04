import pytest
from flask import url_for

from app.utils import user_has_permissions, validate_header_row, validate_recipient, InvalidHeaderError
from app.main.views.index import index
from werkzeug.exceptions import Forbidden


def test_user_has_permissions_on_endpoint_fail(app_,
                                               api_user_active,
                                               mock_login,
                                               mock_get_user_with_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            decorator = user_has_permissions('something')
            decorated_index = decorator(index)
            try:
                response = decorated_index()
                pytest.fail("Failed to throw a forbidden exception")
            except Forbidden:
                pass


def test_user_has_permissions_success(app_,
                                      api_user_active,
                                      mock_login,
                                      mock_get_user_with_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            decorator = user_has_permissions('manage_users')
            decorated_index = decorator(index)
            response = decorated_index()


def test_user_has_permissions_or(app_,
                                 api_user_active,
                                 mock_login,
                                 mock_get_user_with_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            decorator = user_has_permissions('something', 'manage_users', or_=True)
            decorated_index = decorator(index)
            response = decorated_index()


def test_user_has_permissions_multiple(app_,
                                       api_user_active,
                                       mock_login,
                                       mock_get_user_with_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            decorator = user_has_permissions('manage_templates', 'manage_users')
            decorated_index = decorator(index)
            response = decorated_index()


def test_validate_header_row():
    row = {'bad': '+44 7700 900981'}
    try:
        validate_header_row(row, 'sms')
    except InvalidHeaderError as e:
        assert e.message == 'Invalid header name, should be phone number'
