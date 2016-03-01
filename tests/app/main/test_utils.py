import pytest
from flask import url_for

from app.utils import user_has_permissions
from app.main.views.index import index
from werkzeug.exceptions import Forbidden


# def test_user_has_permissions(app_,
#                               api_user_active,
#                               mock_get_user,
#                               mock_get_user_by_email,
#                               mock_login):
#     with app_.test_request_context():
#         with app_.test_client() as client:
#             client.login(api_user_active)
#             decorator = user_has_permissions('something')
#             decorated_index = decorator(index)
#             try:
#                 response = decorated_index()
#                 pytest.fail("Failed to throw a forbidden exception")
#             except Forbidden:
#                 pass
