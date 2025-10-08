import os
import pathlib
import secrets
from collections.abc import Callable
from time import monotonic

import jinja2
import requests
import werkzeug
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
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from gds_metrics import GDSMetrics
from itsdangerous import BadSignature
from notifications_python_client.errors import HTTPError
from notifications_utils import request_helper
from notifications_utils.asset_fingerprinter import asset_fingerprinter
from notifications_utils.eventlet import EventletTimeout
from notifications_utils.formatters import (
    formatted_list,
    get_lines_with_normalised_whitespace,
)
from notifications_utils.logging import flask as utils_logging
from notifications_utils.safe_string import make_string_safe_for_email_local_part, make_string_safe_for_id
from notifications_utils.sanitise_text import SanitiseASCII
from werkzeug.exceptions import HTTPException as WerkzeugHTTPException
from werkzeug.exceptions import abort
from werkzeug.local import LocalProxy

from app.formatters import format_phone_number_human_readable

# must be declared before rest of app is imported to satisfy circular import
# ruff: noqa: E402
memo_resetters: list[Callable] = []

from app import webauthn_server
from app.commands import setup_commands
from app.config import Config, configs
from app.event_handlers import Events
from app.extensions import antivirus_client, redis_client, zendesk_client  # noqa
from app.formatters import (
    convert_to_boolean,
    extract_path_from_url,
    format_auth_type,
    format_billions,
    format_date,
    format_date_human,
    format_date_normal,
    format_date_numeric,
    format_date_short,
    format_datetime,
    format_datetime_human,
    format_datetime_normal,
    format_datetime_numeric,
    format_datetime_relative,
    format_datetime_short,
    format_day_of_week,
    format_delta,
    format_delta_days,
    format_list_items,
    format_notification_status,
    format_notification_status_as_field_status,
    format_notification_status_as_time,
    format_notification_status_as_url,
    format_notification_type,
    format_pennies_as_currency,
    format_pounds_as_currency,
    format_thousands,
    format_time,
    format_yes_no,
    insert_wbr,
    iteration_count,
    message_count,
    message_count_label,
    message_count_noun,
    message_finished_processing_notification,
    nl2br,
    recipient_count,
    recipient_count_label,
    redact_mobile_number,
    sentence_case,
    valid_phone_number,
)
from app.models.organisation import Organisation
from app.models.service import Service
from app.models.user import AnonymousUser, User
from app.notify_client import InviteTokenError
from app.notify_client.api_key_api_client import api_key_api_client  # noqa
from app.notify_client.billing_api_client import billing_api_client  # noqa
from app.notify_client.complaint_api_client import complaint_api_client  # noqa
from app.notify_client.contact_list_api_client import contact_list_api_client  # noqa
from app.notify_client.email_branding_client import email_branding_client  # noqa
from app.notify_client.events_api_client import events_api_client  # noqa
from app.notify_client.inbound_number_client import inbound_number_client  # noqa
from app.notify_client.invite_api_client import invite_api_client  # noqa
from app.notify_client.job_api_client import job_api_client  # noqa
from app.notify_client.letter_attachment_client import letter_attachment_client  # noqa
from app.notify_client.letter_branding_client import letter_branding_client  # noqa
from app.notify_client.letter_jobs_client import letter_jobs_client  # noqa
from app.notify_client.letter_rate_api_client import letter_rate_api_client  # noqa
from app.notify_client.notification_api_client import notification_api_client  # noqa
from app.notify_client.org_invite_api_client import org_invite_api_client  # noqa
from app.notify_client.organisations_api_client import organisations_client  # noqa
from app.notify_client.performance_dashboard_api_client import (
    performance_dashboard_api_client,  # noqa
)
from app.notify_client.platform_admin_api_client import admin_api_client  # noqa
from app.notify_client.protected_sender_id_api_client import protected_sender_id_api_client  # noqa
from app.notify_client.provider_client import provider_client  # noqa
from app.notify_client.report_request_api_client import report_request_api_client  # noqa
from app.notify_client.service_api_client import service_api_client  # noqa
from app.notify_client.sms_rate_client import sms_rate_api_client  # noqa
from app.notify_client.status_api_client import status_api_client  # noqa
from app.notify_client.template_folder_api_client import template_folder_api_client  # noqa
from app.notify_client.template_statistics_api_client import template_statistics_client  # noqa
from app.notify_client.unsubscribe_api_client import unsubscribe_api_client  # noqa
from app.notify_client.upload_api_client import upload_api_client  # noqa
from app.notify_client.user_api_client import user_api_client  # noqa
from app.notify_session import NotifyAdminSessionInterface
from app.overrides_nl.navigation import (
    CaseworkNavigation,
    HeaderNavigation,
    MainNavigation,
    OrgNavigation,
    PlatformAdminNavigation,
)
from app.s3_client.logo_client import logo_client
from app.template_previews import template_preview_client  # noqa
from app.url_converters import (
    AgreementTypeConverter,
    BrandingTypeConverter,
    DailyLimitTypeConverter,
    LetterFileExtensionConverter,
    SimpleDateTypeConverter,
    TemplateTypeConverter,
    TicketTypeConverter,
)
from app.utils import format_provider
from app.utils.user_id import get_user_id_from_flask_login_session

login_manager = LoginManager()
csrf = CSRFProtect()
metrics = GDSMetrics()


current_service = LocalProxy(lambda: g.current_service)

# The current organisation attached to the request stack.
current_organisation = LocalProxy(lambda: g.current_organisation)

navigation = {
    "casework_navigation": CaseworkNavigation(),
    "main_navigation": MainNavigation(),
    "header_navigation": HeaderNavigation(),
    "org_navigation": OrgNavigation(),
    "platform_admin_navigation": PlatformAdminNavigation(),
}


def create_app(application):
    notify_environment = os.environ["NOTIFY_ENVIRONMENT"]

    if notify_environment in configs:
        application.config.from_object(configs[notify_environment])
    else:
        application.config.from_object(Config)

    asset_fingerprinter._asset_root = application.config["ASSET_PATH"]

    init_app(application)

    if "extensions" not in application.jinja_options:
        application.jinja_options["extensions"] = []

    init_jinja(application)

    for client in (
        # Gubbins
        # Note, metrics purposefully first so we start measuring response times as early as possible before any
        # other `app.before_request` handlers (introduced by any of these clients) are processed (which would
        # otherwise mean we aren't measuring the full response time)
        metrics,
        csrf,
        login_manager,
        request_helper,
        # External API clients
        redis_client,
        logo_client,
    ):
        client.init_app(application)

    utils_logging.init_app(application)
    webauthn_server.init_app(application)

    login_manager.login_view = "main.sign_in"
    login_manager.login_message_category = "default"
    login_manager.session_protection = None
    login_manager.anonymous_user = AnonymousUser

    # make sure we handle unicode correctly
    redis_client.redis_store.decode_responses = True

    setup_blueprints(application)

    add_template_filters(application)

    register_errorhandlers(application)

    setup_commands(application)

    setup_event_handlers()


def init_app(application):
    application.after_request(useful_headers_after_request)

    # Load user first (as we want user_id to be available for all calls to API, which service+organisation might make.
    application.before_request(make_nonce_before_request)
    application.before_request(load_user_id_before_request)
    application.before_request(load_service_before_request)
    application.before_request(load_organisation_before_request)

    application.session_interface = NotifyAdminSessionInterface()

    font_paths = [
        str(item)[len(asset_fingerprinter._filesystem_path) :]
        for item in pathlib.Path(asset_fingerprinter._filesystem_path).glob("fonts/*.woff2")
    ]

    @application.context_processor
    def _attach_current_service():
        return {"current_service": current_service}

    @application.context_processor
    def _attach_current_organisation():
        return {"current_org": current_organisation}

    @application.context_processor
    def _attach_current_user():
        return {"current_user": current_user}

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
            "asset_path": application.config["ASSET_PATH"],
            "header_colour": application.config["HEADER_COLOUR"],
            "asset_url": asset_fingerprinter.get_url,
            "font_paths": font_paths,
        }

    application.url_map.converters["uuid"].to_python = lambda self, value: value.lower()
    application.url_map.converters["agreement_type"] = AgreementTypeConverter
    application.url_map.converters["template_type"] = TemplateTypeConverter
    application.url_map.converters["daily_limit_type"] = DailyLimitTypeConverter
    application.url_map.converters["branding_type"] = BrandingTypeConverter
    application.url_map.converters["ticket_type"] = TicketTypeConverter
    application.url_map.converters["letter_file_extension"] = LetterFileExtensionConverter
    application.url_map.converters["simple_date"] = SimpleDateTypeConverter

    # you can specify a default arg in a route decorator, that says "when you hit this route, populate the endpoint with
    # the following kwargs". However, if the `redirect_defaults` flag is set to its default value of true, we also
    # redirect to the first URL for that endpoint if the args match. So it works in reverse, as in, look at the args and
    # find the URL that matches - then returns a 308 PERMANENT REDIRECT to that URL. We don't want that, setting it to
    # false flips the behaviour so we still populate the endpoint args with the default values but don't do any
    # automatic redirects. We only make use of this in our old historical_redirects endpoint
    application.url_map.redirect_defaults = False


def reset_memos():
    """
    Reset all memos registered in memo_resetters
    """
    for resetter in memo_resetters:
        resetter()


@login_manager.user_loader
def load_user(user_id):
    return User.from_id(user_id)


def load_service_before_request():
    g.current_service = None

    if request.path.startswith("/static/"):
        return

    if request.view_args:
        service_id = request.view_args.get("service_id", session.get("service_id"))
    else:
        service_id = session.get("service_id")

    if service_id:
        try:
            g.current_service = Service.from_id(service_id)
        except HTTPError as exc:
            # if service id isn't real, then 404 rather than 500ing later because we expect service to be set
            if exc.status_code == 404:
                abort(404)
            else:
                raise


def load_organisation_before_request():
    g.current_organisation = None

    if request.path.startswith("/static/"):
        return

    if request.view_args:
        org_id = request.view_args.get("org_id")

        if org_id:
            try:
                g.current_organisation = Organisation.from_id(org_id)
            except HTTPError as exc:
                # if org id isn't real, then 404 rather than 500ing later because we expect org to be set
                if exc.status_code == 404:
                    abort(404)
                else:
                    raise


def load_user_id_before_request():
    g.user_id = get_user_id_from_flask_login_session()


def make_nonce_before_request():
    # `govuk_frontend_jinja/template.html` can be extended and inline `<script>` can be added without CSP complaining
    if not getattr(request, "csp_nonce", None):
        request.csp_nonce = secrets.token_urlsafe(16)


#  https://www.owasp.org/index.php/List_of_useful_HTTP_headers
def useful_headers_after_request(response):
    response.headers.add("X-Content-Type-Options", "nosniff")
    response.headers.add("X-XSS-Protection", "1; mode=block")
    response.headers.add(
        "Content-Security-Policy",
        (
            "default-src 'self' {asset_domain} 'unsafe-inline';"
            "script-src 'self' {asset_domain} 'nonce-{csp_nonce}';"
            "connect-src 'self';"
            "object-src 'self';"
            "font-src 'self' {asset_domain} data:;"
            "img-src 'self' {asset_domain}"
            " *.notifications.service.gov.uk {logo_domain} data:;"
            "style-src 'self' {asset_domain} 'unsafe-inline';"
            "frame-ancestors 'self';"
            "frame-src 'self';".format(
                asset_domain=current_app.config["ASSET_DOMAIN"],
                logo_domain=current_app.config["LOGO_CDN_DOMAIN"],
                csp_nonce=getattr(request, "csp_nonce", ""),
            )
        ),
    )
    response.headers.add(
        "Link",
        (
            "<{asset_url}>; rel=dns-prefetch, <{asset_url}>; rel=preconnect".format(
                asset_url=f"https://{current_app.config['ASSET_DOMAIN']}"
            )
        ),
    )
    if "Cache-Control" in response.headers:
        del response.headers["Cache-Control"]
    response.headers.add("Cache-Control", "no-store, no-cache, private, must-revalidate")
    for key, value in response.headers:
        response.headers[key] = SanitiseASCII.encode(value)
    response.headers.add("Strict-Transport-Security", "max-age=31536000; preload")
    response.headers.add("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.add(
        "Cross-Origin-Embedder-Policy",
        "require-corp {asset_domain};".format(asset_domain=current_app.config["ASSET_DOMAIN"]),
    )
    response.headers.add(
        "Cross-Origin-Opener-Policy",
        "same-origin {asset_domain};".format(asset_domain=current_app.config["ASSET_DOMAIN"]),
    )
    response.headers.add(
        "Cross-Origin-Resource-Policy",
        "same-origin {asset_domain};".format(asset_domain=current_app.config["ASSET_DOMAIN"]),
    )
    response.headers.add(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=(), autoplay=(), payment=(), sync-xhr=()",
    )
    response.headers.add("Server", "Cloudfront")
    return response


def register_errorhandlers(application):  # noqa (C901 too complex)
    def _error_response(error_code, error_page_template=None):
        if error_page_template is None:
            error_page_template = error_code
        resp = make_response(render_template(f"error/{error_page_template}.html"), error_code)
        return useful_headers_after_request(resp)

    @application.errorhandler(HTTPError)
    def render_http_error(error):
        application.logger.warning(
            "API %(api)s failed with status=%(status)s, message='%(message)s'",
            {
                "api": error.response.url if isinstance(error.response, requests.Response) else "unknown",
                "status": error.status_code,
                "message": error.message,
            },
        )
        error_code = error.status_code
        if error_code not in [401, 404, 403, 410]:
            # probably a 500 or 503.
            # it might be a 400, which we should handle as if it's an internal server error. If the API might
            # legitimately return a 400, we should handle that within the view or the client that calls it.
            application.logger.exception(
                "API %(api)s failed with status=%(status)s message='%(message)s'",
                {
                    "api": error.response.url if isinstance(error.response, requests.Response) else "unknown",
                    "status": error.status_code,
                    "message": error.message,
                },
            )
            error_code = 500
        return _error_response(error_code)

    @application.errorhandler(400)
    def handle_client_error(error):
        # This is tripped if we call `abort(400)`.
        application.logger.exception("Unhandled 400 client error")
        return _error_response(400, error_page_template=500)

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
        flash("There’s something wrong with the link you’ve used.")
        return _error_response(404)

    @application.errorhandler(CSRFError)
    def handle_csrf(reason):
        application.logger.warning("csrf.error_message: %s", reason)

        if "user_id" not in session:
            application.logger.warning("csrf.session_expired: Redirecting user to log in page")

            try:
                return application.login_manager.unauthorized()
            except werkzeug.exceptions.Unauthorized as e:
                return handle_no_permissions(e)

        application.logger.warning(
            "csrf.invalid_token: Aborting request, user_id: %(user_id)s",
            {"user_id": session["user_id"]},
            extra={"user_id": session["user_id"]},  # include as a distinct field in the log output
        )

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
        return redirect(url_for("main.sign_in"))

    @application.errorhandler(500)
    @application.errorhandler(Exception)
    def handle_bad_request(error):
        current_app.logger.exception(error)
        # We want the Flask in browser stacktrace
        if current_app.config.get("DEBUG", None):
            raise error
        return _error_response(500)

    @application.errorhandler(EventletTimeout)
    def eventlet_timeout(error):
        application.logger.exception(error)
        return _error_response(504, error_page_template=500)


def setup_blueprints(application):
    """
    There are three blueprints: status_blueprint, no_cookie_blueprint, and main_blueprint.

    main_blueprint is the default for everything.

    json_updates_blueprint is for endpoints that provide (duh) JSON data, eg to power auto-updating pages like the
    service dashboard or notifications dashboard.

    status_blueprint is only for the status page - unauthenticated, unstyled, no cookies, etc.

    no_cookie_blueprint is for subresources (things loaded asynchronously) that we might be concerned are setting
    cookies unnecessarily and potentially getting in to strange race conditions and overwriting other cookies, as we've
    seen in the send message flow. Currently, this includes letter template previews, and the iframe from the platform
    admin email branding preview pages.
    """
    from app.main import json_updates as json_updates_blueprint
    from app.main import main as main_blueprint
    from app.main import no_cookie as no_cookie_blueprint
    from app.status import status as status_blueprint

    application.register_blueprint(main_blueprint)
    application.register_blueprint(json_updates_blueprint)

    # no_cookie_blueprint specifically doesn't have `make_session_permanent` or `save_service_or_org_after_request`
    application.register_blueprint(no_cookie_blueprint)
    application.register_blueprint(status_blueprint)


def on_user_logged_in(_sender, user):
    Events.sucessful_login(user_id=user.id)


def setup_event_handlers():
    from flask_login import user_logged_in

    user_logged_in.connect(on_user_logged_in)


def add_template_filters(application):
    for fn in [
        format_auth_type,
        format_billions,
        format_datetime,
        format_datetime_normal,
        format_datetime_short,
        format_time,
        valid_phone_number,
        format_pennies_as_currency,
        format_date,
        format_date_human,
        format_date_normal,
        format_date_numeric,
        format_date_short,
        format_datetime_human,
        format_datetime_relative,
        format_datetime_numeric,
        format_day_of_week,
        format_delta,
        format_delta_days,
        format_notification_status,
        format_notification_type,
        format_notification_status_as_time,
        format_notification_status_as_field_status,
        format_notification_status_as_url,
        format_pounds_as_currency,
        formatted_list,
        get_lines_with_normalised_whitespace,
        nl2br,
        format_phone_number_human_readable,
        format_thousands,
        insert_wbr,
        make_string_safe_for_id,
        convert_to_boolean,
        format_list_items,
        iteration_count,
        recipient_count,
        recipient_count_label,
        redact_mobile_number,
        message_count_label,
        message_count,
        message_count_noun,
        message_finished_processing_notification,
        format_yes_no,
        make_string_safe_for_email_local_part,
        extract_path_from_url,
        sentence_case,
    ]:
        application.add_template_filter(fn)


def init_jinja(application):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    template_folders = [
        os.path.join(repo_root, "app/templates_nl"),
    ]

    application.jinja_loader = jinja2.ChoiceLoader(
        [
            jinja2.FileSystemLoader(template_folders),
            jinja2.PrefixLoader({"govuk_frontend_jinja": jinja2.PackageLoader("govuk_frontend_jinja")}),
        ]
    )

    application.jinja_env.filters["format_provider"] = format_provider
    application.jinja_env.add_extension("jinja2.ext.do")
    application.jinja_env.undefined = NotifyJinjaUndefined


class NotifyJinjaUndefined(jinja2.Undefined):
    """
    The same as jinja2.StrictUndefined with a few exceptions, noted
    in specific comments.

    For more context see:
    https://jinja.palletsprojects.com/en/stable/api/#undefined-types
    """

    __slots__ = ()
    __iter__ = jinja2.Undefined._fail_with_undefined_error
    __len__ = jinja2.Undefined._fail_with_undefined_error
    __hash__ = jinja2.Undefined._fail_with_undefined_error
    # __bool__: UndefinedErrors remain supressed
    __contains__ = jinja2.Undefined._fail_with_undefined_error
    __str__ = jinja2.Undefined._fail_with_undefined_error

    def __eq__(self, other):
        if isinstance(self._undefined_obj, dict):
            # Accessing a missing field on a dict, we do this too
            # often to be strict about it
            return super().__eq__(other)

        if isinstance(other, NotifyJinjaUndefined):
            # Comparing to something else which is undefined, you are
            # probably doing this on purpose
            return True

        if isinstance(self._undefined_obj, jinja2.utils._MissingType):
            # Comparing to an internal Jinja type, you are probably
            # doing this on purpose
            return False

        # In any other case comparing undefined to something is bad
        # so raise an exception
        jinja2.Undefined._fail_with_undefined_error(self, other)
