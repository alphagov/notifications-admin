import os
import pathlib
from functools import partial
from time import monotonic

import jinja2
from flask import (
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
from flask.globals import _lookup_req_object, _request_ctx_stack
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from gds_metrics import GDSMetrics
from govuk_frontend_jinja.flask_ext import init_govuk_frontend
from itsdangerous import BadSignature
from notifications_python_client.errors import HTTPError
from notifications_utils import logging, request_helper
from notifications_utils.formatters import formatted_list, normalise_lines
from notifications_utils.recipients import format_phone_number_human_readable
from notifications_utils.sanitise_text import SanitiseASCII
from werkzeug.exceptions import HTTPException as WerkzeugHTTPException
from werkzeug.exceptions import abort
from werkzeug.local import LocalProxy

from app import proxy_fix, webauthn_server
from app.asset_fingerprinter import asset_fingerprinter
from app.config import configs
from app.extensions import antivirus_client, redis_client, zendesk_client
from app.formatters import (
    convert_to_boolean,
    format_billions,
    format_date,
    format_date_human,
    format_date_normal,
    format_date_numeric,
    format_date_short,
    format_datetime,
    format_datetime_24h,
    format_datetime_human,
    format_datetime_normal,
    format_datetime_relative,
    format_datetime_short,
    format_day_of_week,
    format_delta,
    format_delta_days,
    format_list_items,
    format_mobile_network,
    format_notification_status,
    format_notification_status_as_field_status,
    format_notification_status_as_time,
    format_notification_status_as_url,
    format_notification_type,
    format_number_in_pounds_as_currency,
    format_thousands,
    format_time,
    format_yes_no,
    id_safe,
    iteration_count,
    linkable_name,
    message_count,
    message_count_label,
    message_count_noun,
    nl2br,
    recipient_count,
    recipient_count_label,
    round_to_significant_figures,
    valid_phone_number,
)
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
from app.notify_client.broadcast_message_api_client import (
    broadcast_message_api_client,
)
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
from app.notify_client.performance_dashboard_api_client import (
    performance_dashboard_api_client,
)
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
from app.utils import get_logo_cdn_domain

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
    notify_environment = os.environ['NOTIFY_ENVIRONMENT']

    application.config.from_object(configs[notify_environment])
    asset_fingerprinter._asset_root = application.config['ASSET_PATH']

    init_app(application)

    init_govuk_frontend(application)
    init_jinja(application)

    for client in (
        # Gubbins
        # Note, metrics purposefully first so we start measuring response times as early as possible before any
        # other `app.before_request` handlers (introduced by any of these clients) are processed (which would
        # otherwise mean we aren't measuring the full response time)
        metrics,
        csrf,
        login_manager,
        proxy_fix,
        request_helper,

        # API clients
        api_key_api_client,
        billing_api_client,
        broadcast_message_api_client,
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
        performance_dashboard_api_client,
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
    webauthn_server.init_app(application)

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

    font_paths = [
        str(item)[len(asset_fingerprinter._filesystem_path):]
        for item in pathlib.Path(asset_fingerprinter._filesystem_path).glob('fonts/*.woff2')
    ]

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
            'asset_url': asset_fingerprinter.get_url,
            'font_paths': font_paths,
        }

    application.url_map.converters['uuid'].to_python = lambda self, value: value
    application.url_map.converters['template_type'] = TemplateTypeConverter
    application.url_map.converters['ticket_type'] = TicketTypeConverter
    application.url_map.converters['letter_file_extension'] = LetterFileExtensionConverter
    application.url_map.converters['simple_date'] = SimpleDateTypeConverter


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
        "img-src 'self' {asset_domain} *.tile.openstreetmap.org *.google-analytics.com"
        " *.notifications.service.gov.uk {logo_domain} data:;"
        "frame-src 'self' www.youtube-nocookie.com;".format(
            asset_domain=current_app.config['ASSET_DOMAIN'],
            logo_domain=get_logo_cdn_domain(),
        )
    ))
    response.headers.add('Link', (
        '<{asset_url}>; rel=dns-prefetch, <{asset_url}>; rel=preconnect'.format(
            asset_url=f'https://{current_app.config["ASSET_DOMAIN"]}'
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
    from app.main import main as main_blueprint
    from app.main import no_cookie as no_cookie_blueprint
    from app.status import status as status_blueprint

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
        format_billions,
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
        format_number_in_pounds_as_currency,
        formatted_list,
        normalise_lines,
        nl2br,
        format_phone_number_human_readable,
        format_thousands,
        id_safe,
        convert_to_boolean,
        format_list_items,
        iteration_count,
        recipient_count,
        recipient_count_label,
        round_to_significant_figures,
        message_count_label,
        message_count,
        message_count_noun,
        format_mobile_network,
        format_yes_no,
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
