from datetime import datetime, timedelta

import pytz
from dateutil import parser
from flask import url_for
from notifications_utils.formatters import unescaped_formatted_list
from notifications_utils.letter_timings import letter_can_be_cancelled
from notifications_utils.recipient_validation.postal_address import PostalAddress
from notifications_utils.template import BaseLetterTemplate
from notifications_utils.timezones import (
    convert_bst_to_utc,
    convert_utc_to_bst,
    utc_string_to_aware_gmt_datetime,
)


def printing_today_or_tomorrow(created_at):
    print_cutoff = convert_bst_to_utc(convert_utc_to_bst(datetime.utcnow()).replace(hour=17, minute=30)).replace(
        tzinfo=pytz.utc
    )
    created_at = utc_string_to_aware_gmt_datetime(created_at)

    if created_at < print_cutoff:
        return "today"
    else:
        return "tomorrow"


def get_letter_printing_statement(status, created_at, long_form=True):
    if isinstance(created_at, datetime):
        created_at = created_at.astimezone(pytz.utc).isoformat()
    created_at_dt = parser.parse(created_at).replace(tzinfo=None)
    if letter_can_be_cancelled(status, created_at_dt):
        decription = "Printing starts" if long_form else "Printing"
        return f"{decription} {printing_today_or_tomorrow(created_at)} at 5:30pm"
    else:
        printed_datetime = utc_string_to_aware_gmt_datetime(created_at) + timedelta(hours=6, minutes=30)
        if printed_datetime.date() == datetime.now().date():
            return "Printed today at 5:30pm"
        elif printed_datetime.date() == datetime.now().date() - timedelta(days=1):
            return "Printed yesterday at 5:30pm"

        printed_date = printed_datetime.strftime("%d %B").lstrip("0")
        description = "Printed on" if long_form else "Printed"

        return f"{description} {printed_date} at 5:30pm"


LETTER_VALIDATION_MESSAGES = {
    "letter-not-a4-portrait-oriented": {
        "title": "Your letter is not A4 portrait size",
        "detail": (
            "You need to change the size or orientation of {invalid_pages}. <br>"
            "Files must meet our "
            '<a class="govuk-link govuk-link--destructive" href="{letter_spec_guidance}" target="_blank">'
            "letter specification (opens in a new tab)"
            "</a>."
        ),
        "summary": (
            "Validation failed because {invalid_pages} {invalid_pages_are_or_is} not A4 portrait size.<br>"
            "Files must meet our "
            '<a class="govuk-link govuk-link--no-visited-state" href="{letter_spec_guidance}">'
            "letter specification (opens in a new tab)"
            "</a>."
        ),
    },
    "content-outside-printable-area": {
        "title": "Your content is outside the printable area",
        "detail": (
            "You need to edit {invalid_pages}.<br>"
            "Files must meet our "
            '<a class="govuk-link govuk-link--destructive" href="{letter_spec_guidance}">'
            "letter specification (opens in a new tab)"
            "</a>."
        ),
        "summary": (
            "Validation failed because content is outside the printable area on {invalid_pages}.<br>"
            "Files must meet our "
            '<a class="govuk-link govuk-link--no-visited-state" href="{letter_spec_guidance}" target="_blank">'
            "letter specification (opens in a new tab)"
            "</a>."
        ),
    },
    "letter-too-long": {
        "title": "Your letter is too long",
        "detail": (
            f"Letters must be {BaseLetterTemplate.max_page_count} pages or less "
            f"({BaseLetterTemplate.max_sheet_count} double-sided sheets of paper). <br>"
            "Your letter is {page_count} pages long."
        ),
        "summary": (
            "Validation failed because this letter is {page_count} pages long.<br>"
            f"Letters must be {BaseLetterTemplate.max_page_count} pages or less "
            f"({BaseLetterTemplate.max_sheet_count} double-sided sheets of paper)."
        ),
    },
    "no-encoded-string": {"title": "Sanitise failed - No encoded string"},
    "unable-to-read-the-file": {
        "title": "There’s a problem with your file",
        "detail": ("Notify cannot read this PDF.<br>Save a new copy of your file and try again."),
        "summary": (
            "Validation failed because Notify cannot read this PDF.<br>Save a new copy of your file and try again."
        ),
    },
    "address-is-empty": {
        "title": "The address block is empty",
        "detail": (
            "You need to add a recipient address.<br>"
            "Files must meet our "
            '<a class="govuk-link govuk-link--destructive" href="{letter_spec_guidance}" target="_blank">'
            "letter specification (opens in a new tab)"
            "</a>."
        ),
        "summary": (
            "Validation failed because the address block is empty.<br>"
            "Files must meet our "
            '<a class="govuk-link govuk-link--no-visited-state" href="{letter_spec_guidance}" target="_blank">'
            "letter specification (opens in a new tab)"
            "</a>."
        ),
    },
    "not-a-real-uk-postcode": {
        "title": "There’s a problem with the address for this letter",
        "detail": "The last line of the address must be a real UK postcode.",
        "summary": "Validation failed because the last line of the address is not a real UK postcode.",
    },
    "cant-send-international-letters": {
        "title": "There’s a problem with the address for this letter",
        "detail": "You do not have permission to send letters to other countries.",
        "summary": "Validation failed because your service cannot send letters to other countries.",
    },
    "not-a-real-uk-postcode-or-country": {
        "title": "There’s a problem with the address for this letter",
        "detail": "The last line of the address must be a UK postcode or another country.",
        "summary": "Validation failed because the last line of the address is not a UK postcode or another country.",
    },
    "not-enough-address-lines": {
        "title": "There’s a problem with the address for this letter",
        "detail": f"The address must be at least {PostalAddress.MIN_LINES} lines long.",
        "summary": f"Validation failed because the address must be at least {PostalAddress.MIN_LINES} lines long.",
    },
    "too-many-address-lines": {
        "title": "There’s a problem with the address for this letter",
        "detail": f"The address must be no more than {PostalAddress.MAX_LINES} lines long.",
        "summary": (
            f"Validation failed because the address must be no more than {PostalAddress.MAX_LINES} lines long."
        ),
    },
    "invalid-char-in-address": {
        "title": "There’s a problem with the address for this letter",
        "detail": "Address lines must not start with any of the following characters: @ ( ) = [ ] ” \\ / , < > ~",
        "summary": (
            "Validation failed because address lines must not start with any of the "
            "following characters: @ ( ) = [ ] ” \\ / , < > ~"
        ),
    },
    "has-country-for-bfpo-address": {
        "title": "There’s a problem with the address for this letter",
        "detail": "The last line of a BFPO address must not be a country.",
        "summary": "Validation failed because the last line of the BFPO address is a country.",
    },
    "notify-tag-found-in-content": {
        "title": "There’s a problem with your letter",
        "detail": "Your file includes a letter you’ve downloaded from Notify.<br>You need to edit {invalid_pages}.",
        "summary": (
            "Validation failed because your file includes a letter you’ve downloaded from Notify on {invalid_pages}."
        ),
    },
    "no-fixed-abode-address": {
        "title": "There is a problem",
        "detail": "Enter a real address.",
        "summary": "Validation failed because this is not a real address.",
    },
}


def get_letter_validation_error(validation_message, invalid_pages=None, page_count=None):
    if not invalid_pages:
        invalid_pages = []
    if validation_message not in LETTER_VALIDATION_MESSAGES:
        return {"title": "Validation failed"}

    invalid_pages_are_or_is = "is" if len(invalid_pages) == 1 else "are"

    invalid_pages = unescaped_formatted_list(
        invalid_pages, before_each="", after_each="", prefix="page", prefix_plural="pages"
    )

    return {
        "title": LETTER_VALIDATION_MESSAGES[validation_message]["title"],
        "detail": LETTER_VALIDATION_MESSAGES[validation_message]["detail"].format(
            invalid_pages=invalid_pages,
            invalid_pages_are_or_is=invalid_pages_are_or_is,
            page_count=page_count,
            letter_spec_guidance=url_for("main.guidance_upload_a_letter"),
        ),
        "summary": LETTER_VALIDATION_MESSAGES[validation_message]["summary"].format(
            invalid_pages=invalid_pages,
            invalid_pages_are_or_is=invalid_pages_are_or_is,
            page_count=page_count,
            letter_spec_guidance=url_for("main.guidance_upload_a_letter"),
        ),
    }


def get_error_from_upload_form(form_errors):
    error = {}
    if "PDF" in form_errors:
        error["title"] = "Wrong file type"
    else:
        error["title"] = "There is a problem"

    error["detail"] = form_errors

    return error
