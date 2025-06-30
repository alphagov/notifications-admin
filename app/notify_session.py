from datetime import UTC, datetime, timedelta

from flask import Flask, Request, Response, request
from flask.sessions import SecureCookieSession, SecureCookieSessionInterface
from flask_login import current_user

from app.constants import JSON_UPDATES_BLUEPRINT_NAME, NO_COOKIE_BLUEPRINT_NAME


class NotifyAdminSessionInterface(SecureCookieSessionInterface):
    def _get_inactive_session_expiry(self, app, session_start: datetime):
        """Calculate the inactive expiry timestamp for the session.

        For all users, the session lasts at most 20 hours after logging in.

        For platform admins, the session will also expire after 30 minutes of inactivity (ie no page loads).
        """
        absolute_expiration = session_start + app.permanent_session_lifetime

        if current_user and current_user.platform_admin:
            refresh_duration = timedelta(seconds=app.config["PLATFORM_ADMIN_INACTIVE_SESSION_TIMEOUT"])
        else:
            refresh_duration = app.permanent_session_lifetime

        return min(datetime.now(UTC) + refresh_duration, absolute_expiration)

    def get_expiration_time(self, app: Flask, session: SecureCookieSession) -> datetime | None:
        """Work out the expiry time for the session cookie.

        - For regular users the session remains active for at most 20 hours and effectively never needs to be refreshed.
        - For platform admins, the session remains active for at most 20 hours but expires if not used for 30 minutes.

        WARN: This method powers the Expiry value of the cookie. This tells the browser to delete the cookie after
        that time. If a client is misbehaving, it could still send the cookie back, so we need to do server-side
        processing to validate the expiry time. This is handled by `open_session` below.
        """
        if session.permanent and current_user and "session_expiry" in session:
            return datetime.fromisoformat(session["session_expiry"])

        return super().get_expiration_time(app=app, session=session)

    def open_session(self, app: Flask, request: Request) -> SecureCookieSession | None:
        session = super().open_session(app=app, request=request)

        # If we are beyond the expiry timestamp recorded in the session, return a blank session instead.
        if "session_expiry" in session:
            if datetime.now(UTC) > datetime.fromisoformat(session["session_expiry"]):
                return self.session_class()

        return session

    def save_session(self, app: Flask, session: SecureCookieSession, response: Response) -> None:
        # Catch anyone who is logged-in from before we started tracking session-start times.
        if "user_id" in session:
            now = datetime.now(UTC)
            if "session_start" not in session:
                session["session_start"] = now.isoformat()
            session["session_expiry"] = self._get_inactive_session_expiry(
                app, datetime.fromisoformat(session["session_start"])
            ).isoformat()

        super().save_session(app=app, session=session, response=response)

    def should_set_cookie(self, app, session):
        # Ignore responses from the JSON api endpoints. These power things like the service dashboard or template
        # usage and are passive views. We don't want the session to be refreshed when someone is inactive on an
        # auto-refreshing page. We also don’t want to serve session cookies on letter images (which are on the
        # no_cookie blueprint). We have seen old requests overwrite session data for newer requests in the case
        # of these slow endpoints which are often called in parallel.
        return request.blueprint not in (JSON_UPDATES_BLUEPRINT_NAME, NO_COOKIE_BLUEPRINT_NAME)
