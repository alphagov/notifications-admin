import os
import re
import urllib
from datetime import datetime, timedelta, timezone
from functools import partial
from time import monotonic

import humanize
import jinja2
from flask import (
    Markup,
    current_app,
    flash,
    g,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask._compat import string_types
from flask.globals import _lookup_req_object, _request_ctx_stack
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from gds_metrics import GDSMetrics
from govuk_frontend_jinja.flask_ext import init_govuk_frontend
from itsdangerous import BadSignature
from notifications_python_client.errors import HTTPError
from notifications_utils import formatters, logging, request_helper
from notifications_utils.field import Field
from notifications_utils.recipients import (
    InvalidPhoneError,
    format_phone_number_human_readable,
    validate_phone_number,
)
from notifications_utils.sanitise_text import SanitiseASCII
from notifications_utils.take import Take
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime
from werkzeug.exceptions import HTTPException as WerkzeugHTTPException
from werkzeug.exceptions import abort
from werkzeug.local import LocalProxy

from app import proxy_fix
from app.asset_fingerprinter import asset_fingerprinter
from app.commands import setup_commands
from app.config import configs
from app.extensions import antivirus_client, redis_client, zendesk_client
from app.models.organisation import Organisation
from app.models.service import Service
from app.models.user import AnonymousUser, User
from app.navigation import (
    CaseworkNavigation,
    HeaderNavigation,
    MainNavigation,
    OrgNavigation,
)
from app.notify_client import InviteTokenError
from app.notify_client.api_key_api_client import api_key_api_client
from app.notify_client.billing_api_client import billing_api_client
from app.notify_client.complaint_api_client import complaint_api_client
from app.notify_client.contact_list_api_client import contact_list_api_client
from app.notify_client.email_branding_client import email_branding_client
from app.notify_client.events_api_client import events_api_client
from app.notify_client.inbound_number_client import inbound_number_client
from app.notify_client.invite_api_client import invite_api_client
from app.notify_client.job_api_client import job_api_client
from app.notify_client.letter_branding_client import letter_branding_client
from app.notify_client.letter_jobs_client import letter_jobs_client
from app.notify_client.notification_api_client import notification_api_client
from app.notify_client.org_invite_api_client import org_invite_api_client
from app.notify_client.organisations_api_client import organisations_client
from app.notify_client.platform_stats_api_client import (
    platform_stats_api_client,
)
from app.notify_client.provider_client import provider_client
from app.notify_client.service_api_client import service_api_client
from app.notify_client.status_api_client import status_api_client
from app.notify_client.template_folder_api_client import (
    template_folder_api_client,
)
from app.notify_client.template_statistics_api_client import (
    template_statistics_client,
)
from app.notify_client.upload_api_client import upload_api_client
from app.notify_client.user_api_client import user_api_client
from app.url_converters import (
    LetterFileExtensionConverter,
    SimpleDateTypeConverter,
    TemplateTypeConverter,
    TicketTypeConverter,
)
from app.utils import format_thousands, get_logo_cdn_domain, id_safe

login_manager = LoginManager()
csrf = CSRFProtect()
metrics = GDSMetrics()


# The current service attached to the request stack.
def _get_current_service():
    return _lookup_req_object('service')


current_service = LocalProxy(_get_current_service)

# The current organisation attached to the request stack.
current_organisation = LocalProxy(partial(_lookup_req_object, 'organisation'))

navigation = {
    'casework_navigation': CaseworkNavigation(),
    'main_navigation': MainNavigation(),
    'header_navigation': HeaderNavigation(),
    'org_navigation': OrgNavigation(),
}


def create_app(application):
    setup_commands(application)

    notify_environment = os.environ['NOTIFY_ENVIRONMENT']

    application.config.from_object(configs[notify_environment])
    asset_fingerprinter._asset_root = application.config['ASSET_PATH']

    init_app(application)

    init_govuk_frontend(application)
    init_jinja(application)

    for client in (

        # Gubbins
        csrf,
        login_manager,
        metrics,
        proxy_fix,
        request_helper,

        # API clients
        api_key_api_client,
        billing_api_client,
        contact_list_api_client,
        complaint_api_client,
        email_branding_client,
        events_api_client,
        inbound_number_client,
        invite_api_client,
        job_api_client,
        letter_branding_client,
        letter_jobs_client,
        notification_api_client,
        org_invite_api_client,
        organisations_client,
        platform_stats_api_client,
        provider_client,
        service_api_client,
        status_api_client,
        template_folder_api_client,
        template_statistics_client,
        upload_api_client,
        user_api_client,

        # External API clients
        antivirus_client,
        redis_client,
        zendesk_client,

    ):
        client.init_app(application)

    logging.init_app(application)

    login_manager.login_view = 'main.sign_in'
    login_manager.login_message_category = 'default'
    login_manager.session_protection = None
    login_manager.anonymous_user = AnonymousUser

    # make sure we handle unicode correctly
    redis_client.redis_store.decode_responses = True

    setup_blueprints(application)

    add_template_filters(application)

    register_errorhandlers(application)

    setup_event_handlers()


def init_app(application):
    application.after_request(useful_headers_after_request)

    application.before_request(load_service_before_request)
    application.before_request(load_organisation_before_request)
    application.before_request(request_helper.check_proxy_header_before_request)

    @application.context_processor
    def _attach_current_service():
        return {'current_service': current_service}

    @application.context_processor
    def _attach_current_organisation():
        return {'current_org': current_organisation}

    @application.context_processor
    def _attach_current_user():
        return {'current_user': current_user}

    @application.context_processor
    def _nav_selected():
        return navigation

    @application.before_request
    def record_start_time():
        g.start = monotonic()
        g.endpoint = request.endpoint

    @application.context_processor
    def inject_global_template_variables():
        return {
            'asset_path': application.config['ASSET_PATH'],
            'header_colour': application.config['HEADER_COLOUR'],
            'asset_url': asset_fingerprinter.get_url
        }

    application.url_map.converters['uuid'].to_python = lambda self, value: value
    application.url_map.converters['template_type'] = TemplateTypeConverter
    application.url_map.converters['ticket_type'] = TicketTypeConverter
    application.url_map.converters['letter_file_extension'] = LetterFileExtensionConverter
    application.url_map.converters['simple_date'] = SimpleDateTypeConverter


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
    return utc_string_to_aware_gmt_datetime(date).strftime('%Y-%m-%d')


def format_time_24h(date):
    return utc_string_to_aware_gmt_datetime(date).strftime('%H:%M')


def get_human_day(time, date_prefix=''):

    #  Add 1 minute to transform 00:00 into ‘midnight today’ instead of ‘midnight tomorrow’
    date = (utc_string_to_aware_gmt_datetime(time) - timedelta(minutes=1)).date()
    now = datetime.utcnow()

    if date == (now + timedelta(days=1)).date():
        return 'tomorrow'
    if date == now.date():
        return 'today'
    if date == (now - timedelta(days=1)).date():
        return 'yesterday'
    if date.strftime('%Y') != now.strftime('%Y'):
        return '{} {} {}'.format(
            date_prefix,
            _format_datetime_short(date),
            date.strftime('%Y'),
        ).strip()
    return '{} {}'.format(
        date_prefix,
        _format_datetime_short(date),
    ).strip()


def format_time(date):
    return {
        '12:00AM': 'Midnight',
        '12:00PM': 'Midday'
    }.get(
        utc_string_to_aware_gmt_datetime(date).strftime('%-I:%M%p'),
        utc_string_to_aware_gmt_datetime(date).strftime('%-I:%M%p')
    ).lower()


def format_date(date):
    return utc_string_to_aware_gmt_datetime(date).strftime('%A %d %B %Y')


def format_date_normal(date):
    return utc_string_to_aware_gmt_datetime(date).strftime('%d %B %Y').lstrip('0')


def format_date_short(date):
    return _format_datetime_short(utc_string_to_aware_gmt_datetime(date))


def format_date_human(date):
    return get_human_day(date)


def format_datetime_human(date, date_prefix=''):
    return '{} at {}'.format(
        get_human_day(date, date_prefix='on'),
        format_time(date),
    )


def format_day_of_week(date):
    return utc_string_to_aware_gmt_datetime(date).strftime('%A')


def _format_datetime_short(datetime):
    return datetime.strftime('%d %B').lstrip('0')


def naturaltime_without_indefinite_article(date):
    return re.sub(
        'an? (.*) ago',
        lambda match: '1 {} ago'.format(match.group(1)),
        humanize.naturaltime(date),
    )


def format_delta(date):
    delta = (
        datetime.now(timezone.utc)
    ) - (
        utc_string_to_aware_gmt_datetime(date)
    )
    if delta < timedelta(seconds=30):
        return "just now"
    if delta < timedelta(seconds=60):
        return "in the last minute"
    return naturaltime_without_indefinite_article(delta)


def format_delta_days(date):
    now = datetime.now(timezone.utc)
    date = utc_string_to_aware_gmt_datetime(date)
    if date.strftime('%Y-%m-%d') == now.strftime('%Y-%m-%d'):
        return "today"
    if date.strftime('%Y-%m-%d') == (now - timedelta(days=1)).strftime('%Y-%m-%d'):
        return "yesterday"
    return naturaltime_without_indefinite_article(now - date)


def valid_phone_number(phone_number):
    try:
        validate_phone_number(phone_number)
        return True
    except InvalidPhoneError:
        return False


def format_notification_type(notification_type):
    return {
        'email': 'Email',
        'sms': 'SMS',
        'letter': 'Letter'
    }[notification_type]


def format_notification_status(status, template_type):
    return {
        'email': {
            'failed': 'Failed',
            'technical-failure': 'Technical failure',
            'temporary-failure': 'Inbox not accepting messages right now',
            'permanent-failure': 'Email address does not exist',
            'delivered': 'Delivered',
            'sending': 'Sending',
            'created': 'Sending',
            'sent': 'Delivered'
        },
        'sms': {
            'failed': 'Failed',
            'technical-failure': 'Technical failure',
            'temporary-failure': 'Phone not accepting messages right now',
            'permanent-failure': 'Not delivered',
            'delivered': 'Delivered',
            'sending': 'Sending',
            'created': 'Sending',
            'pending': 'Sending',
            'sent': 'Sent internationally'
        },
        'letter': {
            'failed': '',
            'technical-failure': 'Technical failure',
            'temporary-failure': '',
            'permanent-failure': '',
            'delivered': '',
            'received': '',
            'accepted': '',
            'sending': '',
            'created': '',
            'sent': '',
            'pending-virus-check': '',
            'virus-scan-failed': 'Virus detected',
            'returned-letter': '',
            'cancelled': '',
            'validation-failed': 'Validation failed',
        }
    }[template_type].get(status, status)


def format_notification_status_as_time(status, created, updated):
    return dict.fromkeys(
        {'created', 'pending', 'sending'}, ' since {}'.format(created)
    ).get(status, updated)


def format_notification_status_as_field_status(status, notification_type):
    return {
        'letter': {
            'failed': 'error',
            'technical-failure': 'error',
            'temporary-failure': 'error',
            'permanent-failure': 'error',
            'delivered': None,
            'sent': None,
            'sending': None,
            'created': None,
            'accepted': None,
            'pending-virus-check': None,
            'virus-scan-failed': 'error',
            'returned-letter': None,
            'cancelled': 'error',
        }
    }.get(
        notification_type,
        {
            'failed': 'error',
            'technical-failure': 'error',
            'temporary-failure': 'error',
            'permanent-failure': 'error',
            'delivered': None,
            'sent': None,
            'sending': 'default',
            'created': 'default',
            'pending': 'default',
        }
    ).get(status, 'error')


def format_notification_status_as_url(status, notification_type):
    url = partial(url_for, "main.message_status")

    if status not in {
        'technical-failure', 'temporary-failure', 'permanent-failure',
    }:
        return None

    return {
        'email': url(_anchor='email-statuses'),
        'sms': url(_anchor='sms-statuses')
    }.get(notification_type)


def nl2br(value):
    if value:
        return Markup(Take(Field(
            value,
            html='escape',
        )).then(
            formatters.nl2br
        ))
    return ''


@login_manager.user_loader
def load_user(user_id):
    return User.from_id(user_id)


def make_session_permanent():
    """
    Make sessions permanent. By permanent, we mean "admin app sets when it expires". Normally the cookie would expire
    whenever you close the browser. With this, the session expiry is set in `config['PERMANENT_SESSION_LIFETIME']`
    (20 hours) and is refreshed after every request. IE: you will be logged out after twenty hours of inactivity.

    We don't _need_ to set this every request (it's saved within the cookie itself under the `_permanent` flag), only
    when you first log in/sign up/get invited/etc, but we do it just to be safe. For more reading, check here:
    https://stackoverflow.com/questions/34118093/flask-permanent-session-where-to-define-them
    """

    # TODO: Remove this loop after a weekend, when all cookies have either run through this code or expired
    for val in ['user_id', 'remember', 'remember_seconds']:
        if val in session:
            session[f'_{val}'] = session[val]

    session.permanent = True


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
                _request_ctx_stack.top.service = Service(
                    service_api_client.get_service(service_id)['data']
                )
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
            org_id = request.view_args.get('org_id')

            if org_id:
                try:
                    _request_ctx_stack.top.organisation = Organisation.from_id(org_id)
                except HTTPError as exc:
                    # if org id isn't real, then 404 rather than 500ing later because we expect org to be set
                    if exc.status_code == 404:
                        abort(404)
                    else:
                        raise


def save_service_or_org_after_request(response):
    # Only save the current session if the request is 200
    service_id = request.view_args.get('service_id', None) if request.view_args else None
    organisation_id = request.view_args.get('org_id', None) if request.view_args else None
    if response.status_code == 200:
        if service_id:
            session['service_id'] = service_id
            session['organisation_id'] = None
        elif organisation_id:
            session['service_id'] = None
            session['organisation_id'] = organisation_id
    return response


#  https://www.owasp.org/index.php/List_of_useful_HTTP_headers
def useful_headers_after_request(response):
    response.headers.add('X-Frame-Options', 'deny')
    response.headers.add('X-Content-Type-Options', 'nosniff')
    response.headers.add('X-XSS-Protection', '1; mode=block')
    response.headers.add('Content-Security-Policy', (
        "default-src 'self' {asset_domain} 'unsafe-inline';"
        "script-src 'self' {asset_domain} *.google-analytics.com 'unsafe-inline' 'unsafe-eval' data:;"
        "connect-src 'self' *.google-analytics.com;"
        "object-src 'self';"
        "font-src 'self' {asset_domain} data:;"
        "img-src 'self' {asset_domain} *.google-analytics.com *.notifications.service.gov.uk {logo_domain} data:;"
        "frame-src 'self' www.youtube-nocookie.com;".format(
            asset_domain=current_app.config['ASSET_DOMAIN'],
            logo_domain=get_logo_cdn_domain(),
        )
    ))
    if 'Cache-Control' in response.headers:
        del response.headers['Cache-Control']
    response.headers.add(
        'Cache-Control', 'no-store, no-cache, private, must-revalidate')
    for key, value in response.headers:
        response.headers[key] = SanitiseASCII.encode(value)
    return response


def register_errorhandlers(application):  # noqa (C901 too complex)
    def _error_response(error_code, error_page_template=None):
        if error_page_template is None:
            error_page_template = error_code
        resp = make_response(render_template("error/{0}.html".format(error_page_template)), error_code)
        return useful_headers_after_request(resp)

    @application.errorhandler(HTTPError)
    def render_http_error(error):
        application.logger.warning("API {} failed with status {} message {}".format(
            error.response.url if error.response else 'unknown',
            error.status_code,
            error.message
        ))
        error_code = error.status_code
        if error_code not in [401, 404, 403, 410]:
            # probably a 500 or 503.
            # it might be a 400, which we should handle as if it's an internal server error. If the API might
            # legitimately return a 400, we should handle that within the view or the client that calls it.
            application.logger.exception("API {} failed with status {} message {}".format(
                error.response.url if error.response else 'unknown',
                error.status_code,
                error.message
            ))
            error_code = 500
        return _error_response(error_code)

    @application.errorhandler(400)
    def handle_client_error(error):
        # This is tripped if we call `abort(400)`.
        application.logger.exception('Unhandled 400 client error')
        return _error_response(400, error_page_template=500)

    @application.errorhandler(410)
    def handle_gone(error):
        return _error_response(410)

    @application.errorhandler(413)
    def handle_payload_too_large(error):
        return _error_response(413)

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

        return _error_response(400, error_page_template=500)

    @application.errorhandler(405)
    def handle_method_not_allowed(error):
        return _error_response(405, error_page_template=500)

    @application.errorhandler(WerkzeugHTTPException)
    def handle_http_error(error):
        if error.code == 301:
            # PermanentRedirect exception
            return error

        return _error_response(error.code)

    @application.errorhandler(InviteTokenError)
    def handle_bad_invite_token(error):
        flash(str(error))
        return redirect(url_for('main.sign_in'))

    @application.errorhandler(500)
    @application.errorhandler(Exception)
    def handle_bad_request(error):
        current_app.logger.exception(error)
        # We want the Flask in browser stacktrace
        if current_app.config.get('DEBUG', None):
            raise error
        return _error_response(500)


def setup_blueprints(application):
    """
    There are three blueprints: status_blueprint, no_cookie_blueprint, and main_blueprint.

    main_blueprint is the default for everything.

    status_blueprint is only for the status page - unauthenticated, unstyled, no cookies, etc.

    no_cookie_blueprint is for subresources (things loaded asynchronously) that we might be concerned are setting
    cookies unnecessarily and potentially getting in to strange race conditions and overwriting other cookies, as we've
    seen in the send message flow. Currently, this includes letter template previews, and the iframe from the platform
    admin email branding preview pages.

    This notably doesn't include the *.json ajax endpoints. If we included them in this, the cookies wouldn't be
    updated, including the expiration date. If you have a dashboard open and in focus it'll refresh the expiration timer
    every two seconds, and you will never log out, which is behaviour we want to preserve.
    """
    from app.status import status as status_blueprint
    from app.main import (
        main as main_blueprint,
        no_cookie as no_cookie_blueprint
    )

    main_blueprint.before_request(make_session_permanent)
    main_blueprint.after_request(save_service_or_org_after_request)

    application.register_blueprint(main_blueprint)
    # no_cookie_blueprint specifically doesn't have `make_session_permanent` or `save_service_or_org_after_request`
    application.register_blueprint(no_cookie_blueprint)
    application.register_blueprint(status_blueprint)


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
        format_date_human,
        format_date_normal,
        format_date_numeric,
        format_date_short,
        format_datetime_human,
        format_datetime_relative,
        format_day_of_week,
        format_delta,
        format_delta_days,
        format_notification_status,
        format_notification_type,
        format_notification_status_as_time,
        format_notification_status_as_field_status,
        format_notification_status_as_url,
        formatters.formatted_list,
        nl2br,
        format_phone_number_human_readable,
        format_thousands,
        id_safe,
        convert_to_boolean,
    ]:
        application.add_template_filter(fn)


def init_jinja(application):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    template_folders = [
        os.path.join(repo_root, 'app/templates'),
        os.path.join(repo_root, 'app/templates/vendor/govuk-frontend'),
    ]
    jinja_loader = jinja2.FileSystemLoader(template_folders)
    application.jinja_loader = jinja_loader
