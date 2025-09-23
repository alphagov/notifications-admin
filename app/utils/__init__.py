import hashlib
from datetime import timedelta
from functools import wraps
from itertools import chain

from flask import abort, g, make_response, request
from flask_login import current_user
from notifications_utils.field import Field
from ordered_set import OrderedSet
from werkzeug.datastructures import MultiDict
from werkzeug.routing import RequestRedirect

# if changing these, note there may be database indexes corresponding to some of
# these status sets in -api which may also need updating to prevent a
# performance degradation
SENDING_STATUSES = ["created", "pending", "sending", "pending-virus-check"]
DELIVERED_STATUSES = ["delivered", "sent", "returned-letter"]
FAILURE_STATUSES = [
    "failed",
    "temporary-failure",
    "permanent-failure",
    "technical-failure",
    "virus-scan-failed",
    "validation-failed",
]
REQUESTED_STATUSES = SENDING_STATUSES + DELIVERED_STATUSES + FAILURE_STATUSES

NOTIFICATION_TYPES = ["sms", "email", "letter"]

SEVEN_DAYS_TTL = int(timedelta(days=7).total_seconds())


def service_has_permission(permission):
    from app import current_service

    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            if not current_service or not current_service.has_permission(permission):
                abort(403)
            return func(*args, **kwargs)

        return wrap_func

    return wrap


def service_belongs_to_org_type(org_type):
    from app import current_service

    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            if not current_service or not current_service.organisation_type == org_type:
                abort(403)
            return func(*args, **kwargs)

        return wrap_func

    return wrap


def get_help_argument():
    return request.args.get("help") if request.args.get("help") in ("1", "2", "3") else None


def parse_filter_args(filter_dict):
    if not isinstance(filter_dict, MultiDict):
        filter_dict = MultiDict(filter_dict)

    return MultiDict(
        (key, (",".join(filter_dict.getlist(key))).split(","))
        for key in filter_dict.keys()
        if "".join(filter_dict.getlist(key))
    )


def set_status_filters(filter_args):
    status_filters = filter_args.get("status", [])
    return list(
        OrderedSet(
            chain(
                (status_filters or REQUESTED_STATUSES),
                DELIVERED_STATUSES if "delivered" in status_filters else [],
                SENDING_STATUSES if "sending" in status_filters else [],
                FAILURE_STATUSES if "failed" in status_filters else [],
            )
        )
    )


def unicode_truncate(s, length):
    encoded = s.encode("utf-8")[:length]
    return encoded.decode("utf-8", "ignore")


def should_skip_template_page(template):
    return (
        current_user.has_permissions("send_messages")
        and not current_user.has_permissions("manage_templates", "manage_api_keys")
        and template.template_type != "letter"
        and not template.get_raw("archived")
    )


def get_default_sms_sender(sms_senders):
    return str(next((Field(x["sms_sender"], html="escape") for x in sms_senders if x["is_default"]), "None"))


class PermanentRedirect(RequestRedirect):
    """
    In Werkzeug 0.15.0 the status code for RequestRedirect changed from 301 to 308.
    308 status codes are not supported when Internet Explorer is used with Windows 7
    and Windows 8.1, so this class keeps the original status code of 301.
    """

    code = 301


def hide_from_search_engines(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.hide_from_search_engines = True
        response = make_response(f(*args, **kwargs))
        response.headers["X-Robots-Tag"] = "noindex"
        return response

    return decorated_function


# Function to merge two dict or lists with a JSON-like structure into one.
# JSON-like means they can contain all types JSON can: all the main primitives
# plus nested lists or dictionaries.
# Merge is additive. New values overwrite old and collections are added to.
def merge_jsonlike(source, destination):  # noqa: C901
    def merge_items(source_item, destination_item):
        if isinstance(source_item, dict) and isinstance(destination_item, dict):
            merge_dicts(source_item, destination_item)
        elif isinstance(source_item, list) and isinstance(destination_item, list):
            merge_lists(source_item, destination_item)
        else:  # primitive value
            return False
        return True

    def merge_lists(source, destination):
        last_src_idx = len(source) - 1
        for idx, item in enumerate(destination):
            if idx <= last_src_idx:
                # assign destination value if can't be merged into source
                if merge_items(source[idx], destination[idx]) is False:
                    source[idx] = destination[idx]
            else:
                source.append(item)

    def merge_dicts(source, destination):
        for key, value in destination.items():
            if key in source:
                # assign destination value if can't be merged into source
                if merge_items(source[key], value) is False:
                    source[key] = value
            else:
                source[key] = value

    merge_items(source, destination)


def get_sha512_hashed(str):
    return hashlib.sha512(str.encode()).hexdigest()
