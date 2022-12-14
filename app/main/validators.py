import re
from abc import ABC, abstractmethod

from flask import current_app
from notifications_utils.field import Field
from notifications_utils.formatters import formatted_list
from notifications_utils.recipients import InvalidEmailError, validate_email_address
from notifications_utils.sanitise_text import SanitiseSMS
from notifications_utils.template import BroadcastMessageTemplate
from orderedset import OrderedSet
from wtforms import ValidationError
from wtforms.validators import StopValidation

from app import antivirus_client
from app.main._commonly_used_passwords import commonly_used_passwords
from app.models.spreadsheet import Spreadsheet
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
            raise ValidationError("{} is not a spreadsheet that Notify can read".format(field.data.filename))


class ValidGovEmail:
    def __call__(self, form, field):

        if field.data == "":
            return

        from flask import url_for

        message = """
            Enter a public sector email address or
            <a class="govuk-link govuk-link--no-visited-state" href="{}">find out who can use Notify</a>
        """.format(
            url_for("main.who_can_use_notify")
        )
        if not is_gov_user(field.data.lower()):
            raise ValidationError(message)


class ValidEmail:

    message = "Enter a valid email address"

    def __call__(self, form, field):

        if not field.data:
            return

        try:
            validate_email_address(field.data)
        except InvalidEmailError:
            raise ValidationError(self.message)


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
        non_sms_characters = sorted(list(SanitiseSMS.get_non_compatible_characters(field.data)))
        if non_sms_characters:
            raise ValidationError(
                "You cannot use {} in {}. {} will not show up properly on everyone’s phones.".format(
                    formatted_list(non_sms_characters, conjunction="or", before_each="", after_each=""),
                    {
                        "broadcast": "broadcasts",
                        "sms": "text messages",
                    }.get(self._template_type),
                    ("It" if len(non_sms_characters) == 1 else "They"),
                )
            )


class NoPlaceholders:
    def __init__(self, message=None):
        self.message = message or "You can’t use ((double brackets)) to personalise this message"

    def __call__(self, form, field):
        if Field(field.data).placeholders:
            raise ValidationError(self.message)


class BroadcastLength:
    def __call__(self, form, field):
        template = BroadcastMessageTemplate(
            {
                "template_type": "broadcast",
                "content": field.data,
            }
        )

        if template.content_too_long:
            non_gsm_characters = list(sorted(template.non_gsm_characters))
            if non_gsm_characters:
                raise ValidationError(
                    f"Content must be {template.max_content_count:,.0f} "
                    f"characters or fewer because it contains "
                    f'{formatted_list(non_gsm_characters, conjunction="and", before_each="", after_each="")}'
                )
            raise ValidationError(f"Content must be {template.max_content_count:,.0f} characters or fewer")


class LettersNumbersSingleQuotesFullStopsAndUnderscoresOnly:

    regex = re.compile(r"^[a-zA-Z0-9\s\._']+$")

    def __init__(self, message="Use letters and numbers only"):
        self.message = message

    def __call__(self, form, field):
        if field.data and not re.match(self.regex, field.data):
            raise ValidationError(self.message)


class DoesNotStartWithDoubleZero:
    def __init__(self, message="Cannot start with 00"):
        self.message = message

    def __call__(self, form, field):
        if field.data and field.data.startswith("00"):
            raise ValidationError(self.message)


class MustContainAlphanumericCharacters:

    regex = re.compile(r".*[a-zA-Z0-9].*[a-zA-Z0-9].*")

    def __init__(self, message="Must include at least two alphanumeric characters"):
        self.message = message

    def __call__(self, form, field):
        if field.data and not re.match(self.regex, field.data):
            raise ValidationError(self.message)


class CharactersNotAllowed:
    def __init__(self, characters_not_allowed, *, message=None):
        self.characters_not_allowed = OrderedSet(characters_not_allowed)
        self.message = message

    def __call__(self, form, field):
        illegal_characters = self.characters_not_allowed.intersection(field.data)

        if illegal_characters:
            if self.message:
                raise ValidationError(self.message)
            raise ValidationError(
                f"Cannot contain "
                f'{formatted_list(illegal_characters, conjunction="or", before_each="", after_each="")}'
            )


class StringsNotAllowed:
    def __init__(self, *args, message=None, match_on_substrings=False):
        self.strings_not_allowed = OrderedSet(string.lower() for string in args)
        self.match_on_substrings = match_on_substrings
        self.message = message

    def __call__(self, form, field):
        normalised = field.data.lower()
        for not_allowed in self.strings_not_allowed:
            if normalised == not_allowed or (self.match_on_substrings and not_allowed in normalised):
                if self.message:
                    raise ValidationError(self.message)
                raise ValidationError(f"Cannot {'contain' if self.match_on_substrings else 'be'} ‘{not_allowed}’")


class FileIsVirusFree:
    def __call__(self, form, field):
        if field.data:
            if current_app.config["ANTIVIRUS_ENABLED"]:
                try:
                    virus_free = antivirus_client.scan(field.data)
                    if not virus_free:
                        raise StopValidation("Your file contains a virus")
                finally:
                    field.data.seek(0)
