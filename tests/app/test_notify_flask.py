import datetime

import freezegun
import freezegun.config
import pytest
from flask import Flask, session, url_for

from app import create_app
from tests.conftest import SERVICE_ONE_ID


class TestNotifyAdminSessionInterface:
    @pytest.fixture
    def clean_app(self):
        from tests import TestClient

        app = Flask("app")
        create_app(app)
        app.test_client_class = TestClient
        with app.app_context():
            yield app

    @pytest.fixture
    def clean_app_client(self, clean_app):
        with clean_app.test_request_context(), clean_app.test_client() as client:
            yield client

    def test_logged_user_session_expiration(
        self, request, active_user_with_permissions, mock_get_service, mock_has_permissions, mock_get_notifications
    ):
        app = request.getfixturevalue("clean_app")
        client = request.getfixturevalue("clean_app_client")

        # Set absolute session lifetime to 20 hours
        app.permanent_session_lifetime = datetime.timedelta(hours=20)
        app.config["PERMANENT_SESSION_LIFETIME"] = 20 * 60 * 60

        # Create the session cookie by making a request
        with freezegun.freeze_time("2020-01-01T00:00:00"):
            client.login(active_user_with_permissions)
            response = client.get(url_for("main.api_integration", service_id=SERVICE_ONE_ID))
            assert response.status_code == 200
            assert session["user_id"] == active_user_with_permissions["id"]
            assert "Expires=Wed, 01 Jan 2020 20:00:00 GMT" in response.headers["Set-Cookie"]

        # Move time forward 12 hours; session should still be valid, and expire at the same time
        with freezegun.freeze_time("2020-01-01T12:00:00"):
            response = client.get(url_for("main.api_integration", service_id=SERVICE_ONE_ID))
            assert response.status_code == 200
            assert session["user_id"] == active_user_with_permissions["id"]
            assert "Expires=Wed, 01 Jan 2020 20:00:00 GMT" in response.headers["Set-Cookie"]

        # Move time forward to past session lifetime; session gets invalidated and we get a new one
        with freezegun.freeze_time("2020-01-02T20:00:01"):
            response = client.get(url_for("main.api_integration", service_id=SERVICE_ONE_ID))
            assert response.status_code == 200
            assert "user_id" not in session, "The session should have expired and the user dropped from the session"
            assert (
                "Expires=Fri, 03 Jan 2020 16:00:01 GMT" in response.headers["Set-Cookie"]
            ), "A new anonymous session should be created with a permanent lifetime of 1 hour"

    def test_logged_platform_user_session_full_expiration(
        self, request, platform_admin_user, mock_get_service, mock_has_permissions, mock_get_notifications
    ):
        # webauthn auth needs some more complex mocking/patching not relevant to the code under test, so let's bypass it
        platform_admin_user["auth_type"] = "sms_auth"
        platform_admin_user["can_use_webauthn"] = False

        app = request.getfixturevalue("clean_app")
        client = request.getfixturevalue("clean_app_client")

        # Set absolute session lifetime to 1 hour
        app.permanent_session_lifetime = datetime.timedelta(minutes=60)
        app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60

        # Set platform admin inactive timeout to 30 minutes
        app.config["PLATFORM_ADMIN_INACTIVE_SESSION_TIMEOUT"] = 30 * 60

        # T=00:00. Start a session that will expire 30 minutes later.
        with freezegun.freeze_time("2020-01-01T00:00:00"):
            client.login(platform_admin_user)
            response = client.get(url_for("main.api_integration", service_id=SERVICE_ONE_ID))
            assert response.status_code == 200
            assert session["user_id"] == platform_admin_user["id"]
            assert "Expires=Wed, 01 Jan 2020 00:30:00 GMT" in response.headers["Set-Cookie"]

        # T+00:29; session should still be valid, and expiry updated to 59 minutes after start
        with freezegun.freeze_time("2020-01-01T00:29:00"):
            response = client.get(url_for("main.api_integration", service_id=SERVICE_ONE_ID))
            assert response.status_code == 200
            assert session["user_id"] == platform_admin_user["id"]
            assert "Expires=Wed, 01 Jan 2020 00:59:00 GMT" in response.headers["Set-Cookie"]

        # T+00:59; session still valid but expires in 1 minute - max lifetime
        with freezegun.freeze_time("2020-01-01T00:59:00"):
            response = client.get(url_for("main.api_integration", service_id=SERVICE_ONE_ID))
            assert response.status_code == 200
            assert session["user_id"] == platform_admin_user["id"]
            assert "Expires=Wed, 01 Jan 2020 01:00:00 GMT" in response.headers["Set-Cookie"]

        # T+01:00:01; session expired as past initial lifetime
        with freezegun.freeze_time("2020-01-01T01:00:01"):
            response = client.get(url_for("main.api_integration", service_id=SERVICE_ONE_ID))

            # Ideally this would actually be a 302 redirecting to the login page, but our test client login does
            # a lot of mocking/faking instead of 'real' logins, and so even though the session is cleared the page
            # still actually loads. Let's make assertions about the session instead.
            assert response.status_code == 200
            assert "user_id" not in session, "The session should have expired and the user dropped from the session"
            assert (
                "Expires=Wed, 01 Jan 2020 02:00:01 GMT" in response.headers["Set-Cookie"]
            ), "A new anonymous session should be created with a permanent lifetime of 1 hour"
