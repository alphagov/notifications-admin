import os
import re
import urllib
import dateutil
import pytz
from flask import (
    Flask,
    session,
    Markup,
    escape,
    render_template,
    make_response,
    current_app,
    request,
    g,
    url_for)

from flask._compat import string_types
from flask.globals import _lookup_req_object
from flask_login import LoginManager
from flask_wtf import CsrfProtect
from functools import partial

from monotonic import monotonic
from notifications_python_client.errors import HTTPError
from notifications_utils import logging
from notifications_utils.recipients import validate_phone_number, InvalidPhoneError
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.javascript import JavascriptLexer
from werkzeug.exceptions import abort
from werkzeug.local import LocalProxy

import app.proxy_fix
from app.asset_fingerprinter import AssetFingerprinter
from app.its_dangerous_session import ItsdangerousSessionInterface
from app.notify_client.service_api_client import ServiceAPIClient
from app.notify_client.api_key_api_client import ApiKeyApiClient
from app.notify_client.invite_api_client import InviteApiClient
from app.notify_client.job_api_client import JobApiClient
from app.notify_client.notification_api_client import NotificationApiClient
from app.notify_client.statistics_api_client import StatisticsApiClient
from app.notify_client.status_api_client import StatusApiClient
from app.notify_client.template_statistics_api_client import TemplateStatisticsApiClient
from app.notify_client.user_api_client import UserApiClient
from app.notify_client.events_api_client import EventsApiClient
from app.notify_client.provider_client import ProviderClient
from app.notify_client.organisations_client import OrganisationsClient

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
events_api_client = EventsApiClient()
provider_client = ProviderClient()
organisations_client = OrganisationsClient()
asset_fingerprinter = AssetFingerprinter()

# The current service attached to the request stack.
current_service = LocalProxy(partial(_lookup_req_object, 'service'))


def create_app():
    from config import configs

    application = Flask(__name__)

    application.config.from_object(configs[os.environ['NOTIFY_ENVIRONMENT']])

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
    events_api_client.init_app(application)
    provider_client.init_app(application)
    organisations_client.init_app(application)

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
    application.add_template_filter(format_datetime_normal)
    application.add_template_filter(format_datetime_short)
    application.add_template_filter(format_time)
    application.add_template_filter(syntax_highlight_json)
    application.add_template_filter(valid_phone_number)
    application.add_template_filter(linkable_name)
    application.add_template_filter(format_date)
    application.add_template_filter(format_date_normal)
    application.add_template_filter(format_date_short)
    application.add_template_filter(format_notification_status)
    application.add_template_filter(format_notification_status_as_field_status)
    application.add_template_filter(format_notification_status_as_url)

    application.after_request(useful_headers_after_request)
    application.after_request(save_service_after_request)
    application.before_request(load_service_before_request)

    def _attach_current_service():
        return {'current_service': current_service}

    application.context_processor(_attach_current_service)
    register_errorhandlers(application)

    setup_event_handlers()

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

    @application.before_request
    def record_start_time():
        g.start = monotonic()

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


def gmt_timezones(date):
    date = dateutil.parser.parse(date)
    forced_utc = date.replace(tzinfo=pytz.utc)
    return forced_utc.astimezone(pytz.timezone('Europe/London'))


def format_datetime(date):
    return gmt_timezones(date).strftime('%A %d %B %Y at %H:%M')


def format_datetime_normal(date):
    return gmt_timezones(date).strftime('%d %B %Y at %H:%M').lstrip('0')


def format_datetime_short(date):
    return gmt_timezones(date).strftime('%d %B at %H:%M').lstrip('0')


def format_time(date):
    return gmt_timezones(date).strftime('%H:%M')


def format_date(date):
    return gmt_timezones(date).strftime('%A %d %B %Y')


def format_date_normal(date):
    return gmt_timezones(date).strftime('%d %B %Y').lstrip('0')


def format_date_short(date):
    return gmt_timezones(date).strftime('%d %B').lstrip('0')


def valid_phone_number(phone_number):
    try:
        validate_phone_number(phone_number)
        return True
    except InvalidPhoneError:
        return False


def format_notification_status(status, template_type):
    return {
        'email': {
            'failed': 'Failed',
            'technical-failure': 'Technical failure',
            'temporary-failure': 'Inbox not accepting messages right now',
            'permanent-failure': 'Email address doesn’t exist',
            'delivered': 'Delivered',
            'sending': 'Sending',
            'created': 'Sending'
        },
        'sms': {
            'failed': 'Failed',
            'technical-failure': 'Technical failure',
            'temporary-failure': 'Phone not accepting messages right now',
            'permanent-failure': 'Phone number doesn’t exist',
            'delivered': 'Delivered',
            'sending': 'Sending',
            'created': 'Sending'
        }
    }.get(template_type).get(status, status)


def format_notification_status_as_field_status(status):
    return {
        'failed': 'error',
        'technical-failure': 'error',
        'temporary-failure': 'error',
        'permanent-failure': 'error',
        'delivered': None,
        'sending': 'default',
        'created': 'default'
    }.get(status, 'error')


def format_notification_status_as_url(status):
    url = partial(url_for, "main.delivery_and_failure")
    return {
        'technical-failure': url(_anchor='technical-failure'),
        'temporary-failure': url(_anchor='not-accepting-messages'),
        'permanent-failure': url(_anchor='does-not-exist')
    }.get(status)


@login_manager.user_loader
def load_user(user_id):
    return user_api_client.get_user(user_id)


def load_service_before_request():
    service_id = request.view_args.get('service_id', session.get('service_id')) if request.view_args \
        else session.get('service_id')
    from flask.globals import _request_ctx_stack
    if _request_ctx_stack.top is not None:
        setattr(
            _request_ctx_stack.top,
            'service',
            service_api_client.get_service(service_id)['data'] if service_id else None)


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
    response.headers.add('Content-Security-Policy', (
        "default-src 'self' 'unsafe-inline';"
        "script-src 'self' *.google-analytics.com 'unsafe-inline' data:;"
        "object-src 'self';"
        "font-src 'self' data:;"
        "img-src 'self' *.google-analytics.com *.notifications.service.gov.uk data:;"
    ))
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
        application.logger.error("API {} failed with status {} message {}".format(
            error.response.url if error.response else 'unknown',
            error.status_code,
            error.message
        ))
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


def setup_event_handlers():
    from flask.ext.login import user_logged_in, user_login_confirmed
    from app.event_handlers import on_user_logged_in, on_user_login_confirmed

    user_logged_in.connect(on_user_logged_in)
    user_login_confirmed.connect(on_user_login_confirmed)
