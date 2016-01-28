from datetime import timedelta, datetime

from werkzeug.datastructures import CallbackDict
from flask.sessions import SessionInterface, SessionMixin
from itsdangerous import URLSafeTimedSerializer, BadSignature


class ItsdangerousSession(CallbackDict, SessionMixin):
    def __init__(self, initial=None):
        def on_update(self):
            self.modified = True

        CallbackDict.__init__(self, initial, on_update)
        self.modified = False


class ItsdangerousSessionInterface(SessionInterface):
    session_class = ItsdangerousSession

    def get_serializer(self, app):
        salt = app.config.get('DANGEROUS_SALT')
        if not app.secret_key:
            return None
        return URLSafeTimedSerializer(app.secret_key,
                                      salt=salt)

    def open_session(self, app, request):
        s = self.get_serializer(app)
        if s is None:
            return None
        val = request.cookies.get(app.session_cookie_name)
        if not val:
            return self.session_class()
        max_age = app.permanent_session_lifetime.total_seconds()
        try:
            data = s.loads(val, max_age=max_age)
            return self.session_class(data)
        except BadSignature:
            return self.session_class()

    def save_session(self, app, session, response):
        domain = self.get_cookie_domain(app)
        if not session:
            if session.modified:
                response.delete_cookie(app.session_cookie_name,
                                       domain=domain)
            return
        session.permanent = True
        expires = datetime.utcnow() + timedelta(app.config.get('PERMANENT_SESSION_LIFETIME'))
        val = self.get_serializer(app).dumps(dict(session))
        response.set_cookie(app.session_cookie_name, val,
                            expires=expires, httponly=True,
                            domain=domain, secure=app.config.get('SESSION_COOKIE_SECURE'))
