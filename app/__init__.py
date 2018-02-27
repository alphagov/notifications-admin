import os
import urllib
from datetime import datetime, timedelta, timezone
from time import monotonic

import itertools
import ago
from itsdangerous import BadSignature
from flask import (
    session,
    render_template,
    make_response,
    current_app,
    request,
    g,
    url_for,
    flash
)
from flask._compat import string_types
from flask.globals import _lookup_req_object, _request_ctx_stack
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from functools import partial

from notifications_python_client.errors import HTTPError
from notifications_utils import logging, request_helper, formatters
from notifications_utils.clients import DeskproClient
from notifications_utils.clients.statsd.statsd_client import StatsdClient
from notifications_utils.recipients import (
    validate_phone_number,
    InvalidPhoneError,
    format_phone_number_human_readable,
)
from notifications_utils.formatters import formatted_list
from werkzeug.exceptions import abort
from werkzeug.local import LocalProxy

from app import proxy_fix
from app.config import configs
from app.asset_fingerprinter import AssetFingerprinter
from app.notify_client.service_api_client import ServiceAPIClient
from app.notify_client.api_key_api_client import ApiKeyApiClient
from app.notify_client.invite_api_client import InviteApiClient
from app.notify_client.job_api_client import JobApiClient
from app.notify_client.notification_api_client import NotificationApiClient
from app.notify_client.status_api_client import StatusApiClient
from app.notify_client.template_statistics_api_client import TemplateStatisticsApiClient
from app.notify_client.user_api_client import UserApiClient
from app.notify_client.events_api_client import EventsApiClient
from app.notify_client.provider_client import ProviderClient
from app.notify_client.email_branding_client import EmailBrandingClient
from app.notify_client.models import AnonymousUser
from app.notify_client.organisations_api_client import OrganisationsClient
from app.notify_client.org_invite_api_client import OrgInviteApiClient
from app.notify_client.letter_jobs_client import LetterJobsClient
from app.notify_client.inbound_number_client import InboundNumberClient
from app.notify_client.billing_api_client import BillingAPIClient
from app.commands import setup_commands
from app.utils import get_cdn_domain
from app.utils import gmt_timezones

login_manager = LoginManager()
csrf = CSRFProtect()

service_api_client = ServiceAPIClient()
user_api_client = UserApiClient()
api_key_api_client = ApiKeyApiClient()
job_api_client = JobApiClient()
notification_api_client = NotificationApiClient()
status_api_client = StatusApiClient()
invite_api_client = InviteApiClient()
template_statistics_client = TemplateStatisticsApiClient()
events_api_client = EventsApiClient()
provider_client = ProviderClient()
email_branding_client = EmailBrandingClient()
organisations_client = OrganisationsClient()
org_invite_api_client = OrgInviteApiClient()
asset_fingerprinter = AssetFingerprinter()
statsd_client = StatsdClient()
deskpro_client = DeskproClient()
letter_jobs_client = LetterJobsClient()
inbound_number_client = InboundNumberClient()
billing_api_client = BillingAPIClient()

# The current service attached to the request stack.
current_service = LocalProxy(partial(_lookup_req_object, 'service'))

# The current organisation attached to the request stack.
current_organisation = LocalProxy(partial(_lookup_req_object, 'organisation'))


def create_app(application):
    setup_commands(application)

    notify_environment = os.environ['NOTIFY_ENVIRONMENT']

    application.config.from_object(configs[notify_environment])

    init_app(application)
    statsd_client.init_app(application)
    deskpro_client.init_app(application)
    logging.init_app(application, statsd_client)
    csrf.init_app(application)
    request_helper.init_app(application)

    service_api_client.init_app(application)
    user_api_client.init_app(application)
    api_key_api_client.init_app(application)
    job_api_client.init_app(application)
    notification_api_client.init_app(application)
    status_api_client.init_app(application)
    invite_api_client.init_app(application)
    org_invite_api_client.init_app(application)
    template_statistics_client.init_app(application)
    events_api_client.init_app(application)
    provider_client.init_app(application)
    email_branding_client.init_app(application)
    organisations_client.init_app(application)
    letter_jobs_client.init_app(application)
    inbound_number_client.init_app(application)
    billing_api_client.init_app(application)

    login_manager.init_app(application)
    login_manager.login_view = 'main.sign_in'
    login_manager.login_message_category = 'default'
    login_manager.session_protection = None
    login_manager.anonymous_user = AnonymousUser

    from app.main import main as main_blueprint
    application.register_blueprint(main_blueprint)

    from .status import status as status_blueprint
    application.register_blueprint(status_blueprint)

    proxy_fix.init_app(application)

    add_template_filters(application)

    register_errorhandlers(application)

    setup_event_handlers()


def init_app(application):
    application.after_request(useful_headers_after_request)
    application.after_request(save_service_after_request)
    application.before_request(load_service_before_request)
    application.before_request(load_organisation_before_request)
    application.before_request(request_helper.check_proxy_header_before_request)

    @application.before_request
    def make_session_permanent():
        # this is dumb. You'd think, given that there's `config['PERMANENT_SESSION_LIFETIME']`, that you'd enable
        # permanent sessions in the config too - but no, you have to declare it for each request.
        # https://stackoverflow.com/questions/34118093/flask-permanent-session-where-to-define-them
        # session.permanent is also, helpfully, a way of saying that the session isn't permanent - in that, it will
        # expire on its own, as opposed to being controlled by the browser's session. Because session is a proxy, it's
        # only accessible from within a request context, so we need to set this before every request :rolls_eyes:
        session.permanent = True

    @application.context_processor
    def _attach_current_service():
        return {'current_service': current_service}

    @application.context_processor
    def _attach_current_organisation():
        return {'current_org': current_organisation}

    @application.context_processor
    def _attach_current_user():
        return{'current_user': current_user}

    @application.before_request
    def record_start_time():
        g.start = monotonic()
        g.endpoint = request.endpoint

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


def linkable_name(value):
    return urllib.parse.quote_plus(value)


def format_datetime(date):
    return '{} at {}'.format(
        format_date(date),
        format_time(date)
    )


def format_datetime_24h(date):
    return '{} at {}'.format(
        format_date(date),
        format_time_24h(date),
    )


def format_datetime_normal(date):
    return '{} at {}'.format(
        format_date_normal(date),
        format_time(date)
    )


def format_datetime_short(date):
    return '{} at {}'.format(
        format_date_short(date),
        format_time(date)
    )


def format_datetime_relative(date):
    return '{} at {}'.format(
        get_human_day(date),
        format_time(date)
    )


def format_datetime_numeric(date):
    return '{} {}'.format(
        format_date_numeric(date),
        format_time_24h(date),
    )


def format_date_numeric(date):
    return gmt_timezones(date).strftime('%Y-%m-%d')


def format_time_24h(date):
    return gmt_timezones(date).strftime('%H:%M')


def get_human_day(time):

    #  Add 1 hour to get ‘midnight today’ instead of ‘midnight tomorrow’
    time_as_day = (gmt_timezones(time) - timedelta(hours=1)).strftime('%A')
    six_days_ago = gmt_timezones((datetime.utcnow() + timedelta(days=-6)).isoformat())

    if gmt_timezones(time) < six_days_ago:
        return format_date_short(time)
    if time_as_day == (datetime.utcnow() + timedelta(days=1)).strftime('%A'):
        return 'tomorrow'
    if time_as_day == datetime.utcnow().strftime('%A'):
        return 'today'
    if time_as_day == (datetime.utcnow() + timedelta(days=-1)).strftime('%A'):
        return 'yesterday'
    return format_date_short(time)


def format_time(date):
    return {
        '12:00AM': 'Midnight',
        '12:00PM': 'Midday'
    }.get(
        gmt_timezones(date).strftime('%-I:%M%p'),
        gmt_timezones(date).strftime('%-I:%M%p')
    ).lower()


def format_date(date):
    return gmt_timezones(date).strftime('%A %d %B %Y')


def format_date_normal(date):
    return gmt_timezones(date).strftime('%d %B %Y').lstrip('0')


def format_date_short(date):
    return gmt_timezones(date).strftime('%d %B').lstrip('0')


def format_delta(date):
    delta = (
        datetime.now(timezone.utc)
    ) - (
        gmt_timezones(date)
    )
    if delta < timedelta(seconds=30):
        return "just now"
    if delta < timedelta(seconds=60):
        return "in the last minute"
    return ago.human(
        delta,
        future_tense='{} from now',  # No-one should ever see this
        past_tense='{} ago',
        precision=1
    )


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
            'created': 'Sending',
            'sent': 'Delivered'
        },
        'sms': {
            'failed': 'Failed',
            'technical-failure': 'Technical failure',
            'temporary-failure': 'Phone not accepting messages right now',
            'permanent-failure': 'Phone number doesn’t exist',
            'delivered': 'Delivered',
            'sending': 'Sending',
            'created': 'Sending',
            'sent': 'Sent internationally'
        },
        'letter': {
            'failed': 'Failed',
            'technical-failure': 'Technical failure',
            'temporary-failure': 'Temporary failure',
            'permanent-failure': 'Permanent failure',
            'delivered': 'Delivered',
            'sending': 'Sending',
            'created': 'Sending',
            'sent': 'Delivered'
        }
    }[template_type].get(status, status)


def format_notification_status_as_time(status, created, updated):
    return {
        'sending': ' since {}'.format(created),
        'created': ' since {}'.format(created)
    }.get(status, updated)


def format_notification_status_as_field_status(status):
    return {
        'failed': 'error',
        'technical-failure': 'error',
        'temporary-failure': 'error',
        'permanent-failure': 'error',
        'delivered': None,
        'sent': None,
        'sending': 'default',
        'created': 'default'
    }.get(status, 'error')


def format_notification_status_as_url(status):
    url = partial(url_for, "main.using_notify")
    return {
        'technical-failure': url(_anchor='technical-failure'),
        'temporary-failure': url(_anchor='not-accepting-messages'),
        'permanent-failure': url(_anchor='does-not-exist')
    }.get(status)


def nl2br(value):
    return formatters.nl2br(value) if value else ''


@login_manager.user_loader
def load_user(user_id):
    return user_api_client.get_user(user_id)


def load_service_before_request():
    if '/static/' in request.url:
        _request_ctx_stack.top.service = None
        return
    if _request_ctx_stack.top is not None:
        _request_ctx_stack.top.service = None

        if request.view_args:
            service_id = request.view_args.get('service_id', session.get('service_id'))
        else:
            service_id = session.get('service_id')

        if service_id:
            try:
                _request_ctx_stack.top.service = service_api_client.get_service(service_id)['data']
            except HTTPError as exc:
                # if service id isn't real, then 404 rather than 500ing later because we expect service to be set
                if exc.status_code == 404:
                    abort(404)
                else:
                    raise


def load_organisation_before_request():
    if '/static/' in request.url:
        _request_ctx_stack.top.organisation = None
        return
    if _request_ctx_stack.top is not None:
        _request_ctx_stack.top.organisation = None

        if request.view_args:
            org_id = request.view_args.get('org_id', session.get('org_id'))
        else:
            org_id = session.get('org_id')

        if org_id:
            try:
                _request_ctx_stack.top.organisation = organisations_client.get_organisation(org_id)
            except HTTPError as exc:
                # if org id isn't real, then 404 rather than 500ing later because we expect org to be set
                if exc.status_code == 404:
                    abort(404)
                else:
                    raise


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
        "script-src 'self' *.google-analytics.com 'unsafe-inline' 'unsafe-eval' data:;"
        "connect-src 'self' *.google-analytics.com;"
        "object-src 'self';"
        "font-src 'self' data:;"
        "img-src 'self' *.google-analytics.com *.notifications.service.gov.uk {} data:;"
        "frame-src www.youtube.com;".format(get_cdn_domain())
    ))
    if 'Cache-Control' in response.headers:
        del response.headers['Cache-Control']
    response.headers.add(
        'Cache-Control', 'no-store, no-cache, private, must-revalidate')
    return response


def register_errorhandlers(application):  # noqa (C901 too complex)
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
        if error_code == 400:
            if isinstance(error.message, str):
                msg = [error.message]
            else:
                msg = list(itertools.chain(*[error.message[x] for x in error.message.keys()]))
            resp = make_response(render_template("error/400.html", message=msg))
            return useful_headers_after_request(resp)
        elif error_code not in [401, 404, 403, 410, 500]:
            error_code = 500
        return _error_response(error_code)

    @application.errorhandler(410)
    def handle_gone(error):
        return _error_response(410)

    @application.errorhandler(404)
    def handle_not_found(error):
        return _error_response(404)

    @application.errorhandler(403)
    def handle_not_authorized(error):
        return _error_response(403)

    @application.errorhandler(401)
    def handle_no_permissions(error):
        return _error_response(401)

    @application.errorhandler(BadSignature)
    def handle_bad_token(error):
        # if someone has a malformed token
        flash('There’s something wrong with the link you’ve used.')
        return _error_response(404)

    @application.errorhandler(CSRFError)
    def handle_csrf(reason):
        application.logger.warning('csrf.error_message: {}'.format(reason))

        if 'user_id' not in session:
            application.logger.warning(
                u'csrf.session_expired: Redirecting user to log in page'
            )

            return application.login_manager.unauthorized()

        application.logger.warning(
            u'csrf.invalid_token: Aborting request, user_id: {user_id}',
            extra={'user_id': session['user_id']})

        resp = make_response(render_template(
            "error/400.html",
            message=['Something went wrong, please go back and try again.']
        ), 400)
        return useful_headers_after_request(resp)

    @application.errorhandler(500)
    @application.errorhandler(Exception)
    def handle_bad_request(error):
        current_app.logger.exception(error)
        # We want the Flask in browser stacktrace
        if current_app.config.get('DEBUG', None):
            raise error
        return _error_response(500)


def setup_event_handlers():
    from flask_login import user_logged_in
    from app.event_handlers import on_user_logged_in

    user_logged_in.connect(on_user_logged_in)


def add_template_filters(application):
    for fn in [
        format_datetime,
        format_datetime_24h,
        format_datetime_normal,
        format_datetime_short,
        format_time,
        valid_phone_number,
        linkable_name,
        format_date,
        format_date_normal,
        format_date_short,
        format_datetime_relative,
        format_delta,
        format_notification_status,
        format_notification_status_as_time,
        format_notification_status_as_field_status,
        format_notification_status_as_url,
        formatted_list,
        nl2br,
        format_phone_number_human_readable,
    ]:
        application.add_template_filter(fn)
