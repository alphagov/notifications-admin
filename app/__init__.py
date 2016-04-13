import os
import re

import dateutil
import datetime
import urllib
from flask import (
    Flask,
    session,
    Markup,
    escape,
    render_template,
    make_response,
    current_app,
    request)
from flask._compat import string_types
from flask_login import LoginManager
from flask_wtf import CsrfProtect
from notifications_python_client import HTTPError
from pygments import highlight
from pygments.lexers import JavascriptLexer
from pygments.formatters import HtmlFormatter
from werkzeug.exceptions import abort
from babel.dates import format_timedelta

from app.notify_client.api_client import ServiceAPIClient
from app.notify_client.api_key_api_client import ApiKeyApiClient
from app.notify_client.user_api_client import UserApiClient
from app.notify_client.job_api_client import JobApiClient
from app.notify_client.notification_api_client import NotificationApiClient
from app.notify_client.status_api_client import StatusApiClient
from app.notify_client.invite_api_client import InviteApiClient
from app.notify_client.statistics_api_client import StatisticsApiClient
from app.notify_client.template_statistics_api_client import TemplateStatisticsApiClient

from app.its_dangerous_session import ItsdangerousSessionInterface
from app.asset_fingerprinter import AssetFingerprinter
from utils.recipients import validate_phone_number, InvalidPhoneError
import app.proxy_fix
from config import configs
from utils import logging
from werkzeug.local import LocalStack, LocalProxy
from flask.globals import _lookup_req_object
from functools import partial


login_manager = LoginManager()
csrf = CsrfProtect()

service_api_client = ServiceAPIClient()
user_api_client = UserApiClient()
api_key_api_client = ApiKeyApiClient()
job_api_client = JobApiClient()
notification_api_client = NotificationApiClient()
status_api_client = StatusApiClient()
invite_api_client = InviteApiClient()
statistics_api_client = StatisticsApiClient()
template_statistics_client = TemplateStatisticsApiClient()
asset_fingerprinter = AssetFingerprinter()

# The current service attached to the request stack.
current_service = LocalProxy(partial(_lookup_req_object, 'service'))


def create_app():
    application = Flask(__name__)

    application.config.from_object(os.environ['NOTIFY_ADMIN_ENVIRONMENT'])

    init_app(application)
    logging.init_app(application)
    init_csrf(application)

    service_api_client.init_app(application)
    user_api_client.init_app(application)
    api_key_api_client.init_app(application)
    job_api_client.init_app(application)
    notification_api_client.init_app(application)
    status_api_client.init_app(application)
    invite_api_client.init_app(application)
    statistics_api_client.init_app(application)
    template_statistics_client.init_app(application)

    login_manager.init_app(application)
    login_manager.login_view = 'main.sign_in'
    login_manager.login_message_category = 'default'

    from app.main import main as main_blueprint
    application.register_blueprint(main_blueprint)

    from .status import status as status_blueprint
    application.register_blueprint(status_blueprint)

    proxy_fix.init_app(application)

    application.session_interface = ItsdangerousSessionInterface()

    application.add_template_filter(nl2br)
    application.add_template_filter(format_datetime)
    application.add_template_filter(format_time)
    application.add_template_filter(syntax_highlight_json)
    application.add_template_filter(valid_phone_number)
    application.add_template_filter(linkable_name)
    application.add_template_filter(format_date)
    application.add_template_filter(format_delta)

    application.after_request(useful_headers_after_request)
    application.after_request(save_service_after_request)
    application.before_request(load_service_before_request)

    def _attach_current_service():
        return {'current_service': current_service}
    application.context_processor(_attach_current_service)
    register_errorhandlers(application)

    return application


def init_csrf(application):
    csrf.init_app(application)

    @csrf.error_handler
    def csrf_handler(reason):
        if 'user_id' not in session:
            application.logger.info(
                u'csrf.session_expired: Redirecting user to log in page'
            )

            return application.login_manager.unauthorized()

        application.logger.info(
            u'csrf.invalid_token: Aborting request, user_id: {user_id}',
            extra={'user_id': session['user_id']})

        abort(400, reason)


def init_app(application):
    @application.context_processor
    def inject_global_template_variables():
        return {
            'asset_path': '/static/',
            'header_colour': application.config['HEADER_COLOUR'],
            'asset_url': asset_fingerprinter.get_url
        }


def convert_to_boolean(value):
    if isinstance(value, string_types):
        if value.lower() in ['t', 'true', 'on', 'yes', '1']:
            return True
        elif value.lower() in ['f', 'false', 'off', 'no', '0']:
            return False

    return value


def nl2br(value):
    _paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')

    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', Markup('<br>\n'))
                          for p in _paragraph_re.split(escape(value)))
    return Markup(result)


def linkable_name(value):
    return urllib.parse.quote_plus(value)


def syntax_highlight_json(code):
    return Markup(highlight(code, JavascriptLexer(), HtmlFormatter(noclasses=True)))


def format_datetime(date):
    date = dateutil.parser.parse(date)
    native = date.replace(tzinfo=None)
    return native.strftime('%A %d %B %Y at %H:%M')


def format_time(date):
    date = dateutil.parser.parse(date)
    native = date.replace(tzinfo=None)
    return native.strftime('%H:%M')


def format_date(date):
    date = dateutil.parser.parse(date)
    return date.strftime('%A %d %B %Y')


def format_delta(date):
    date = dateutil.parser.parse(date)
    native = date.replace(tzinfo=None)
    difference = native - datetime.datetime.now()
    return format_timedelta(
        datetime.timedelta(seconds=difference.total_seconds()),
        add_direction=True,
        format='short'
    )


def valid_phone_number(phone_number):
    try:
        validate_phone_number(phone_number)
        return True
    except InvalidPhoneError:
        return False


@login_manager.user_loader
def load_user(user_id):
    return user_api_client.get_user(user_id)


def load_service_before_request():
    service_id = request.view_args.get('service_id', None) if request.view_args else None
    if service_id:
        from flask.globals import _request_ctx_stack
        if _request_ctx_stack.top is not None:
            setattr(
                _request_ctx_stack.top,
                'service',
                service_api_client.get_service(service_id)['data'])


def save_service_after_request(response):
    # Only save the current session if the request is 200
    service_id = request.view_args.get('service_id', None) if request.view_args else None
    if response.status_code == 200 and service_id:
        session['service_id'] = service_id
    return response


#  https://www.owasp.org/index.php/List_of_useful_HTTP_headers
def useful_headers_after_request(response):
    response.headers.add('X-Frame-Options', 'deny')
    response.headers.add('X-Content-Type-Options', 'nosniff')
    response.headers.add('X-XSS-Protection', '1; mode=block')
    response.headers.add('Content-Security-Policy',
                         "default-src 'self' 'unsafe-inline'; script-src 'self' *.google-analytics.com 'unsafe-inline' data:; object-src 'self'; font-src 'self' data:; img-src 'self' *.google-analytics.com data:;")  # noqa
    if 'Cache-Control' in response.headers:
        del response.headers['Cache-Control']
    response.headers.add(
        'Cache-Control', 'no-store, no-cache, private, must-revalidate')
    return response


def register_errorhandlers(application):
    def _error_response(error_code):
        resp = make_response(render_template("error/{0}.html".format(error_code)), error_code)
        return useful_headers_after_request(resp)

    @application.errorhandler(HTTPError)
    def render_http_error(error):
        error_code = error.status_code
        if error_code not in [401, 404, 403, 500]:
            error_code = 500
        return _error_response(error_code)

    @application.errorhandler(404)
    def handle_not_found(error):
        return _error_response(404)

    @application.errorhandler(403)
    def handle_not_authorized(error):
        return _error_response(403)

    @application.errorhandler(401)
    def handle_no_permissions(error):
        return _error_response(401)

    @application.errorhandler(500)
    def handle_exception(error):
        if current_app.config.get('DEBUG', None):
            raise error
        return _error_response(500)

    @application.errorhandler(Exception)
    def handle_bad_request(error):
        # We want the Flask in browser stacktrace
        if current_app.config.get('DEBUG', None):
            raise error
        return _error_response(500)
