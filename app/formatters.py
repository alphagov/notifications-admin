import decimal
import re
import urllib
from datetime import UTC, datetime, timedelta
from numbers import Number

import ago
import dateutil
import humanize
from flask import url_for
from markupsafe import Markup
from notifications_utils.field import Field
from notifications_utils.formatters import make_quotes_smart
from notifications_utils.formatters import nl2br as utils_nl2br
from notifications_utils.recipient_validation.notifynl.phone_number import PhoneNumber
from notifications_utils.recipient_validation.phone_number import InvalidPhoneError
from notifications_utils.take import Take
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime

from app.utils.time import is_less_than_days_ago


def convert_to_boolean(value):
    if isinstance(value, str):
        if value.lower() in ["t", "true", "on", "yes", "1"]:
            return True
        elif value.lower() in ["f", "false", "off", "no", "0"]:
            return False

    return value


def format_datetime(date):
    return f"{format_date(date)} at {format_time(date)}"


def format_datetime_normal(date):
    return f"{format_date_normal(date)} at {format_time(date)}"


def format_datetime_short(date):
    return f"{format_date_short(date)} at {format_time(date)}"


def format_datetime_relative(date):
    return f"{get_human_day(date)} at {format_time(date)}"


def format_datetime_numeric(date):
    return f"{format_date_numeric(date)} {format_time_24h(date)}"


def format_date_numeric(date):
    return utc_string_to_aware_gmt_datetime(date).strftime("%Y-%m-%d")


def format_time_24h(date):
    return utc_string_to_aware_gmt_datetime(date).strftime("%H:%M")


def get_human_day(time, date_prefix="", include_day_of_week=False):
    #  Add 1 minute to transform 00:00 into ‘midnight today’ instead of ‘midnight tomorrow’
    date = (utc_string_to_aware_gmt_datetime(time) - timedelta(minutes=1)).date()
    now = datetime.utcnow()

    if date == (now + timedelta(days=1)).date():
        return "tomorrow"
    if date == now.date():
        return "today"
    if date == (now - timedelta(days=1)).date():
        return "yesterday"

    date_prefix = f"{date_prefix} " if date_prefix else ""
    day_of_week = date.strftime("%A ") if include_day_of_week else ""
    year = date.strftime(" %Y") if date.strftime("%Y") != now.strftime("%Y") else ""

    return f"{date_prefix}{day_of_week}{_format_datetime_short(date)}{year}"


def format_time(date):
    return {"12:00AM": "Midnight", "12:00PM": "Midday"}.get(
        utc_string_to_aware_gmt_datetime(date).strftime("%-I:%M%p"),
        utc_string_to_aware_gmt_datetime(date).strftime("%-I:%M%p"),
    ).lower()


def format_date(date):
    return utc_string_to_aware_gmt_datetime(date).strftime("%A %d %B %Y")


def format_date_normal(date):
    return utc_string_to_aware_gmt_datetime(date).strftime("%d %B %Y").lstrip("0")


def format_date_short(date):
    return _format_datetime_short(utc_string_to_aware_gmt_datetime(date))


def format_date_human(date):
    return get_human_day(date)


def format_datetime_human(date, date_prefix="on", separator="at"):
    return f"{get_human_day(date, date_prefix=date_prefix)} {separator} {format_time(date)}"


def format_day_of_week(date):
    return utc_string_to_aware_gmt_datetime(date).strftime("%A")


def _format_datetime_short(datetime):
    return datetime.strftime("%d %B").lstrip("0")


def naturaltime_without_indefinite_article(date):
    return re.sub(
        "an? (.*) ago",
        lambda match: f"1 {match.group(1)} ago",
        humanize.naturaltime(date),
    )


def format_delta(date):
    delta = (datetime.now(UTC)) - (utc_string_to_aware_gmt_datetime(date))
    if delta < timedelta(seconds=30):
        return "just now"
    if delta < timedelta(seconds=60):
        return "in the last minute"
    return naturaltime_without_indefinite_article(delta)


def format_delta_days(date, numeric_prefix=""):
    now = datetime.now(UTC)
    date = utc_string_to_aware_gmt_datetime(date)
    if date.strftime("%Y-%m-%d") == now.strftime("%Y-%m-%d"):
        return "today"
    if date.strftime("%Y-%m-%d") == (now - timedelta(days=1)).strftime("%Y-%m-%d"):
        return "yesterday"
    return numeric_prefix + naturaltime_without_indefinite_article(now - date)


def valid_phone_number(phone_number):
    try:
        PhoneNumber(phone_number)
        return True
    except InvalidPhoneError:
        return False


def format_notification_type(notification_type):
    return {"email": "Email", "sms": "Text message", "letter": "Letter"}[notification_type]


def format_notification_status(status, template_type):
    return {
        "email": {
            "failed": "Failed",
            "technical-failure": "Technical failure",
            "temporary-failure": "Inbox not accepting messages right now",
            "permanent-failure": "Email address does not exist",
            "delivered": "Delivered",
            "sending": "Delivering",
            "created": "Delivering",
            "sent": "Delivered",
        },
        "sms": {
            "failed": "Failed",
            "technical-failure": "Technical failure",
            "temporary-failure": "Phone not accepting messages right now",
            "permanent-failure": "Not delivered",
            "delivered": "Delivered",
            "sending": "Delivering",
            "created": "Delivering",
            "pending": "Delivering",
            "sent": "Sent to an international number",
            "validation-failed": "Validation failed",
        },
        "letter": {
            "failed": "",
            "technical-failure": "Technical failure",
            "temporary-failure": "",
            "permanent-failure": "Permanent failure",
            "delivered": "",
            "received": "",
            "accepted": "",
            "sending": "",
            "created": "",
            "sent": "",
            "pending-virus-check": "",
            "virus-scan-failed": "Virus detected",
            "returned-letter": "",
            "cancelled": "",
            "validation-failed": "Validation failed",
        },
    }[template_type].get(status, status)


def format_notification_status_as_time(status, created, updated):
    return dict.fromkeys({"created", "pending", "sending"}, f" since {created}").get(status, updated)


def format_notification_status_as_field_status(status, notification_type):
    return {
        "letter": {
            "failed": "error",
            "technical-failure": "error",
            "temporary-failure": "error",
            "permanent-failure": "error",
            "delivered": None,
            "sent": None,
            "sending": None,
            "created": None,
            "accepted": None,
            "pending-virus-check": None,
            "virus-scan-failed": "error",
            "returned-letter": None,
            "cancelled": "error",
        },
    }.get(
        notification_type,
        {
            "failed": "error",
            "technical-failure": "error",
            "temporary-failure": "error",
            "permanent-failure": "error",
            "delivered": None,
            "sent": "sent-international" if notification_type == "sms" else None,
            "sending": "default",
            "created": "default",
            "pending": "default",
        },
    ).get(status, "error")


def format_notification_status_as_url(status, notification_type):
    if status not in {
        "technical-failure",
        "temporary-failure",
        "permanent-failure",
    }:
        return None

    if notification_type not in {
        "email",
        "sms",
    }:
        return None

    return url_for("main.guidance_message_status", notification_type=notification_type)


def nl2br(value):
    if value:
        return Markup(
            Take(
                Field(
                    value,
                    html="escape",
                )
            ).then(utils_nl2br)
        )
    return ""


def format_pounds_as_currency(number: float):
    return format_pennies_as_currency(round(number * 100), long=False)


def format_pennies_as_currency(pennies: int | float, long: bool) -> str:
    # \/ Avoid floating point precision errors with fractional pennies, eg for SMS rates \/
    pennies = decimal.Decimal(str(pennies))
    if pennies >= 100:
        pennies = round(pennies)
        return f"£{pennies // 100:,}.{pennies % 100:02}"
    elif long:
        return f"{pennies} pence"

    return f"{pennies}p"


def format_list_items(items, format_string, *args, **kwargs):
    """
    Apply formatting to each item in an iterable. Returns a list.
    Each item is made available in the format_string as the 'item' keyword argument.
    example usage: ['png','svg','pdf']|format_list_items('{0}. {item}', [1,2,3]) -> ['1. png', '2. svg', '3. pdf']
    """
    return [format_string.format(*args, item=item, **kwargs) for item in items]


def format_thousands(value):
    if isinstance(value, Number):
        return f"{value:,.0f}"
    if value is None:
        return ""
    return value


def insert_wbr(string):
    return Markup(string.replace(",", ",<wbr />"))


def redact_mobile_number(mobile_number, spacing=""):
    indices = [-4, -5, -6, -7]
    redact_character = spacing + "•" + spacing
    mobile_number_list = list(mobile_number.replace(" ", ""))
    for i in indices:
        mobile_number_list[i] = redact_character
    return "".join(mobile_number_list)


def get_time_left(created_at, service_data_retention_days=7):
    if not isinstance(created_at, datetime):
        created_at = dateutil.parser.parse(created_at)
    return ago.human(
        (datetime.now(UTC))
        - (created_at.replace(hour=0, minute=0, second=0) + timedelta(days=service_data_retention_days + 1)),
        future_tense="Data available for {}",
        past_tense="Data no longer available",  # No-one should ever see this
        precision=1,
    )


def starts_with_initial(name):
    return bool(re.match(r"^.\.", name))


def remove_middle_initial(name):
    return re.sub(r"\s+.\s+", " ", name)


def remove_digits(name):
    return "".join(c for c in name if not c.isdigit())


def normalize_spaces(name):
    return " ".join(name.split())


def guess_name_from_email_address(email_address):
    possible_name = re.split(r"[\@\+]", email_address)[0]

    if "." not in possible_name or starts_with_initial(possible_name):
        return ""

    return (
        Take(possible_name)
        .then(str.replace, ".", " ")
        .then(remove_digits)
        .then(remove_middle_initial)
        .then(str.title)
        .then(make_quotes_smart)
        .then(normalize_spaces)
    )


def message_count_label(count, message_type, suffix="sent"):
    if suffix:
        return f"{message_count_noun(count, message_type)} {suffix}"
    return message_count_noun(count, message_type)


def message_count_noun(count, message_type):
    singular = count == 1

    if message_type == "sms":
        return "text message" if singular else "text messages"

    if message_type == "international_sms":
        return "international text message" if singular else "international text messages"

    if message_type == "email":
        return "email" if singular else "emails"

    if message_type == "letter":
        return "letter" if singular else "letters"

    if message_type and message_type.endswith("request"):
        return message_type if singular else message_type + "s"

    return "message" if singular else "messages"


def message_count(count, message_type):
    return f"{format_thousands(count)} {message_count_noun(count, message_type)}"


def recipient_count_label(count, template_type):
    singular = count == 1

    if template_type == "sms":
        return "phone number" if singular else "phone numbers"

    if template_type == "international_sms":
        return "international phone number" if singular else "international phone numbers"

    if template_type == "email":
        return "email address" if singular else "email addresses"

    if template_type == "letter":
        return "address" if singular else "addresses"

    return "recipient" if singular else "recipients"


def recipient_count(count, template_type):
    return f"{format_thousands(count)} {recipient_count_label(count, template_type)}"


def iteration_count(count):
    if count == 1:
        return "once"
    if count == 2:
        return "twice"
    return f"{count} times"


def character_count(count):
    if count == 1:
        return "1 character"
    return f"{format_thousands(count)} characters"


def format_billions(count):
    return humanize.intword(count)


def format_yes_no(value, yes="Yes", no="No", none="No"):
    if value is None:
        return none
    return yes if value else no


def format_auth_type(auth_type, with_indefinite_article=False):
    indefinite_article, auth_type = {
        "email_auth": ("an", "Email link"),
        "sms_auth": ("a", "Text message code"),
        "webauthn_auth": ("a", "Security key"),
    }[auth_type]

    if with_indefinite_article:
        return f"{indefinite_article} {auth_type.lower()}"

    return auth_type


def extract_path_from_url(url):
    return urllib.parse.urlunsplit(urllib.parse.urlsplit(url)._replace(scheme="", netloc=""))


def sentence_case(sentence):
    first_word, rest_of_sentence = (sentence + " ").split(" ", 1)
    return f"{first_word.title()} {rest_of_sentence}"[:-1]


def message_finished_processing_notification(processing_started, data_retention_period):
    within_data_retention_message = "No messages to show"
    outside_data_retention_message = (
        f"These messages have been deleted because they were sent more than {data_retention_period} days ago"
    )

    return (
        within_data_retention_message
        if is_less_than_days_ago(processing_started, data_retention_period)
        else outside_data_retention_message
    )


def format_phone_number_human_readable(number):
    try:
        phone_number = PhoneNumber(number)
    except InvalidPhoneError:
        # if there was a validation error, we want to shortcut out here, but still display the number on the front end
        return number
    return phone_number.get_human_readable_format()
