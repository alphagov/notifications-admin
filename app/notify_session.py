import typing
from datetime import datetime, timedelta, timezone

from flask import Flask, Request, Response
from flask.sessions import SecureCookieSession, SecureCookieSessionInterface
from flask_login import current_user


class NotifyAdminSessionInterface(SecureCookieSessionInterface):
    def get_inactive_session_expiry(self, app, session_start: datetime):
        """Calculate the inactive expiry timestamp for the session.

        For all users, the session lasts at most 20 hours after logging in.

        For platform admins, the session will also expire after 30 minutes of inactivity (ie no page loads).
        """
        absolute_expiration = session_start + app.permanent_session_lifetime

        if current_user and current_user.platform_admin:
            refresh_duration = timedelta(seconds=app.config["PLATFORM_ADMIN_INACTIVE_SESSION_TIMEOUT"])
        else:
            refresh_duration = app.permanent_session_lifetime

        return min(datetime.now(timezone.utc) + refresh_duration, absolute_expiration)

    def get_expiration_time(self, app: Flask, session: SecureCookieSession) -> typing.Optional[datetime]:
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

    def open_session(self, app: Flask, request: Request) -> typing.Optional[SecureCookieSession]:
        session = super().open_session(app=app, request=request)

        # If we are beyond the expiry timestamp recorded in the session, return a blank session instead.
        if "session_expiry" in session:
            if datetime.now(timezone.utc) > datetime.fromisoformat(session["session_expiry"]):
                return self.session_class()

        return session

    def save_session(self, app: Flask, session: SecureCookieSession, response: Response) -> None:
        # Catch anyone who is logged-in from before we started tracking session-start times.
        # Ignore `application/json` responses. These power things like the service dashboard or template
        # usage and are passive views. We don't want the session to be refreshed when someone is inactive on an
        # auto-refreshing page.
        if "user_id" in session and response.content_type != "application/json":
            now = datetime.now(timezone.utc)
            if "session_start" not in session:
                session["session_start"] = now.isoformat()
            session["session_expiry"] = self.get_inactive_session_expiry(
                app, datetime.fromisoformat(session["session_start"])
            ).isoformat()

        super().save_session(app=app, session=session, response=response)
