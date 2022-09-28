from werkzeug.middleware.proxy_fix import ProxyFix


class CustomProxyFix(object):
    def __init__(self, app, forwarded_proto):
        self.app = ProxyFix(app, x_for=1, x_proto=1, x_host=1, x_port=0, x_prefix=0)
        self.forwarded_proto = forwarded_proto

    def __call__(self, environ, start_response):
        environ.update({"HTTP_X_FORWARDED_PROTO": self.forwarded_proto})
        return self.app(environ, start_response)


def init_app(app):
    app.wsgi_app = CustomProxyFix(app.wsgi_app, app.config.get("HTTP_PROTOCOL", "http"))
