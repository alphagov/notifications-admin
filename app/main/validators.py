import re
from abc import ABC, abstractmethod

from flask import current_app, render_template
from notifications_utils.clients.zendesk.zendesk_client import NotifySupportTicket, NotifyTicketType
from notifications_utils.field import Field
from notifications_utils.formatters import autolink_urls, formatted_list
from notifications_utils.markdown import notify_email_markdown
from notifications_utils.recipient_validation.email_address import validate_email_address
from notifications_utils.recipient_validation.errors import InvalidEmailError, InvalidPhoneError
from notifications_utils.recipient_validation.notifynl.phone_number import PhoneNumber
from notifications_utils.sanitise_text import SanitiseSMS
from ordered_set import OrderedSet
from wtforms import ValidationError
from wtforms.validators import URL, DataRequired, InputRequired, StopValidation
from wtforms.validators import Length as WTFormsLength

from app import antivirus_client, current_service, zendesk_client
from app.formatters import sentence_case
from app.main._commonly_used_passwords import commonly_used_passwords
from app.models.spreadsheet import Spreadsheet
from app.notify_client.protected_sender_id_api_client import protected_sender_id_api_client
from app.utils.user import is_gov_user


class CommonlyUsedPassword:
    def __init__(self, message=None):
        if not message:
            message = "Password is in list of commonly used passwords."
        self.message = message

    def __call__(self, form, field):
        if field.data in commonly_used_passwords:
            raise ValidationError(self.message)


class CsvFileValidator:
    def __init__(self, message="Not a csv file"):
        self.message = message

    def __call__(self, form, field):
        if not Spreadsheet.can_handle(field.data.filename):
            raise ValidationError("The file must be a spreadsheet that Notify can read")


class ValidGovEmail:
    def __call__(self, form, field):
        if field.data == "":
            return

        from flask import url_for

        message = """
            Enter a public sector email address or
            <a class="govuk-link govuk-link--no-visited-state" href="{}">find out who can use Notify</a>
        """.format(url_for("main.guidance_who_can_use_notify"))
        if not is_gov_user(field.data.lower()):
            raise ValidationError(message)


class ValidEmail:
    def __init__(
        self,
        message="Enter an email address in the correct format, like name@example.gov.uk",
        error_summary_message="Enter %s in the correct format",
    ):
        self.message = message
        self.error_summary_message = error_summary_message

    def __call__(self, form, field):
        if not field.data:
            return

        try:
            validate_email_address(field.data)
        except InvalidEmailError as e:
            if hasattr(field, "error_summary_messages"):
                field.error_summary_messages.append(self.error_summary_message)
            raise ValidationError(self.message) from e


class ValidPhoneNumber:
    def __init__(
        self,
        allow_international_sms=False,
        allow_sms_to_uk_landlines=False,
        message=None,
    ):
        self.allow_international_sms = allow_international_sms
        self.allow_sms_to_uk_landlines = allow_sms_to_uk_landlines
        self.message = message

    _error_summary_messages_map = {
        InvalidPhoneError.Codes.TOO_SHORT: "%s is too short",
        InvalidPhoneError.Codes.TOO_LONG: "%s is too long",
        InvalidPhoneError.Codes.NOT_A_UK_MOBILE: "%s does not look like a UK mobile number",
        InvalidPhoneError.Codes.UNSUPPORTED_COUNTRY_CODE: "Country code for %s not found",
        InvalidPhoneError.Codes.UNKNOWN_CHARACTER: "%s can only include: 0 1 2 3 4 5 6 7 8 9 ( ) + -",
        InvalidPhoneError.Codes.INVALID_NUMBER: "%s is not valid – double check the phone number you entered",
    }

    def __call__(self, form, field):
        try:
            if field.data:
                number = PhoneNumber(field.data)
                number.validate(
                    allow_international_number=self.allow_international_sms,
                    allow_uk_landline=self.allow_sms_to_uk_landlines,
                )
        except InvalidPhoneError as e:
            error_message = str(e)
            if hasattr(field, "error_summary_messages"):
                error_summary_message = self._error_summary_messages_map[e.code]

                field.error_summary_messages.append(error_summary_message)

            raise ValidationError(error_message) from e


class NoCommasInPlaceHolders:
    def __init__(self, message="You cannot put commas between double brackets"):
        self.message = message

    def __call__(self, form, field):
        if "," in "".join(Field(field.data).placeholders):
            raise ValidationError(self.message)


class NoElementInSVG(ABC):
    @property
    @abstractmethod
    def element(self):
        pass

    @property
    @abstractmethod
    def message(self):
        pass

    def __call__(self, form, field):
        svg_contents = field.data.stream.read().decode("utf-8")
        field.data.stream.seek(0)
        if f"<{self.element}" in svg_contents.lower():
            raise ValidationError(self.message)


class NoEmbeddedImagesInSVG(NoElementInSVG):
    element = "image"
    message = "This SVG has an embedded raster image in it and will not render well"


class NoTextInSVG(NoElementInSVG):
    element = "text"
    message = "This SVG has text which has not been converted to paths and may not render well"


class OnlySMSCharacters:
    def __init__(self, *args, template_type, **kwargs):
        self._template_type = template_type
        super().__init__(*args, **kwargs)

    def __call__(self, form, field):
        non_sms_characters = sorted(SanitiseSMS.get_non_compatible_characters(field.data))
        if non_sms_characters:
            raise ValidationError(
                "You cannot use {} in text messages. {} will not display properly on some phones.".format(
                    formatted_list(non_sms_characters, conjunction="or", before_each="", after_each=""),
                    ("It" if len(non_sms_characters) == 1 else "These characters"),
                )
            )


class DoesNotStartWithDoubleZero:
    def __init__(self, message="Text message sender ID cannot start with 00"):
        self.message = message

    def __call__(self, form, field):
        if field.data and field.data.startswith("00"):
            raise ValidationError(self.message)


class IsNotAGenericSenderID:
    generic_sender_ids = ["info", "verify", "alert"]

    def __init__(
        self,
        message="Text message sender ID cannot be Alert, Info or Verify as those are prohibited due to usage by spam",
    ):
        self.message = message

    def __call__(self, form, field):
        if field.data and field.data.lower() in self.generic_sender_ids:
            raise ValidationError(self.message)


class IsNotLikeNHSNoReply:
    def __call__(self, form, field):
        lower_cased_data = field.data.lower()
        if (
            field.data
            and ("nhs" in lower_cased_data and "no" in lower_cased_data and "reply" in lower_cased_data)
            and field.data != "NHSNoReply"
        ):
            raise ValidationError("Text message sender ID must match other NHS services - change it to ‘NHSNoReply’")


def create_phishing_senderid_zendesk_ticket(senderID=None):
    ticket_message = render_template(
        "support-tickets/phishing-senderid.txt",
        senderID=senderID,
    )
    ticket = NotifySupportTicket(
        subject=f"Possible Phishing sender ID - {current_service.name}",
        message=ticket_message,
        ticket_type=NotifySupportTicket.TYPE_TASK,
        notify_ticket_type=NotifyTicketType.TECHNICAL,
        notify_task_type="notify_task_blocked_sender",
    )
    zendesk_client.send_ticket_to_zendesk(ticket)


class IsNotAPotentiallyMaliciousSenderID:
    def __call__(self, form, field):
        if protected_sender_id_api_client.get_check_sender_id(sender_id=field.data):
            create_phishing_senderid_zendesk_ticket(senderID=field.data)
            current_app.logger.warning("User tried to set sender id to potentially malicious one: %s", field.data)
            raise ValidationError(
                f"Text message sender ID cannot be ‘{field.data}’ - this is to protect recipients from phishing scams"
            )


class IsAUKMobileNumberOrShortCode:
    number_regex = re.compile(r"^[0-9\.]+$")
    mobile_regex = re.compile(r"^07[0-9]{9}$")
    shortcode_regex = re.compile(r"^[6-8][0-9]{4}$")

    def __init__(self, message="A numeric sender id should be a valid mobile number or short code"):
        self.message = message

    def __call__(self, form, field):
        if (
            field.data
            and re.match(self.number_regex, field.data)
            and not re.match(self.mobile_regex, field.data)
            and not re.match(self.shortcode_regex, field.data)
        ):
            raise ValidationError(self.message)


class MustContainAlphanumericCharacters:
    regex = re.compile(r".*[a-zA-Z0-9].*[a-zA-Z0-9].*")

    def __init__(self, *, thing=None, message="Must include at least two alphanumeric characters"):
        if thing:
            self.message = f"{sentence_case(thing)} must include at least 2 letters or numbers"
        else:
            # DEPRECATED - prefer to pass in `thing` instead. When all instances are using `thing,` retire `message`
            # altogether.
            self.message = message

    def __call__(self, form, field):
        if field.data and not re.match(self.regex, field.data):
            raise ValidationError(self.message)


class CharactersNotAllowed:
    def __init__(self, characters_not_allowed, *args, thing="item", message=None, error_summary_message=None):
        self.characters_not_allowed = OrderedSet(characters_not_allowed)
        self.thing = thing
        self.message = message
        self.error_summary_message = error_summary_message

    def __call__(self, form, field):
        illegal_characters = self.characters_not_allowed.intersection(field.data)

        if illegal_characters:
            if self.message:
                error_message = self.message
            else:
                error_message = (
                    f"Cannot contain "
                    f"{formatted_list(illegal_characters, conjunction='or', before_each='', after_each='')}"
                )

            if hasattr(field, "error_summary_messages"):
                if self.error_summary_message:
                    error_summary_message = self.error_summary_message
                else:
                    error_summary_message = (
                        f"%s cannot contain "
                        f"{formatted_list(illegal_characters, conjunction='or', before_each='', after_each='')}"
                    )
                field.error_summary_messages.append(error_summary_message)

            raise ValidationError(error_message)


class StringsNotAllowed:
    def __init__(self, *args, thing="item", message=None, error_summary_message=None, match_on_substrings=False):
        self.strings_not_allowed = OrderedSet(string.lower() for string in args)
        self.match_on_substrings = match_on_substrings
        self.thing = thing
        self.message = message
        self.error_summary_message = error_summary_message

    def __call__(self, form, field):
        normalised = field.data.lower()
        for not_allowed in self.strings_not_allowed:
            if normalised == not_allowed or (self.match_on_substrings and not_allowed in normalised):
                if self.message:
                    error_message = self.message
                else:
                    error_message = f"Cannot {'contain' if self.match_on_substrings else 'be'} ‘{not_allowed}’"

                if hasattr(field, "error_summary_messages"):
                    if self.error_summary_message:
                        error_summary_message = self.error_summary_message
                    else:
                        error_summary_message = (
                            f"%s cannot {'contain' if self.match_on_substrings else 'be'} ‘{not_allowed}’"
                        )
                    field.error_summary_messages.append(error_summary_message)

                raise ValidationError(error_message)


class FileIsVirusFree:
    def __call__(self, form, field):
        if field.data:
            if current_app.config["ANTIVIRUS_ENABLED"]:
                try:
                    virus_free = antivirus_client.scan(field.data)
                    if not virus_free:
                        raise StopValidation("This file contains a virus")
                finally:
                    field.data.seek(0)


class NotifyDataRequired(DataRequired):
    def __init__(self, thing):
        super().__init__(message=f"Enter {thing}")


class NotifyInputRequired(InputRequired):
    def __init__(self, thing):
        super().__init__(message=f"Enter {thing}")


class NotifyUrlValidator(URL):
    def __init__(self, thing="a URL in the correct format"):
        super().__init__(message=f"Enter {thing}")


class CannotContainURLsOrLinks:
    def __init__(self, *, thing):
        self.thing = thing

    def __call__(self, form, field):
        for func in (autolink_urls, notify_email_markdown):
            if "<a href=" in func(field.data):
                raise ValidationError(f"{self.thing.capitalize()} cannot contain a URL")


class Length(WTFormsLength):
    def __init__(self, min=-1, max=-1, message=None, thing=None, unit="characters"):
        super().__init__(min=min, max=max, message=message)
        self.thing = thing
        self.unit = unit

        if not self.message:
            if not self.thing:
                raise RuntimeError("Must provide `thing` (preferred) unless `message` is explicitly set.")

            if min >= 0 and max >= 0:
                if min == max:
                    self.message = f"{sentence_case(thing)} must be {min} {unit} long"
                else:
                    self.message = f"{sentence_case(thing)} must be between {min} and {max} {unit} long"
            elif min >= 0:
                self.message = f"{sentence_case(thing)} must be at least {min} {unit} long"
            else:
                self.message = f"{sentence_case(thing)} cannot be longer than {max} {unit}"
