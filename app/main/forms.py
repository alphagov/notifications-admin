import weakref
from contextlib import suppress
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from functools import partial
from html import escape
from itertools import chain
from math import ceil
from numbers import Number

import pytz
from flask import request
from flask_login import current_user
from flask_wtf import FlaskForm as Form
from flask_wtf.file import FileAllowed, FileSize
from flask_wtf.file import FileField as FileField_wtf
from markupsafe import Markup
from notifications_utils.countries.data import Postage
from notifications_utils.formatters import strip_all_whitespace
from notifications_utils.insensitive_dict import InsensitiveDict, InsensitiveSet
from notifications_utils.recipient_validation.email_address import validate_email_address
from notifications_utils.recipient_validation.errors import InvalidEmailError, InvalidPhoneError
from notifications_utils.recipient_validation.notifynl.phone_number import PhoneNumber as PhoneNumberUtils
from notifications_utils.recipient_validation.postal_address import PostalAddress
from notifications_utils.safe_string import make_string_safe_for_email_local_part
from notifications_utils.timezones import local_timezone, utc_string_to_aware_gmt_datetime
from ordered_set import OrderedSet
from werkzeug.utils import cached_property
from wtforms import (
    BooleanField,
    DateField,
    EmailField,
    Field,
    FieldList,
    FileField,
    HiddenField,
    PasswordField,
    SearchField,
    SelectMultipleField,
    StringField,
    TelField,
    TextAreaField,
    ValidationError,
    validators,
)
from wtforms import RadioField as WTFormsRadioField
from wtforms.validators import (
    DataRequired,
    InputRequired,
    NumberRange,
    Optional,
    Regexp,
    StopValidation,
)

from app import asset_fingerprinter, current_organisation
from app.constants import (
    SERVICE_JOIN_REQUEST_APPROVED,
    SERVICE_JOIN_REQUEST_REJECTED,
    SIGN_IN_METHOD_TEXT,
    SIGN_IN_METHOD_TEXT_OR_EMAIL,
    LetterLanguageOptions,
)
from app.formatters import (
    format_auth_type,
    format_date_human,
    format_thousands,
    get_human_day,
    guess_name_from_email_address,
    message_count_noun,
    sentence_case,
)
from app.main.validators import (
    CannotContainURLsOrLinks,
    CharactersNotAllowed,
    CommonlyUsedPassword,
    CsvFileValidator,
    DoesNotStartWithDoubleZero,
    FileIsVirusFree,
    IsAUKMobileNumberOrShortCode,
    IsNotAGenericSenderID,
    IsNotAPotentiallyMaliciousSenderID,
    IsNotLikeNHSNoReply,
    Length,
    MustContainAlphanumericCharacters,
    NoCommasInPlaceHolders,
    NoEmbeddedImagesInSVG,
    NoTextInSVG,
    NotifyDataRequired,
    NotifyInputRequired,
    NotifyUrlValidator,
    OnlySMSCharacters,
    StringsNotAllowed,
    ValidEmail,
    ValidGovEmail,
    ValidPhoneNumber,
)
from app.models.branding import (
    GOVERNMENT_IDENTITY_SYSTEM_COLOURS,
    get_government_identity_system_crests_or_insignia,
)
from app.models.feedback import PROBLEM_TICKET_TYPE, QUESTION_TICKET_TYPE
from app.models.organisation import Organisation
from app.utils import branding
from app.utils.govuk_frontend_field import (
    GovukFrontendWidgetMixin,
    render_govuk_frontend_macro,
)
from app.utils.image_processing import CorruptImage, ImageProcessor, WrongImageFormat
from app.utils.user_permissions import (
    all_ui_permissions,
    organisation_user_permission_names,
    organisation_user_permission_options,
    permission_options,
)


def get_time_value_and_label(future_time):
    return (
        future_time.replace(tzinfo=None).isoformat(),
        f"{get_human_day(future_time, include_day_of_week=True).title()} at {get_human_time(future_time)}",
    )


def get_human_time(time):
    time = utc_string_to_aware_gmt_datetime(time)
    return {"0": "midnight", "12": "midday"}.get(time.strftime("%-H"), time.strftime("%-I%p").lower())


def get_furthest_possible_scheduled_time():
    return (datetime.now(local_timezone) + timedelta(days=7)).replace(hour=0, minute=0, second=0)


def get_next_hours_until(until):
    now = datetime.now(UTC)
    hours = ceil((until - now).total_seconds() / (60 * 60))
    return [
        (now + timedelta(hours=i)).replace(minute=0, second=0, microsecond=0).replace(tzinfo=pytz.utc)
        for i in range(1, hours + 1)
    ]


def get_next_days_until(until):
    now = datetime.now(UTC)
    days = int((until - now).total_seconds() / (60 * 60 * 24))

    return [
        get_human_day((now + timedelta(days=i)).replace(tzinfo=pytz.utc), include_day_of_week=True).title()
        for i in range(days + 1)
    ]


class RadioField(WTFormsRadioField):
    def __init__(self, *args, thing="an option", **kwargs):
        super().__init__(*args, **kwargs)
        self.thing = thing
        self.validate_choice = False

    def pre_validate(self, form):
        super().pre_validate(form)
        if self.data not in dict(self.choices).keys():
            raise ValidationError(f"Select {self.thing}")


def make_email_address_field(label="Email address", *, gov_user: bool, required=True, thing=None):
    if thing:
        validators = [
            ValidEmail(message=f"Enter {thing} in the correct format, like name@example.gov.uk"),
        ]
    else:
        # FIXME: being deprecated; remove this when all form fields have been transferred across to `thing`.
        validators = [
            ValidEmail(),
        ]

    if gov_user:
        validators.append(ValidGovEmail())

    if required:
        if thing:
            validators.append(NotifyDataRequired(thing=thing))
        else:
            # FIXME: being deprecated; prefer to pass in `thing`.
            validators.append(DataRequired(message="Cannot be empty"))

    return GovukEmailField(label, validators)


class RequiredValidatorsMixin(Field):
    """
    A mixin for use if there are ever required validators you want to always apply, regardless of what a subclass does
    or how the field is invoked.

    Normally if you pass `validators` in a Field.__init__, that list overrides any base class validators entirely.
    This isn't always desirable, for example, we might want to ensure that all our files are virus scanned regardless
    of whether they pass other validators (filesize, is the file openable, etc)

    To set these, use this mixin then specify `required_validators` as a class variable.
    Note that these validators will be run before any other validators passed in through the field constructor.

    This inherits from Field to ensure that it gets invoked before the `Field` constructor
    (which actually takes the validators and saves them)
    """

    required_validators = []

    def __init__(self, *args, validators=None, **kwargs):
        if validators is None:
            validators = []
        # make a copy of `self.required_validators` to ensure it's not shared with other instances of this field
        super().__init__(*args, validators=(self.required_validators[:] + validators), **kwargs)


class GovukTextInputFieldMixin(GovukFrontendWidgetMixin):
    input_type = "text"
    govuk_frontend_component_name = "text-input"

    def prepare_params(self, **kwargs):
        value = kwargs["value"] if "value" in kwargs else self._value()
        value = str(value) if isinstance(value, Number) else value

        error_message_format = "html" if kwargs.get("error_message_with_html") else "text"

        # convert to parameters that govuk understands
        params = {
            "classes": "govuk-!-width-two-thirds",
            "errorMessage": self.get_error_message(error_message_format),
            "id": self.id,
            "label": {"text": self.label.text},
            "name": self.name,
            "value": value if value else None,
            "type": self.input_type,
        }

        return params


class PhoneNumber(GovukTextInputFieldMixin, TelField):
    input_type = "tel"


def valid_phone_number(label="Mobile number", international=False, sms_to_uk_landline=False):
    if not (sms_to_uk_landline or international):
        return PhoneNumber(
            label,
            validators=[
                DataRequired(message="Cannot be empty"),
                ValidPhoneNumber(allow_international_sms=international),
            ],
        )
    else:
        return PhoneNumber(
            label,
            validators=[
                NotifyDataRequired(thing="a mobile number"),
                ValidPhoneNumber(
                    allow_sms_to_uk_landlines=sms_to_uk_landline,
                    allow_international_sms=international,
                ),
            ],
        )


def make_password_field(label="Password", thing="a password", validate_length=True):
    validators = [
        NotifyDataRequired(thing=thing),
        CommonlyUsedPassword(message="Choose a password that’s harder to guess"),
    ]

    if validate_length:
        validators.insert(1, Length(min=8, max=255, thing=thing))

    return GovukPasswordField(
        label,
        validators=validators,
    )


class GovukTextInputField(GovukTextInputFieldMixin, StringField):
    pass


class GovukPasswordField(GovukTextInputFieldMixin, PasswordField):
    input_type = "password"


class GovukEmailField(GovukTextInputFieldMixin, EmailField):
    input_type = "email"
    param_extensions = {"spellcheck": False}  # email addresses don't need to be spellchecked


class GovukSearchField(GovukTextInputFieldMixin, SearchField):
    input_type = "search"
    param_extensions = {"classes": "govuk-!-width-full"}


class GovukTextareaField(GovukFrontendWidgetMixin, TextAreaField):
    govuk_frontend_component_name = "textarea"

    def prepare_params(self, **kwargs):
        params = {
            "name": self.name,
            "id": self.id,
            "rows": 8,
            "label": {"text": self.label.text, "classes": None, "isPageHeading": False},
            "hint": None,
            "errorMessage": self.get_error_message(),
            "value": self._value(),
        }

        return params


class NotifyDateField(DateField):
    """A thin wrapper around WTForm's DateField providing our own error message."""

    def __init__(self, label=None, validators=None, format="%Y-%m-%d", thing="a date", **kwargs):
        super().__init__(label, validators, format, **kwargs)
        self.thing = thing

    def process_formdata(self, valuelist):
        try:
            super().process_formdata(valuelist)
        except ValueError as e:
            raise ValueError(f"Enter {self.thing} in the correct format") from e


class GovukDateField(GovukTextInputFieldMixin, NotifyDateField):
    pass


class SMSCode(GovukTextInputField):
    # the design system recommends against ever using `type="number"`. "tel" makes mobile browsers
    # show a phone keypad input rather than a full qwerty keyboard.
    input_type = "tel"
    param_extensions = {
        "attributes": {
            "pattern": "[0-9]*",
            "data-notify-module": "autofocus",
        },
        "classes": "govuk-input govuk-input--width-5 govuk-input--extra-letter-spacing",
    }
    validators = [
        NotifyDataRequired(thing="your text message code"),
        Regexp(regex=r"^\d+$", message="Numbers only"),
        Length(min=5, max=5, thing="security code", unit="digits"),
    ]

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = InsensitiveDict.make_key(valuelist[0])


class GovukIntegerField(GovukTextInputField):
    #  Actual value is 2,147,483,647 but this is a scary looking arbitrary number
    POSTGRES_MAX_INT = 2_000_000_000

    def __init__(self, label=None, *, things, **kwargs):
        self.things = things
        super().__init__(label, **kwargs)

    def process_formdata(self, valuelist):
        if valuelist:
            value = valuelist[0].replace(",", "").replace(" ", "")

            for type_ in (int, float):
                with suppress(ValueError):
                    value = type_(value)
                    break

            if value == "":
                value = 0

        return super().process_formdata([value])

    def pre_validate(self, form):
        if self.data:
            if not isinstance(self.data, int):
                raise StopValidation(f"Enter {self.things} in digits")

            if self.data > self.POSTGRES_MAX_INT:
                raise ValidationError(
                    f"{sentence_case(self.things)} must be {format_thousands(self.POSTGRES_MAX_INT)} or less"
                )

        return super().pre_validate(form)

    def __call__(self, **kwargs):
        if not hasattr(self, "get_form"):
            # If the field is unbound – not yet attached to a Form instance – then
            # it won’t have a submitted value yet so we can return early
            return super().__call__(**kwargs)

        if self.get_form().is_submitted() and not self.get_form().validate():
            return super().__call__(value=(self.raw_data or [None])[0], **kwargs)

        try:
            value = int(self.data)
            value = format_thousands(value)
        except (ValueError, TypeError):
            value = self.data if self.data is not None else ""

        return super().__call__(value=value, **kwargs)


class HexColourCodeField(GovukTextInputField, RequiredValidatorsMixin):
    required_validators = [
        Regexp(regex="^$|^#?(?:[0-9a-fA-F]{3}){1,2}$", message="Enter a hex colour code in the correct format"),
    ]
    param_extensions = {
        "prefix": {
            "text": "#",
        },
        "classes": "govuk-input--width-6",
        "attributes": {"data-notify-module": "colour-preview"},
    }

    def _value(self):
        return self.data[1:] if self.data and self.data.startswith("#") else self.data

    def post_validate(self, form, validation_stopped):
        if not self.errors:
            if self.data and not self.data.startswith("#"):
                self.data = "#" + self.data


class FieldWithNoneOption:
    # This is a special value that is specific to our forms. This is
    # more expicit than casting `None` to a string `'None'` which can
    # have unexpected edge cases
    NONE_OPTION_VALUE = "__NONE__"

    # When receiving Python data, eg when instantiating the form object
    # we want to convert that data to our special value, so that it gets
    # recognised as being one of the valid choices
    def process_data(self, value):
        self.data = self.NONE_OPTION_VALUE if value is None else value

    # After validation we want to convert it back to a Python `None` for
    # use elsewhere, eg posting to the API
    def post_validate(self, form, validation_stopped):
        if self.data == self.NONE_OPTION_VALUE and not validation_stopped:
            self.data = None


class RadioFieldWithNoneOption(FieldWithNoneOption, RadioField):
    pass


class NestedFieldMixin:
    def children(self):
        # start map with root option as a single child entry
        child_map = {None: [option for option in self if option.data == self.NONE_OPTION_VALUE]}

        # add entries for all other children
        for option in self:
            # assign all options with a NONE_OPTION_VALUE (not always None) to the None key
            if option.data == self.NONE_OPTION_VALUE:
                child_ids = [folder["id"] for folder in self.all_template_folders if folder["parent_id"] is None]
                key = self.NONE_OPTION_VALUE
            else:
                child_ids = [folder["id"] for folder in self.all_template_folders if folder["parent_id"] == option.data]
                key = option.data

            child_map[key] = [option for option in self if option.data in child_ids]

        return child_map

    # to be used as the only version of .children once radios are converted
    @cached_property
    def _children(self):
        return self.children()

    def get_items_from_options(self, field):
        items = []

        for option in self._children[None]:
            item = self.get_item_from_option(option)
            if option.data in self._children:
                item["children"] = self.render_children(field.name, option.label.text, self._children[option.data])
            items.append(item)

        return items

    def render_children(self, name, label, options):
        params = {
            "name": name,
            "fieldset": {"legend": {"text": label, "classes": "govuk-visually-hidden"}},
            "formGroup": {"classes": "govuk-form-group--nested"},
            "asList": True,
            "items": [],
        }
        for option in options:
            item = self.get_item_from_option(option)

            if len(self._children[option.data]):
                item["children"] = self.render_children(name, option.label.text, self._children[option.data])

            params["items"].append(item)

        return render_govuk_frontend_macro(self.govuk_frontend_component_name, params=params)


class NestedCheckboxesField(SelectMultipleField, NestedFieldMixin):
    NONE_OPTION_VALUE = None


class HiddenFieldWithNoneOption(FieldWithNoneOption, HiddenField):
    pass


class OrderableFieldsForm(Form):
    """Can be used to force fields to be iterated in a specific order.

    WTForms will iterate over fields on a form in the order that they are instantiated at runtime (this is generally
    top-down as you read through the file). This order is sometimes different from the order that fields are displayed
    on the page. With simple forms this is easy - we can just reorder the fields in the class declaration. However,
    we have a number of forms that have inheritance chains, which makes reordering more difficult.

    Where we are using forms with inheritance and display fields in a different order than they're created for the form,
    we can use `custom_field_order` to rejig the fields. In particular this may be important to get error messages
    displaying in error summaries to match the order of forms visually on the page.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if hasattr(self, "custom_field_order"):
            from flask import current_app

            custom_field_order = self.custom_field_order
            if current_app.config["WTF_CSRF_ENABLED"]:
                custom_field_order = ("csrf_token",) + custom_field_order

            unlisted_fields = set(self._fields).symmetric_difference(set(custom_field_order))
            if unlisted_fields:
                raise RuntimeError(
                    "When setting `OrderableFieldsForm.custom_field_order`, all fields must be listed exhaustively. "
                    f"The following fields are missing: {unlisted_fields}."
                )

            self._fields = {fieldname: self._fields[fieldname] for fieldname in custom_field_order}


class StripWhitespaceForm(OrderableFieldsForm):
    class Meta:
        def bind_field(self, form, unbound_field, options):
            # FieldList simply doesn't support filters.
            # @see: https://github.com/wtforms/wtforms/issues/148
            no_filter_fields = (FieldList, PasswordField, GovukPasswordField)
            filters = [strip_all_whitespace] if not issubclass(unbound_field.field_class, no_filter_fields) else []
            filters += unbound_field.kwargs.get("filters", [])
            bound = unbound_field.bind(form=form, filters=filters, **options)
            bound.get_form = weakref.ref(form)  # GC won't collect the form if we don't use a weakref
            return bound

        def render_field(self, field, render_kw):
            render_kw.setdefault("required", False)
            return super().render_field(field, render_kw)


class StripWhitespaceStringField(GovukTextInputField):
    def __init__(self, label=None, **kwargs):
        kwargs["filters"] = tuple(
            chain(
                kwargs.get("filters", ()),
                (strip_all_whitespace,),
            )
        )
        super(GovukTextInputField, self).__init__(label, **kwargs)


class PostalAddressField(GovukTextareaField):
    def process_formdata(self, valuelist):
        if valuelist:
            self.data = PostalAddress(valuelist[0]).normalised


class VirusScannedFileField(FileField_wtf, RequiredValidatorsMixin):
    required_validators = [
        FileIsVirusFree(),
    ]


class LoginForm(StripWhitespaceForm):
    email_address = make_email_address_field(gov_user=False, thing="your email address")
    password = GovukPasswordField("Password", validators=[NotifyDataRequired(thing="your password")])


class RegisterUserForm(StripWhitespaceForm):
    name = GovukTextInputField(
        "Full name",
        validators=[
            NotifyDataRequired(thing="your full name"),
            CannotContainURLsOrLinks(thing="your full name"),
        ],
    )
    email_address = make_email_address_field(gov_user=True, thing="your email address")
    mobile_number = valid_phone_number(international=True)
    password = make_password_field(thing="your password")
    # always register as sms type
    auth_type = HiddenField("auth_type", default="sms_auth")


class RegisterUserFromInviteForm(RegisterUserForm):
    custom_field_order = (
        "name",
        "mobile_number",
        "password",
        "service",
        "email_address",
        "auth_type",
    )

    def __init__(self, invited_user):
        super().__init__(
            service=invited_user.service,
            email_address=invited_user.email_address,
            auth_type=invited_user.auth_type,
            name=guess_name_from_email_address(invited_user.email_address),
        )

    mobile_number = PhoneNumber("Mobile number", validators=[ValidPhoneNumber(allow_international_sms=True)])
    service = HiddenField("service")
    email_address = HiddenField("email_address")
    auth_type = HiddenField("auth_type", validators=[DataRequired()])

    def validate_mobile_number(self, field):
        if self.auth_type.data == "sms_auth" and not field.data:
            raise ValidationError("Enter your mobile number")


class RegisterUserFromOrgInviteForm(StripWhitespaceForm):
    def __init__(self, invited_org_user):
        super().__init__(
            organisation=invited_org_user.organisation,
            email_address=invited_org_user.email_address,
        )

    name = GovukTextInputField("Full name", validators=[NotifyDataRequired(thing="your full name")])

    mobile_number = PhoneNumber(
        "Mobile number",
        validators=[
            NotifyDataRequired(thing="your mobile number"),
            ValidPhoneNumber(allow_international_sms=True),
        ],
    )
    password = make_password_field(thing="your password")
    organisation = HiddenField("organisation")
    email_address = HiddenField("email_address")
    auth_type = HiddenField("auth_type", validators=[DataRequired()])


class GovukCheckboxField(GovukFrontendWidgetMixin, BooleanField):
    govuk_frontend_component_name = "checkbox"

    def prepare_params(self, **kwargs):
        params = {
            "name": self.name,
            "errorMessage": self.get_error_message(),
            "items": [
                {
                    "name": self.name,
                    "id": self.id,
                    "text": self.label.text,
                    "value": self._value(),
                    "checked": self.data,
                }
            ],
        }
        return params


# based on work done by @richardjpope: https://github.com/richardjpope/recourse/blob/master/recourse/forms.py#L6
class GovukCheckboxesField(GovukFrontendWidgetMixin, SelectMultipleField):
    govuk_frontend_component_name = "checkbox"
    render_as_list = False

    def get_item_from_option(self, option):
        return {
            "name": option.name,
            "id": option.id,
            "text": option.label.text,
            "value": option._value(),
            "checked": option.checked,
        }

    def get_items_from_options(self, field):
        return [self.get_item_from_option(option) for option in field]

    @property
    def error_summary_id(self):
        items = self.get_items_from_options(self)
        if len(items) > 0:
            return items[0]["id"]

        return self.id

    def prepare_params(self, **kwargs):
        # returns either a list or a hierarchy of lists
        # depending on how get_items_from_options is implemented
        items = self.get_items_from_options(self)

        params = {
            "name": self.name,
            "fieldset": {
                "attributes": {"id": self.name},
                "legend": {"text": self.label.text, "classes": "govuk-fieldset__legend--s"},
            },
            "asList": self.render_as_list,
            "errorMessage": self.get_error_message(),
            "items": items,
        }

        return params


# Wraps checkboxes rendering in HTML needed by the collapsible JS
class GovukCollapsibleCheckboxesField(GovukCheckboxesField):
    param_extensions = {"hint": {"html": '<div class="selection-summary" role="region" aria-live="polite"></div>'}}

    def __init__(self, *args, field_label="", **kwargs):
        self.field_label = field_label
        super().__init__(*args, **kwargs)

    def widget(self, *args, **kwargs):
        checkboxes_string = super().widget(*args, **kwargs)

        # wrap the checkboxes HTML in the HTML needed by the collapsible JS
        result = Markup(
            f'<div class="selection-wrapper"'
            f'     data-notify-module="collapsible-checkboxes"'
            f'     data-field-label="{self.field_label}">'
            f"  {checkboxes_string}"
            f"</div>"
        )

        return result


# GovukCollapsibleCheckboxesField adds an ARIA live-region to the hint and wraps the render in HTML needed by the
# collapsible JS
# NestedFieldMixin puts the items into a tree hierarchy, pre-rendering the sub-trees of the top-level items
class GovukCollapsibleNestedCheckboxesField(NestedFieldMixin, GovukCollapsibleCheckboxesField):
    NONE_OPTION_VALUE = None
    render_as_list = True


class GovukRadiosField(GovukFrontendWidgetMixin, RadioField):
    govuk_frontend_component_name = "radios"

    class Divider(str):
        """
        Behaves like a normal string but can be used instead of a `(value, label)`
        pair as one of the items in `GovukRadiosField.choices`, for example:

            numbers = GovukRadiosField(choices=(
                (1, "One"),
                (2, "Two"),
                GovukRadiosField.Divider("or")
                (3, "Three"),
            ))

        When rendered it won’t appear as a choice the user can click, but instead
        as text in between the choices, as per:
        https://design-system.service.gov.uk/components/radios/#radio-items-with-a-text-divider
        """

        def __iter__(self):
            # This is what WTForms will use as the value of the choice. We will
            # throw this away, but needs to be unique, unguessable and impossible
            # to confuse with a real choice
            yield object()
            # This is what WTForms will use as the label, which we can later
            # use to see if the choice is actually a divider
            yield self

    def get_item_from_option(self, option):
        if isinstance(option.label.text, self.Divider):
            return {
                "divider": option.label.text,
            }
        return {
            "name": option.name,
            "id": option.id,
            "text": option.label.text,
            "value": option._value(),
            "checked": option.checked,
        }

    def get_items_from_options(self, field):
        return [self.get_item_from_option(option) for option in field]

    @property
    def error_summary_id(self):
        items = self.get_items_from_options(self)
        if len(items) > 0:
            return items[0]["id"]

        return self.id

    def prepare_params(self, **kwargs):
        # returns either a list or a hierarchy of lists
        # depending on how get_items_from_options is implemented
        items = self.get_items_from_options(self)

        return {
            "name": self.name,
            "fieldset": {
                "attributes": {"id": self.name},
                "legend": {
                    "text": self.label.text,
                    "classes": "govuk-fieldset__legend--s, govuk-!-font-weight-regular",
                },
            },
            "errorMessage": self.get_error_message(),
            "items": items,
        }


class OnOffField(GovukRadiosField):
    def __init__(self, label, choices=None, choices_for_error_message=None, *args, **kwargs):
        choices = choices or [
            (True, "On"),
            (False, "Off"),
        ]
        super().__init__(
            label,
            *args,
            choices=choices,
            thing=choices_for_error_message or f"{choices[0][1].lower()} or {choices[1][1].lower()}",
            **kwargs,
        )

    def process_formdata(self, valuelist):
        if valuelist:
            value = valuelist[0]
            self.data = (value == "True") if value in ["True", "False"] else value

    def iter_choices(self):
        for value, label in self.choices:
            # This overrides WTForms default behaviour which is to check
            # self.coerce(value) == self.data
            # where self.coerce returns a string for a boolean input
            yield (value, label, (self.data in {value, self.coerce(value)}), {})


class OrganisationTypeField(GovukRadiosField):
    def __init__(self, *args, include_only=None, validators=None, **kwargs):
        super().__init__(
            *args,
            choices=[
                (value, label)
                for value, label in Organisation.TYPE_LABELS.items()
                if not include_only or value in include_only
            ],
            thing="a type of organisation",
            validators=validators or [],
            **kwargs,
        )


class GovukRadiosFieldWithNoneOption(FieldWithNoneOption, GovukRadiosField):
    pass


class GovukNestedRadiosField(NestedFieldMixin, GovukRadiosFieldWithNoneOption):
    govuk_frontend_component_name = "nested-radios"
    param_extensions = {"formGroup": {"classes": "govuk-form-group--nested-radio"}}

    def render_children(self, name, label, options):
        params = {
            "name": name,
            "fieldset": {"legend": {"text": label, "classes": "govuk-visually-hidden "}},
            "items": [],
        }
        for option in options:
            item = self.get_item_from_option(option)
            item.update(
                {
                    "hint": {"text": self.option_hints.get(option.data, "")},
                }
            )
            if len(self._children[option.data]):
                item["children"] = self.render_children(name, option.label.text, self._children[option.data])

            params["items"].append(item)

        return render_govuk_frontend_macro(self.govuk_frontend_component_name, params=params)


class GovukRadiosWithImagesField(GovukRadiosField):
    govuk_frontend_component_name = "radios-with-images"

    param_extensions = {
        "classes": "govuk-radios--inline",
        "fieldset": {"legend": {"classes": "govuk-fieldset__legend--l", "isPageHeading": True}},
    }

    def __init__(self, label="", *, image_data, **kwargs):
        super(GovukRadiosField, self).__init__(label, **kwargs)

        self.image_data = image_data

    def get_item_from_option(self, option):
        # deepcopy to avoid mutating the same `dict` multiple times
        image_data = deepcopy(self.image_data[option.data])
        image_data["url"] = asset_fingerprinter.get_url(image_data["path"])
        return {
            "name": option.name,
            "id": option.id,
            "text": option.label.text,
            "value": str(option.data),  # to protect against non-string types like uuids
            "checked": option.checked,
            "image": image_data,
        }


class GovukRadiosFieldWithRequiredMessage(GovukRadiosField):
    def __init__(self, *args, required_message="Not a valid choice", **kwargs):
        self.required_message = required_message
        super().__init__(*args, **kwargs)

    def pre_validate(self, form):
        try:
            return super().pre_validate(form)
        except ValueError as e:
            raise ValidationError(self.required_message) from e


class ListEntryFieldList(FieldList):
    def __init__(self, *args, thing, **kwargs):
        super().__init__(*args, **kwargs)
        self.thing = thing


# guard against data entries that aren't a known permission
def filter_by_permissions(valuelist, permissions):
    if valuelist is None:
        return None
    else:
        return [entry for entry in valuelist if any(entry in option for option in permissions)]


class AuthTypeForm(StripWhitespaceForm):
    auth_type = GovukRadiosField(
        "Sign-in method",
        choices=[
            ("sms_auth", format_auth_type("sms_auth")),
            ("email_auth", format_auth_type("email_auth")),
        ],
    )


class PermissionsForm(StripWhitespaceForm):
    def __init__(self, all_template_folders=None, disable_sms_auth=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.folder_permissions.choices = []
        self.disable_sms_auth = disable_sms_auth
        if all_template_folders is not None:
            self.folder_permissions.all_template_folders = all_template_folders
            self.folder_permissions.choices = [
                (item["id"], item["name"]) for item in ([{"name": "Templates", "id": None}] + all_template_folders)
            ]

        # In a scenario where there is no mobile number for the user
        # the option to select sms_auth is disabled
        if self.disable_sms_auth:
            self.login_authentication.param_extensions = {
                "items": [
                    {
                        "hint": {
                            "text": "Not available because this team member has not added a "
                            "phone number to their account"
                        },
                        "disabled": True,
                    },
                    {"checked": True},
                ]
            }

    folder_permissions = GovukCollapsibleNestedCheckboxesField("Folders this team member can see", field_label="folder")

    login_authentication = GovukRadiosField(
        "Sign-in method",
        choices=[
            ("sms_auth", "Text message code"),
            ("email_auth", "Email link"),
        ],
        thing="a sign-in method",
        param_extensions={"fieldset": {"legend": {"classes": "govuk-fieldset__legend--s"}}},
    )

    permissions_field = GovukCheckboxesField(
        "Permissions",
        filters=[partial(filter_by_permissions, permissions=permission_options)],
        choices=list(permission_options),
        param_extensions={"hint": {"text": "All team members can see sent messages."}},
    )

    @property
    def permissions(self):
        return set(self.permissions_field.data)

    @classmethod
    def from_user_and_service(cls, user, service):
        if user.platform_admin:
            all_template_folders = None
            folder_permissions = None
        else:
            all_template_folders = service.all_template_folders
            folder_permissions = [
                folder["id"]
                for folder in all_template_folders
                if user.has_template_folder_permission(folder, service=service)
            ]

        form = cls(
            folder_permissions=folder_permissions,
            all_template_folders=all_template_folders,
            permissions_field=user.permissions_for_service(service.id) & all_ui_permissions,
            login_authentication=user.auth_type,
            disable_sms_auth=False if user.mobile_number else True,
        )

        # If a user logs in with a security key, we generally don't want a service admin to be able to change this.
        # As well as enforcing this in the backend, we need to delete the auth radios to prevent validation errors.
        if user.webauthn_auth:
            del form.login_authentication
        return form


class JoinServiceRequestApproveForm(StripWhitespaceForm):
    join_service_approve_request = GovukRadiosField(
        "",
        choices=[
            (SERVICE_JOIN_REQUEST_APPROVED, "Yes"),
            (SERVICE_JOIN_REQUEST_REJECTED, "No"),
        ],
        thing="an option",
        param_extensions={"fieldset": {"legend": {"classes": ""}}},
        default=SERVICE_JOIN_REQUEST_APPROVED,
    )


class OrganisationUserPermissionsForm(StripWhitespaceForm):
    permissions_field = GovukCheckboxesField(
        "Permissions",
        filters=[partial(filter_by_permissions, permissions=organisation_user_permission_options)],
        choices=[
            (value, f"This team member can {label.lower()}") for value, label in organisation_user_permission_options
        ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._restrict_permission_choices()

    def _restrict_permission_choices(self):
        # Remove any permissions that an org doesn't have access to
        self.permissions_field.choices = [
            (value, label)
            for value, label in self.permissions_field.choices
            if current_organisation.can_use_org_user_permission(value)
        ]

    @property
    def permissions(self):
        return set(self.permissions_field.data)

    @classmethod
    def from_user_and_organisation(cls, user, organisation, **kwargs):
        form = cls(
            permissions_field=user.permissions_for_organisation(organisation.id) & organisation_user_permission_names,
            **kwargs,
        )
        return form


class BaseInviteUserForm:
    email_address = make_email_address_field(gov_user=False, thing="an email address")

    def __init__(self, inviter_email_address, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inviter_email_address = inviter_email_address

    def validate_email_address(self, field):
        if current_user.platform_admin:
            return
        if field.data.lower() == self.inviter_email_address.lower():
            raise ValidationError("Enter an email address that is not your own")


class InviteUserForm(BaseInviteUserForm, PermissionsForm):
    custom_field_order: tuple = (
        "email_address",
        "permissions_field",
        "folder_permissions",
        "login_authentication",
    )


class InviteOrgUserForm(BaseInviteUserForm, OrganisationUserPermissionsForm):
    pass


class TwoFactorForm(StripWhitespaceForm):
    def __init__(self, validate_code_func, *args, **kwargs):
        """
        Keyword arguments:
        validate_code_func -- Validates the code with the API.
        """
        self.validate_code_func = validate_code_func
        super().__init__(*args, **kwargs)

    sms_code = SMSCode("Text message code")

    def validate(self, *args, **kwargs):
        if not self.sms_code.validate(self):
            return False

        is_valid, reason = self.validate_code_func(self.sms_code.data)

        if not is_valid:
            self.sms_code.errors.append(reason)
            return False

        return super().validate(*args, **kwargs)


class TextNotReceivedForm(StripWhitespaceForm):
    mobile_number = valid_phone_number(international=True)


class RenameServiceForm(StripWhitespaceForm):
    name = GovukTextInputField(
        "Service name",
        validators=[
            NotifyDataRequired(thing="a service name"),
            MustContainAlphanumericCharacters(thing="service name"),
        ],
    )

    def validate_name(self, field):
        """
        Validate that the email from name ("Service Name" <service.name@notifications.service.gov.uk)
        is under 320 characters (if it's over, SES will reject the email and we'll end up with technical errors)
        """
        normalised_service_name = make_string_safe_for_email_local_part(field.data)
        try:
            # TODO: should probs store this value in config["NOTIFY_EMAIL_DOMAIN"] or similar
            email = validate_email_address(f"{normalised_service_name}@notifications.service.gov.uk")
        except InvalidEmailError as e:
            raise ValidationError("Service name cannot include characters from a non-Latin alphabet") from e

        if len(f'"{field.data}" <{email}>') > 320:
            # This is a little white lie - the service name _can_ be longer, provided the normalised name is short so
            # that the whole email is under 320 characters. 143 is chosen because a 143 char name + 143 char normalised
            # name + 34 characters of email domain, quotes, angle brackets etc = 320 characters total.
            raise ValidationError("Service name cannot be longer than 143 characters")


class RenameOrganisationForm(StripWhitespaceForm):
    name = GovukTextInputField(
        "Organisation name",
        validators=[
            NotifyDataRequired(thing="your organisation name"),
            MustContainAlphanumericCharacters(thing="organisation name"),
            Length(max=255, thing="organisation name"),
        ],
    )


class AddGPOrganisationForm(StripWhitespaceForm):
    def __init__(self, *args, service_name="unknown", **kwargs):
        super().__init__(*args, **kwargs)
        self.same_as_service_name.label.text = f"Is your GP surgery called ‘{service_name}’?"
        self.service_name = service_name
        self.same_as_service_name.param_extensions = {
            "items": [
                {},
                {"conditional": {"html": self.name}},
            ]
        }

    def get_organisation_name(self):
        if self.same_as_service_name.data:
            return self.service_name
        return self.name.data

    same_as_service_name = OnOffField(
        "Is your GP surgery called the same name as your service?",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ],
        choices_for_error_message="‘yes‘ to confirm the name of your GP surgery",
    )

    name = GovukTextInputField(
        "What’s your GP surgery called?",
    )

    def validate_name(self, field):
        if self.same_as_service_name.data is False:
            if not field.data:
                raise ValidationError("Enter the name of your GP surgery")
        else:
            field.data = ""


class AddNHSLocalOrganisationForm(StripWhitespaceForm):
    def __init__(self, *args, organisation_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organisations.choices = organisation_choices

    organisations = GovukRadiosField(
        "Which NHS Trust or Integrated Care Board do you work for?",
        param_extensions={"fieldset": {"legend": {"classes": "govuk-visually-hidden"}}},
        thing="an NHS Trust or Integrated Care Board",
    )


class OrganisationOrganisationTypeForm(StripWhitespaceForm):
    organisation_type = OrganisationTypeField("What type of organisation is this?")


class OrganisationCrownStatusForm(StripWhitespaceForm):
    crown_status = GovukRadiosField(
        "Is this organisation a crown body?",
        choices=[
            ("crown", "Yes"),
            ("non-crown", "No"),
            ("unknown", "Not sure"),
        ],
        thing="yes if the organisation is a Crown body",
    )


class OrganisationAgreementSignedForm(StripWhitespaceForm):
    agreement_signed = GovukRadiosField(
        "Has this organisation signed the agreement?",
        choices=[
            ("yes", "Yes"),
            ("no", "No"),
            ("unknown", "No (but we have some service-specific agreements in place)"),
        ],
        thing="whether this organisation has signed the agreement",
        param_extensions={
            "items": [
                {"hint": {"text": "Users will be told their organisation has already signed the agreement"}},
                {"hint": {"text": "Users will be prompted to sign the agreement before they can go live"}},
                {"hint": {"text": "Users will not be prompted to sign the agreement"}},
            ]
        },
    )


class FieldInListEntry:
    def pre_validate(self, form):
        self.error_summary_messages = []
        super().pre_validate(form)


class StripWhitespaceStringFieldInListEntry(FieldInListEntry, StripWhitespaceStringField):
    pass


class AdminOrganisationDomainsForm(StripWhitespaceForm):
    def populate(self, domains_list):
        for index, value in enumerate(domains_list):
            self.domains[index].data = value

    domains = ListEntryFieldList(
        StripWhitespaceStringFieldInListEntry(
            "",
            validators=[
                CharactersNotAllowed("@"),
                StringsNotAllowed("nhs.uk", "nhs.net"),
                Optional(),
            ],
            default="",
        ),
        min_entries=30,
        max_entries=30,
        label="Domain names",
        thing="domain name",
    )


class CreateServiceForm(StripWhitespaceForm):
    name = GovukTextInputField(
        "Service name",
        validators=[
            DataRequired(message="Enter a service name"),
            MustContainAlphanumericCharacters(),
            Length(max=255, thing="service name"),
        ],
    )
    organisation_type = OrganisationTypeField("Who runs this service?")


class CreateNhsServiceForm(CreateServiceForm):
    organisation_type = OrganisationTypeField(
        "Who runs this service?",
        include_only={"nhs_central", "nhs_local", "nhs_gp"},
    )


class AdminNewOrganisationForm(
    RenameOrganisationForm,
    OrganisationOrganisationTypeForm,
    OrganisationCrownStatusForm,
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Don’t offer the ‘not sure’ choice
        self.crown_status.choices = self.crown_status.choices[:-1]

    name = GovukTextInputField(
        "Organisation name",
        validators=[
            NotifyDataRequired(thing="an organisation name"),
            MustContainAlphanumericCharacters(thing="organisation name"),
            Length(max=255, thing="organisation name"),
        ],
    )


class AdminServiceSMSAllowanceForm(StripWhitespaceForm):
    free_sms_allowance = GovukIntegerField(
        "Numbers of text message fragments per year",
        things="the number of text message fragments",
        validators=[
            NotifyInputRequired(thing="a number of text messages"),
            NumberRange(min=0, message="Number must be greater than or equal to 0"),
        ],
    )


class AdminServiceMessageLimitForm(StripWhitespaceForm):
    message_limit = GovukIntegerField("", things="the number of messages", validators=[])

    def __init__(self, notification_type, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.message_limit.label.text = f"Daily {message_count_noun(1, notification_type)} limit"
        self.message_limit.things = f"the number of {message_count_noun(999, notification_type)}"
        hint_text = f"Number of {message_count_noun(999, notification_type)} the service is allowed to send each day"
        if notification_type != "international_sms":
            self.message_limit.param_extensions = {"hint": {"text": hint_text}}

        self.message_limit.validators = [
            NotifyInputRequired(thing=f"a number of {message_count_noun(2, notification_type)}"),
            NumberRange(min=0, message="Number must be greater than or equal to 0"),
        ]


class AdminServiceRateLimitForm(StripWhitespaceForm):
    rate_limit = GovukIntegerField(
        "Number of messages the service can send in a rolling 60 second window",
        things="the number of messages",
        validators=[
            NotifyDataRequired(thing="a number of messages"),
            NumberRange(min=0, message="Number must be greater than or equal to 0"),
        ],
    )


class ConfirmPasswordForm(StripWhitespaceForm):
    def __init__(self, validate_password_func, *args, **kwargs):
        self.validate_password_func = validate_password_func
        super().__init__(*args, **kwargs)

    password = GovukPasswordField("Enter your password", validators=[NotifyDataRequired(thing="your password")])

    def validate_password(self, field):
        if not self.validate_password_func(field.data):
            raise ValidationError("Incorrect password")


class TemplateNameMixin:
    name = GovukTextInputField(
        "Template name",
        validators=[
            NotifyDataRequired(thing="Template name"),
            Length(max=255, thing="Template name"),
        ],
    )


class RenameTemplateForm(StripWhitespaceForm, TemplateNameMixin):
    pass


class BaseTemplateForm(StripWhitespaceForm):
    template_content = GovukTextareaField(
        "Message", validators=[NotifyDataRequired(thing="your message"), NoCommasInPlaceHolders()]
    )

    def __init__(self, *args, **kwargs):
        if "content" in kwargs:
            kwargs["template_content"] = kwargs["content"]
        super().__init__(*args, **kwargs)

    @property
    def new_template_data(self):
        new_template_data = {"content": self.template_content.data}

        if hasattr(self, "subject"):
            new_template_data["subject"] = self.subject.data

        if hasattr(self, "name"):
            new_template_data["name"] = self.name.data

        if hasattr(self, "has_unsubscribe_link"):
            new_template_data["has_unsubscribe_link"] = self.has_unsubscribe_link.data

        return new_template_data


class SMSTemplateForm(BaseTemplateForm, TemplateNameMixin):
    def validate_template_content(self, field):
        OnlySMSCharacters(template_type="sms")(None, field)


class LetterAddressForm(StripWhitespaceForm):
    def __init__(self, *args, allow_international_letters=False, **kwargs):
        self.allow_international_letters = allow_international_letters
        super().__init__(*args, **kwargs)

    address = PostalAddressField("Address", validators=[NotifyDataRequired(thing="an address")])

    def validate_address(self, field):
        address = PostalAddress(
            field.data,
            allow_international_letters=self.allow_international_letters,
        )

        if not address.has_enough_lines:
            raise ValidationError(f"Address must be at least {PostalAddress.MIN_LINES} lines long")

        if address.has_too_many_lines:
            raise ValidationError(f"Address must be no more than {PostalAddress.MAX_LINES} lines long")

        if address.has_invalid_country_for_bfpo_address:
            raise ValidationError(
                "The last line of a British Forces Post Office (BFPO) address cannot be the name of a country"
            )

        if not address.has_valid_last_line:
            if self.allow_international_letters:
                raise ValidationError("The last line of the address must be a UK postcode or the name of a country")
            if address.international:
                raise ValidationError("You do not have permission to send letters to other countries")
            raise ValidationError("Last line of the address must be a real UK postcode")

        if address.has_invalid_characters:
            raise ValidationError(
                "Address lines cannot start with any of the following characters: "
                + " ".join(PostalAddress.INVALID_CHARACTERS_AT_START_OF_ADDRESS_LINE)
            )

        if address.has_no_fixed_abode_address:
            raise ValidationError("Enter a real address")


class EmailTemplateForm(BaseTemplateForm, TemplateNameMixin):
    subject = GovukTextareaField("Subject", validators=[NotifyDataRequired(thing="the subject of the email")])
    has_unsubscribe_link = GovukCheckboxField(
        "Add an unsubscribe link",
        param_extensions={
            "items": [
                {
                    "hint": {"text": "You will see unsubscribe requests on the dashboard"},
                    "classes": "govuk-checkboxes__item--single-with-hint",
                }
            ],
        },
    )


class LetterTemplateForm(BaseTemplateForm, TemplateNameMixin):
    subject = GovukTextareaField("Heading", validators=[NotifyDataRequired(thing="a main heading for your letter")])
    template_content = GovukTextareaField(
        "Body text", validators=[NotifyDataRequired(thing="the body text of your letter"), NoCommasInPlaceHolders()]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get("letter_languages") == LetterLanguageOptions.welsh_then_english:
            self.subject.label.text = f"{self.subject.label.text} (English)"
            self.template_content.label.text = f"{self.template_content.label.text} (English)"


class WelshLetterTemplateForm(BaseTemplateForm, TemplateNameMixin):
    subject = GovukTextareaField("Heading (Welsh)", validators=[DataRequired(message="Cannot be empty")])
    template_content = GovukTextareaField(
        "Body text (Welsh)", validators=[DataRequired(message="Cannot be empty"), NoCommasInPlaceHolders()]
    )

    def __init__(self, *args, subject, content, letter_welsh_subject, letter_welsh_content, **kwargs):
        # Populate subject and template_content form fields using the Welsh template values; we can discard the English
        # data for this form.
        super().__init__(*args, subject=letter_welsh_subject, content=letter_welsh_content, **kwargs)

    @property
    def new_template_data(self):
        data = super().new_template_data

        if "subject" in data:
            data["letter_welsh_subject"] = data.pop("subject")

        if "content" in data:
            data["letter_welsh_content"] = data.pop("content")

        return data


class LetterTemplatePostageForm(StripWhitespaceForm):
    choices = [
        ("first", "First class"),
        ("second", "Second class"),
        ("economy", "Economy mail"),
    ]

    postage = GovukRadiosField(
        "Choose the postage for this letter template",
        choices=choices,
        thing="first class, second class or economy mail",
        validators=[DataRequired()],
    )


class LetterTemplateLanguagesForm(StripWhitespaceForm):
    languages = GovukRadiosField(
        "This will change the language used for the date and page numbers of your letter template.",
        choices=[
            (LetterLanguageOptions.english.value, "English only"),
            (LetterLanguageOptions.welsh_then_english.value, "Welsh followed by English"),
        ],
        validators=[InputRequired()],
    )


class LetterUploadPostageForm(StripWhitespaceForm):
    def __init__(self, *args, postage_zone, **kwargs):
        super().__init__(*args, **kwargs)

        if postage_zone != Postage.UK:
            self.postage.choices = [(postage_zone, "")]
            self.postage.data = postage_zone

    @property
    def show_postage(self):
        return len(self.postage.choices) > 1

    postage = GovukRadiosField(
        "Choose the postage for this letter",
        choices=[
            ("first", "First class"),
            ("second", "Second class"),
            ("economy", "Economy mail"),
        ],
        default="second",
        validators=[DataRequired()],
    )


class ForgotPasswordForm(StripWhitespaceForm):
    email_address = make_email_address_field(gov_user=False, thing="your email address")


class NewPasswordForm(StripWhitespaceForm):
    new_password = make_password_field(thing="your new password")


class ChangePasswordForm(StripWhitespaceForm):
    def __init__(self, validate_password_func, *args, **kwargs):
        self.validate_password_func = validate_password_func
        super().__init__(*args, **kwargs)

    old_password = make_password_field("Current password", thing="your current password", validate_length=False)
    new_password = make_password_field("New password", thing="your new password")

    def validate_old_password(self, field):
        if not self.validate_password_func(field.data):
            raise ValidationError("Incorrect password")


class CsvUploadForm(StripWhitespaceForm):
    file = FileField(
        "Add recipients",
        validators=[
            DataRequired(message="You need to chose a file to upload"),
            CsvFileValidator(),
            FileSize(max_size=10 * 1024 * 1024, message="The file must be smaller than 10MB"),
        ],
    )


class ChangeNameForm(StripWhitespaceForm):
    new_name = GovukTextInputField(
        "Change your name",
        validators=[
            NotifyDataRequired(thing="your name"),
            CannotContainURLsOrLinks(thing="your name"),
        ],
    )


class ChangeEmailForm(StripWhitespaceForm):
    def __init__(self, validate_email_func, *args, **kwargs):
        self.validate_email_func = validate_email_func
        super().__init__(*args, **kwargs)

    email_address = make_email_address_field(
        label="Change your email address",
        thing="an email address",
        gov_user=True,
    )

    def validate_email_address(self, field):
        # The validate_email_func can be used to call API to check if the email address is already in
        # use. We don't want to run that check for invalid email addresses, since that will cause an error.
        # If there are any other validation errors on the email_address, we should skip this check.
        if self.email_address.errors:
            return

        is_valid = self.validate_email_func(field.data)
        if is_valid:
            raise ValidationError("This email address is already in use")


class ChangeNonGovEmailForm(ChangeEmailForm):
    email_address = make_email_address_field(gov_user=False)


class ChangeMobileNumberForm(StripWhitespaceForm):
    mobile_number = valid_phone_number(label="Change your mobile number", international=True)


class ChooseTimeForm(StripWhitespaceForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scheduled_for.choices = [("", "Now")] + [
            get_time_value_and_label(hour) for hour in get_next_hours_until(get_furthest_possible_scheduled_time())
        ]
        self.scheduled_for.days = get_next_days_until(get_furthest_possible_scheduled_time())

    scheduled_for = GovukRadiosField(
        "When to send these messages",
        default="",
    )


class CreateKeyForm(StripWhitespaceForm):
    def __init__(self, existing_keys, *args, **kwargs):
        self.existing_key_names = InsensitiveSet(key.name for key in existing_keys if not key.expiry_date)
        super().__init__(*args, **kwargs)

    key_name = GovukTextInputField(
        "Name for this key", validators=[NotifyDataRequired(thing="a name for this API key")]
    )

    key_type = GovukRadiosField(
        "Type of key",
        thing="a type of API key",
    )

    def validate_key_name(self, key_name):
        if key_name.data in self.existing_key_names:
            raise ValidationError("A key with this name already exists")


class SupportType(StripWhitespaceForm):
    support_type = GovukRadiosField(
        "How can we help you?",
        choices=[
            (PROBLEM_TICKET_TYPE, "Report a problem"),
            (QUESTION_TICKET_TYPE, "Ask a question or give feedback"),
        ],
    )


class SupportRedirect(StripWhitespaceForm):
    who = GovukRadiosField(
        "What do you need help with?",
        choices=[
            ("public-sector", "I work in the public sector and need to send emails, text messages or letters"),
            ("public", "I’m a member of the public with a question for the government"),
        ],
    )


class FeedbackOrProblem(StripWhitespaceForm):
    feedback = GovukTextareaField("Your message", validators=[NotifyDataRequired(thing="your message")])
    name = GovukTextInputField("Name (optional)")
    email_address = make_email_address_field(
        label="Email address", gov_user=False, required=True, thing="your email address"
    )


class Triage(StripWhitespaceForm):
    severe = GovukRadiosField(
        "Did you get one of the following errors?",
        choices=[
            ("yes", "Yes"),
            ("no", "No"),
        ],
        thing="‘yes’ if it is an emergency",
    )


class EstimateUsageForm(StripWhitespaceForm):
    volume_email = GovukIntegerField(
        "How many emails do you expect to send in the next year?",
        things="the number of emails",
    )
    volume_sms = GovukIntegerField(
        "How many text messages do you expect to send in the next year?",
        things="the number of text messages",
    )
    volume_letter = GovukIntegerField(
        "How many letters do you expect to send in the next year?",
        things="the number of letters",
    )

    at_least_one_volume_filled = True

    def validate(self, *args, **kwargs):
        if self.volume_email.data == self.volume_sms.data == self.volume_letter.data == 0:
            self.at_least_one_volume_filled = False
            return False

        return super().validate(*args, **kwargs)


class AdminProviderRatioForm(OrderableFieldsForm):
    def __init__(self, providers):
        self._providers = providers

        # hack: https://github.com/wtforms/wtforms/issues/736
        self._unbound_fields = [
            (
                provider["identifier"],
                GovukIntegerField(
                    f"{provider['display_name']} (%)",
                    things="a percentage",
                    validators=[validators.NumberRange(min=0, max=100, message="Must be between 0 and 100")],
                    param_extensions={
                        "classes": "govuk-input--width-3",
                    },
                ),
            )
            for provider in providers
        ]

        super().__init__(data={provider["identifier"]: provider["priority"] for provider in providers})

    def validate(self, *args, **kwargs):
        if not super().validate(*args, **kwargs):
            return False

        total = sum(getattr(self, provider["identifier"]).data for provider in self._providers)

        if total == 100:
            return True

        for provider in self._providers:
            getattr(self, provider["identifier"]).errors += ["The total must add up to 100%"]

        return False


class ServiceContactDetailsForm(StripWhitespaceForm):
    contact_details_type = GovukRadiosField(
        "Type of contact details",
        choices=[
            ("url", "Link to a website"),
            ("email_address", "Email address"),
            ("phone_number", "Phone number"),
        ],
    )

    url = GovukTextInputField("URL", param_extensions={"hint": {"text": "For example, https://www.example.gov.uk"}})
    email_address = GovukEmailField("Email address")
    # This is a text field because the number provided by the user can also be a short code
    phone_number = GovukTextInputField("Phone number")

    def validate(self, *args, **kwargs):
        if self.contact_details_type.data == "url":
            self.url.validators = [
                NotifyDataRequired(thing="a URL in the correct format"),
                NotifyUrlValidator(),
            ]

        elif self.contact_details_type.data == "email_address":
            self.email_address.validators = [
                NotifyDataRequired(thing="an email address"),
                Length(min=5, max=255, thing="email address"),
                ValidEmail(),
            ]

        elif self.contact_details_type.data == "phone_number":
            # we can't use the existing phone number validation functions here since we want to allow landlines
            # and disallow emergency 3-digit numbers
            def valid_non_emergency_phone_number(self, num):
                try:
                    PhoneNumberUtils(num.data, is_service_contact_number=True)
                except InvalidPhoneError as e:
                    if e.code == InvalidPhoneError.Codes.UNSUPPORTED_EMERGENCY_NUMBER:
                        raise ValidationError(str(e)) from e
                    elif e.code == InvalidPhoneError.Codes.TOO_LONG:
                        # assume the number is an extension and return the number with minimal normalisation
                        return True

                    else:
                        raise ValidationError("Enter a phone number in the correct format") from e

                return True

            self.phone_number.validators = [
                NotifyDataRequired(thing="a phone number"),
                Length(min=3, max=20, thing="phone number"),
                valid_non_emergency_phone_number,
            ]

        return super().validate(*args, **kwargs)


class ServiceReplyToEmailForm(StripWhitespaceForm):
    email_address = make_email_address_field(label="Reply-to email address", thing="an email address", gov_user=False)
    is_default = GovukCheckboxField("Make this email address the default")


class ServiceSmsSenderForm(StripWhitespaceForm):
    sms_sender = GovukTextInputField(
        "Text message sender ID",
        validators=[
            NotifyDataRequired(thing="a text message sender ID"),
            Length(min=3, thing="text message sender ID"),
            Length(max=11, thing="text message sender ID"),
            Regexp(
                r"^[a-zA-Z0-9 &.\-_]+$",
                message=(
                    "Text message sender ID can only include letters, numbers, spaces, "
                    "and the following characters: & . - _"
                ),
            ),
            DoesNotStartWithDoubleZero(),
            IsNotAGenericSenderID(),
            IsNotAPotentiallyMaliciousSenderID(),
            IsAUKMobileNumberOrShortCode(),
            IsNotLikeNHSNoReply(),
        ],
    )
    is_default = GovukCheckboxField("Make this text message sender ID the default")


class ServiceEditInboundNumberForm(StripWhitespaceForm):
    is_default = GovukCheckboxField("Make this text message sender ID the default")


class AdminNotesForm(StripWhitespaceForm):
    notes = GovukTextareaField("Notes", validators=[])


class AdminBillingDetailsForm(StripWhitespaceForm):
    billing_contact_email_addresses = GovukTextInputField("Contact email addresses")
    billing_contact_names = GovukTextInputField("Contact names")
    billing_reference = GovukTextInputField("Reference")
    purchase_order_number = GovukTextInputField("Purchase order number")
    notes = GovukTextareaField("Notes", validators=[])


class ServiceLetterContactBlockForm(StripWhitespaceForm):
    letter_contact_block = GovukTextareaField(
        validators=[NotifyDataRequired(thing="a sender address"), NoCommasInPlaceHolders()]
    )
    is_default = GovukCheckboxField("Set as your default address")

    def validate_letter_contact_block(self, field):
        line_count = field.data.strip().count("\n")
        if line_count >= 10:
            raise ValidationError(f"This address is {line_count + 1} lines long - the most you can have is 10 lines")


class OnOffSettingForm(StripWhitespaceForm):
    def __init__(self, name, *args, truthy="On", falsey="Off", choices_for_error_message=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.enabled.label.text = name
        self.enabled.choices = [
            (True, truthy),
            (False, falsey),
        ]
        if choices_for_error_message:
            self.enabled.thing = choices_for_error_message

    enabled = OnOffField("Choices")


class YesNoSettingForm(OnOffSettingForm):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, truthy="Yes", falsey="No", choices_for_error_message="yes or no", **kwargs)


class ServiceSwitchChannelForm(OnOffSettingForm):
    def __init__(self, channel, *args, **kwargs):
        name = "Send {}".format(
            {
                "email": "emails",
                "sms": "text messages",
                "letter": "letters",
            }.get(channel)
        )

        super().__init__(name, *args, **kwargs)


class ServiceEmailSenderForm(StripWhitespaceForm):
    BAD_EMAIL_LOCAL_PARTS = {
        "noreply",
        "no.reply",
        "info",
        "support",
        "alert",
    }

    use_custom_email_sender_name = OnOffField(
        "Choose a sender name",
        choices_for_error_message="same or custom",
        choices=[
            (False, "Use the name of your service"),
            (True, "Enter a custom sender name"),
        ],
    )

    custom_email_sender_name = GovukTextInputField("Sender name", validators=[])

    def validate(self, *args, **kwargs):
        if self.use_custom_email_sender_name.data is True:
            self.custom_email_sender_name.validators = [
                NotifyDataRequired(thing="a sender name"),
                MustContainAlphanumericCharacters(thing="sender name"),
                Length(max=255, thing="sender name"),
            ]

        return super().validate(*args, **kwargs)

    def validate_custom_email_sender_name(self, field):
        """
        Validate that the email from name ("Sender Name" <sender.name@notifications.service.gov.uk)
        is under 320 characters (if it's over, SES will reject the email and we'll end up with technical errors)
        """
        if self.use_custom_email_sender_name.data is not True:
            return

        normalised_sender_name = make_string_safe_for_email_local_part(field.data)
        try:
            # TODO: should probs store this value in config["NOTIFY_EMAIL_DOMAIN"] or similar
            email = validate_email_address(f"{normalised_sender_name}@notifications.service.gov.uk")
        except InvalidEmailError as e:
            raise ValidationError("Sender name cannot include characters from a non-Latin alphabet") from e

        if len(f'"{field.data}" <{email}>') > 320:
            # This is a little white lie - the sender name _can_ be longer, provided the normalised name is short so
            # that the whole email is under 320 characters. 143 is chosen because a 143 char name + 143 char normalised
            # name + 34 characters of email domain, quotes, angle brackets etc = 320 characters total.
            raise ValidationError("Sender name cannot be longer than 143 characters")

        if normalised_sender_name in self.BAD_EMAIL_LOCAL_PARTS:
            raise ValidationError("Sender name needs to be more specific")

        with suppress(InvalidEmailError):
            validate_email_address(field.data)
            raise ValidationError("Sender name cannot be an email address")


class AdminSetEmailBrandingForm(StripWhitespaceForm):
    branding_style = GovukRadiosFieldWithNoneOption(
        "Branding style",
        param_extensions={"fieldset": {"legend": {"classes": "govuk-visually-hidden"}}},
        thing="a branding style",
    )

    DEFAULT = (FieldWithNoneOption.NONE_OPTION_VALUE, "GOV.UK")

    def __init__(self, all_branding_options, current_branding):
        super().__init__(branding_style=current_branding)

        self.branding_style.choices = sorted(
            all_branding_options + [self.DEFAULT],
            key=lambda branding: (
                branding[0] != current_branding,
                branding[0] is not self.DEFAULT[0],
                branding[1].lower(),
            ),
        )


class AdminSetLetterBrandingForm(AdminSetEmailBrandingForm):
    # form is the same, but instead of GOV.UK we have None as a valid option
    DEFAULT = (FieldWithNoneOption.NONE_OPTION_VALUE, "None")


class AdminPreviewBrandingForm(StripWhitespaceForm):
    branding_style = HiddenFieldWithNoneOption("branding_style")


class AdminEditEmailBrandingForm(StripWhitespaceForm):
    name = GovukTextInputField("Name of brand")
    text = GovukTextInputField("Logo text", param_extensions={"hint": {"text": "Text that appears beside the logo"}})
    alt_text = GovukTextInputField(
        "Alt text", param_extensions={"hint": {"text": "Text for people who cannot see the logo"}}
    )
    colour = HexColourCodeField("Colour")
    file = VirusScannedFileField("Upload a PNG logo", validators=[FileAllowed(["png"], "The logo must be a PNG file")])
    brand_type = GovukRadiosField(
        "Brand type",
        choices=[
            ("both", "GOV.UK and branding"),
            ("org", "Branding only"),
            ("org_banner", "Branding banner"),
        ],
    )

    def validate_name(self, name):
        op = request.form.get("operation")
        if op == "email-branding-details" and not self.name.data:
            raise ValidationError("Enter a name for the branding")

    def validate(self, *args, **kwargs):
        rv = super().validate(*args, **kwargs)

        op = request.form.get("operation")
        if op == "email-branding-details":
            # we only want to validate alt_text/text if we're editing the fields, not the file
            if self.alt_text.data:
                self.alt_text.data = escape(self.alt_text.data)

            if self.alt_text.data and self.text.data:
                self.alt_text.errors.append("Alt text must be empty if you have already entered logo text")
                return False

            if not (self.alt_text.data or self.text.data):
                self.alt_text.errors.append("Enter alt text for your logo")
                return False

        return rv


class DuplicatableHiddenField(HiddenField):
    """
    An instance of HiddenField which can be reused in multiple forms on the same
    page without being given the same ID.
    """

    def __init__(self, *args, **kwargs):
        self._call_index = 0
        super().__init__(*args, **kwargs)

    def __call__(self, **kwargs):
        self._call_index += 1
        return super().__call__(id=f"{self.name}_{self._call_index}", **kwargs)


class AdminChangeOrganisationDefaultEmailBrandingForm(StripWhitespaceForm):
    email_branding_id = DuplicatableHiddenField(
        "Email branding id",
        validators=[DataRequired()],
    )


class AdminChangeOrganisationDefaultLetterBrandingForm(StripWhitespaceForm):
    letter_branding_id = DuplicatableHiddenField(
        "Letter branding id",
        validators=[DataRequired()],
    )


class AddEmailBrandingOptionsForm(StripWhitespaceForm):
    branding_field = GovukCheckboxesField(
        "Branding options",
        validators=[DataRequired(message="Select at least 1 email branding option")],
        param_extensions={"fieldset": {"legend": {"classes": "govuk-visually-hidden"}}},
    )


class AddLetterBrandingOptionsForm(StripWhitespaceForm):
    branding_field = GovukCheckboxesField(
        "Branding options",
        validators=[DataRequired(message="Select at least 1 letter branding option")],
        param_extensions={"fieldset": {"legend": {"classes": "govuk-visually-hidden"}}},
    )


class AdminSetBrandingAddToBrandingPoolStepForm(StripWhitespaceForm):
    add_to_pool = GovukRadiosField(
        choices=[("yes", "Yes"), ("no", "No")],
        thing="yes or no",
        param_extensions={
            "fieldset": {
                "legend": {
                    # This removes the `govuk-fieldset__legend--s` class, thereby
                    # making the form label font regular weight, not bold
                    "classes": "",
                },
            }
        },
    )


class AdminEditLetterBrandingForm(StripWhitespaceForm):
    name = GovukTextInputField("Name of brand")

    def validate_name(self, name):
        op = request.form.get("operation")
        if op == "branding-details" and not self.name.data:
            raise ValidationError("Enter a name for the branding")


class AdminEditLetterBrandingSVGUploadForm(StripWhitespaceForm):
    file = VirusScannedFileField(
        "Upload an SVG logo",
        validators=[
            FileAllowed(["svg"], "The logo must be an SVG file"),
            DataRequired(message="You need to upload a file to submit"),
            NoEmbeddedImagesInSVG(),
            NoTextInSVG(),
        ],
    )


class LetterBrandingUploadBranding(StripWhitespaceForm):
    EXPECTED_BRANDING_FORMAT = "svg"

    branding = VirusScannedFileField(
        "Upload letter branding",
        validators=[
            FileAllowed(["svg"], "Branding must be an SVG file"),
            DataRequired(message="You need to upload a file to submit"),
            FileSize(max_size=2 * 1024 * 1024, message="The file must be smaller than 2MB"),
            NoEmbeddedImagesInSVG(),
            NoTextInSVG(),
        ],
    )


class LetterBrandingNameForm(StripWhitespaceForm):
    name = GovukTextInputField("Branding name", validators=[DataRequired(message="Cannot be empty")])


class EmailBrandingLogoUpload(StripWhitespaceForm):
    EXPECTED_LOGO_FORMAT = "png"

    logo = VirusScannedFileField(
        "Upload a logo",
        validators=[
            DataRequired(message="You need to upload a file to submit"),
            FileSize(max_size=2 * 1024 * 1024, message="The file must be smaller than 2MB"),
        ],
    )

    def validate_logo(self, field):
        from flask import current_app

        try:
            image_processor = ImageProcessor(field.data, img_format=self.EXPECTED_LOGO_FORMAT)
        except WrongImageFormat as e:
            raise ValidationError(f"Logo must be a {self.EXPECTED_LOGO_FORMAT.upper()} file") from e
        except CorruptImage as e:
            raise ValidationError("Notify cannot read this file") from e

        min_height_px = current_app.config["EMAIL_BRANDING_MIN_LOGO_HEIGHT_PX"]
        max_width_px = current_app.config["EMAIL_BRANDING_MAX_LOGO_WIDTH_PX"]

        # If it's not tall enough, it's probably not high quality enough to look good if we scale it up.
        if image_processor.height < min_height_px:
            raise ValidationError(f"Logo must be at least {min_height_px} pixels high")

        # If it's too wide, let's scale it down a bit.
        if image_processor.width > max_width_px:
            image_processor.resize(new_width=max_width_px)

        # If after scaling it down, it's not tall enough, let's pad the height as this will probably still look OK.
        if image_processor.height < min_height_px:
            image_processor.pad(to_height=min_height_px)

        field.data.stream = image_processor.get_data()


class PDFUploadForm(StripWhitespaceForm):
    file = VirusScannedFileField(
        "Upload a letter in PDF format",
        validators=[
            FileAllowed(["pdf"], "The file must be a PDF"),
            DataRequired(message="You need to choose a file to upload"),
            FileSize(max_size=2 * 1024 * 1024, message="The file must be smaller than 2MB"),
        ],
    )


class EmailFieldInGuestList(GovukEmailField, StripWhitespaceStringFieldInListEntry):
    pass


class PhoneNumberInGuestList(PhoneNumber, StripWhitespaceStringFieldInListEntry):
    pass


class GuestList(StripWhitespaceForm):
    def populate(self, email_addresses, phone_numbers):
        for form_field, existing_guest_list in (
            (self.email_addresses, email_addresses),
            (self.phone_numbers, phone_numbers),
        ):
            for index, value in enumerate(existing_guest_list):
                form_field[index].data = value

    email_addresses = ListEntryFieldList(
        EmailFieldInGuestList("", validators=[Optional(), ValidEmail()], default=""),
        min_entries=5,
        max_entries=5,
        label="Email addresses",
        thing="email address",
    )

    phone_numbers = ListEntryFieldList(
        PhoneNumberInGuestList("", validators=[Optional(), ValidPhoneNumber(allow_international_sms=True)], default=""),
        min_entries=5,
        max_entries=5,
        label="Mobile numbers",
        thing="mobile number",
    )


class RequiredDateFilterForm(StripWhitespaceForm):
    start_date = GovukDateField("Start date", thing="a start date")
    end_date = GovukDateField("End date", thing="an end date")


class BillingReportDateFilterForm(StripWhitespaceForm):
    start_date = GovukDateField("Start date", thing="a start date")
    end_date = GovukDateField("End date", thing="an end date")


class SearchByNameForm(StripWhitespaceForm):
    search = GovukSearchField(
        "Search by name",
        validators=[DataRequired("You need to enter full or partial name to search by.")],
    )


class SearchUsersForm(StripWhitespaceForm):
    search = GovukSearchField("Search by name or email address")


class SearchNotificationsForm(StripWhitespaceForm):
    to = GovukSearchField()

    labels = {
        "email": "Search by email address",
        "sms": "Search by phone number",
    }

    def __init__(self, message_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.to.label.text = self.labels.get(
            message_type,
            "Search by phone number or email address",
        )


class SearchTemplatesForm(StripWhitespaceForm):
    search = GovukSearchField()

    def __init__(self, api_keys, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search.label.text = "Search by name or ID" if api_keys else "Search by name"


class PlaceholderForm(StripWhitespaceForm):
    pass


class AdminServiceInboundNumberForm(StripWhitespaceForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inbound_number.choices = kwargs["inbound_number_choices"]

    inbound_number = GovukRadiosField(
        "Set inbound number",
        thing="an inbound number",
    )


class AdminServiceInboundNumberArchive(StripWhitespaceForm):
    removal_options = GovukRadiosField(
        "What do you want to do with the number?",
        choices=[("true", "Archive"), ("false", "Release")],
        validators=[DataRequired(message="Select an option")],
        param_extensions={
            "items": [
                {"hint": {"text": "No other services can use this phone number"}},
                {"hint": {"text": "Another service can use this phone number"}},
            ]
        },
    )


class CallbackForm(StripWhitespaceForm):
    url = GovukTextInputField(
        "URL",
        validators=[
            DataRequired(message="Cannot be empty"),
            Regexp(regex="^https.*", message="Must be a valid https URL"),
        ],
    )
    bearer_token = GovukPasswordField(
        "Bearer token",
        validators=[DataRequired(message="Cannot be empty"), Length(min=10, thing="the bearer token")],
    )

    def validate(self, *args, **kwargs):
        return super().validate(*args, **kwargs) or self.url.data == ""


class SMSPrefixForm(StripWhitespaceForm):
    enabled = OnOffField("")  # label is assigned on instantiation


def get_placeholder_form_instance(
    placeholder_name,
    dict_to_populate_from,
    template_type,
    allow_international_phone_numbers=False,
    allow_sms_to_uk_landline=False,
):
    if InsensitiveDict.make_key(placeholder_name) == "emailaddress" and template_type == "email":
        field = make_email_address_field(label=placeholder_name, gov_user=False, thing="an email address")
    elif InsensitiveDict.make_key(placeholder_name) == "phonenumber" and template_type == "sms":
        field = valid_phone_number(
            label=placeholder_name,
            international=allow_international_phone_numbers,
            sms_to_uk_landline=allow_sms_to_uk_landline,
        )
    else:
        field = GovukTextInputField(placeholder_name, validators=[DataRequired(message="Cannot be empty")])

    PlaceholderForm.placeholder_value = field

    return PlaceholderForm(placeholder_value=dict_to_populate_from.get(placeholder_name, ""))


class SetSenderForm(StripWhitespaceForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sender.choices = kwargs["sender_choices"]
        self.sender.label.text = kwargs["sender_label"]

    sender = GovukRadiosField()


class SetTemplateSenderForm(StripWhitespaceForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sender.choices = kwargs["sender_choices"]
        self.sender.label.text = "Select your sender"

    sender = GovukRadiosField()


class AdminSetOrganisationForm(StripWhitespaceForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organisations.choices = kwargs["choices"]

    organisations = GovukRadiosField("Select an organisation", validators=[DataRequired()])


class ChooseBrandingField(GovukRadiosField):
    FALLBACK_OPTION_VALUE = "something_else"
    FALLBACK_OPTION = (FALLBACK_OPTION_VALUE, "Something else")

    param_extensions = {
        "fieldset": {
            "legend": {
                # This removes the `govuk-fieldset__legend--s` class, thereby
                # making the form label font regular weight, not bold
                "classes": "",
            },
        },
    }

    def set_choices(self, choices):
        choices = OrderedSet(choices)
        if len(choices) > 2:
            choices = choices | {ChooseBrandingField.Divider("or")}
        self.choices = tuple(choices | {self.FALLBACK_OPTION})


class ChooseBrandingForm(StripWhitespaceForm):
    @property
    def something_else_is_only_option(self):
        return self.options.choices == (self.options.FALLBACK_OPTION,)


class ChooseEmailBrandingForm(ChooseBrandingForm):
    options = ChooseBrandingField("Choose your new email branding")

    def __init__(self, service):
        super().__init__()
        self.options.set_choices(branding.get_email_choices(service))


class ChooseLetterBrandingForm(ChooseBrandingForm):
    options = ChooseBrandingField("Choose your new letter branding")

    def __init__(self, service):
        super().__init__()
        self.options.set_choices(branding.get_letter_choices(service))


class BrandingRequestForm(StripWhitespaceForm):
    branding_request = GovukTextareaField(
        "Describe the branding you want",
        validators=[DataRequired("Cannot be empty")],
        param_extensions={
            "label": {
                "isPageHeading": True,
                "classes": "govuk-label--l",
            },
            "hint": {"text": "Include links to your brand guidelines or examples of how to use your branding."},
        },
    )


class GovernmentIdentityLogoForm(StripWhitespaceForm):
    logo_text = GovukTextInputField(
        "Enter the text that will appear in your logo",
        validators=[NotifyDataRequired(thing="the text that will appear in your logo")],
    )


class EmailBrandingChooseLogoForm(StripWhitespaceForm):
    BRANDING_OPTIONS_DATA = {
        "single_identity": {
            "label": "Create a government identity logo",
            "image": {
                "path": "images/branding/single_identity.png",
                "alt_text": "An example of an email with a government identity logo,"
                " including a blue stripe, a crest and department's name",
                "dimensions": {"width": 606, "height": 404},
            },
        },
        "org": {
            "label": "Upload a logo",
            "image": {
                "path": "images/branding/org.png",
                "alt_text": 'An example of an email with the heading "Your logo" in blue text on a white background.',
                "dimensions": {"width": 606, "height": 404},
            },
        },
    }

    branding_options = GovukRadiosWithImagesField(
        "Choose a logo for your emails",
        choices=tuple((key, value["label"]) for key, value in BRANDING_OPTIONS_DATA.items()),
        image_data={key: value["image"] for key, value in BRANDING_OPTIONS_DATA.items()},
    )


class EmailBrandingChooseBanner(OrderableFieldsForm):
    BANNER_CHOICES_DATA = {
        "org_banner": {
            "label": "Yes",
            "image": {
                "path": "images/branding/org_banner.png",
                "alt_text": "An example of an email with a logo on a blue banner.",
                "dimensions": {"width": 606, "height": 404},
            },
        },
        "org": {
            "label": "No",
            "image": {
                "path": "images/branding/org.png",
                "alt_text": "An example of an email with a logo on a clear background.",
                "dimensions": {"width": 606, "height": 404},
            },
        },
    }

    banner = GovukRadiosWithImagesField(
        "Does your logo appear on a coloured background?",
        choices=tuple((key, value["label"]) for key, value in BANNER_CHOICES_DATA.items()),
        image_data={key: value["image"] for key, value in BANNER_CHOICES_DATA.items()},
    )


class EmailBrandingChooseBannerColour(StripWhitespaceForm):
    hex_colour = HexColourCodeField("Choose a background colour", validators=[DataRequired()])


class EmailBrandingAltTextForm(StripWhitespaceForm):
    alt_text = GovukTextInputField("Alt text", validators=[DataRequired(message="Cannot be empty")])

    def validate_alt_text(self, field):
        if "logo" in field.data.lower():
            raise ValidationError("Do not include the word ‘logo’ in your alt text")


class SetServiceDataRetentionForm(StripWhitespaceForm):
    days_of_retention = GovukIntegerField(
        label="Number of days",
        things="the number of days",
        validators=[
            NotifyDataRequired(thing="a number of days"),
            validators.NumberRange(min=3, max=90, message="The number of days must be between 3 and 90"),
        ],
        param_extensions={"hint": {"text": "Must be between 3 and 90"}},
    )


class AdminServiceAddDataRetentionForm(StripWhitespaceForm):
    notification_type = GovukRadiosField(
        "What notification type?",
        choices=[
            ("email", "Email"),
            ("sms", "SMS"),
            ("letter", "Letter"),
        ],
        thing="a type of notification",
    )
    days_of_retention = GovukIntegerField(
        label="Days of retention",
        things="a number of days",
        validators=[validators.NumberRange(min=3, max=90, message="The number of days must be between 3 and 90")],
    )


class AdminServiceEditDataRetentionForm(StripWhitespaceForm):
    days_of_retention = GovukIntegerField(
        label="Days of retention",
        things="a number of days",
        validators=[validators.NumberRange(min=3, max=90, message="The number of days must be between 3 and 90")],
    )


class AdminReturnedLettersForm(StripWhitespaceForm):
    references = GovukTextareaField(
        "Letter references",
        validators=[
            NotifyDataRequired(thing="the returned letter references"),
        ],
    )


class TemplateFolderForm(StripWhitespaceForm):
    def __init__(self, all_service_users=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if all_service_users is not None:
            self.users_with_permission.all_service_users = all_service_users
            self.users_with_permission.choices = [(item.id, item.name) for item in all_service_users]

    users_with_permission = GovukCollapsibleCheckboxesField(
        "Team members who can see this folder", field_label="team member"
    )
    name = GovukTextInputField("Folder name", validators=[DataRequired(message="Cannot be empty")])


def required_for_ops(*operations):
    operations = set(operations)

    def validate(form, field):
        if form.op not in operations and any(field.raw_data):
            # super weird
            raise validators.StopValidation("Must be empty")
        if form.op in operations and not any(field.raw_data):
            raise validators.StopValidation("Enter a name for this folder")

    return validate


class TemplateAndFoldersSelectionForm(OrderableFieldsForm):
    """
    This form expects the form data to include an operation, based on which submit button is clicked.
    If enter is pressed, unknown will be sent by a hidden submit button at the top of the form.
    The value of this operation affects which fields are required, expected to be empty, or optional.

    * unknown
        currently not implemented, but in the future will try and work out if there are any obvious commands that can be
        assumed based on which fields are empty vs populated.
    * move-to-existing-folder
        must have data for templates_and_folders checkboxes, and move_to radios
    * move-to-new-folder
        must have data for move_to_new_folder_name, cannot have data for move_to_existing_folder_name
    * add-new-folder
        must have data for move_to_existing_folder_name, cannot have data for move_to_new_folder_name
    """

    ALL_TEMPLATES_FOLDER = {
        "name": "Templates",
        "id": RadioFieldWithNoneOption.NONE_OPTION_VALUE,
    }

    def __init__(
        self,
        all_template_folders,
        template_list,
        available_template_types,
        allow_adding_copy_of_template,
        option_hints,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.available_template_types = available_template_types

        self.templates_and_folders.choices = [(item.id, item.name) for item in template_list]

        self.op = None
        self.is_move_op = self.is_add_folder_op = self.is_add_template_op = False

        self.move_to.all_template_folders = all_template_folders

        self.move_to.option_hints = option_hints

        self.move_to.choices = [
            (item["id"], item["name"]) for item in ([self.ALL_TEMPLATES_FOLDER] + all_template_folders)
        ]

        self.add_template_by_template_type.choices = list(
            filter(
                None,
                [
                    ("email", "Email") if "email" in available_template_types else None,
                    ("sms", "Text message") if "sms" in available_template_types else None,
                    ("letter", "Letter") if "letter" in available_template_types else None,
                    ("copy-existing", "Copy an existing template") if allow_adding_copy_of_template else None,
                ],
            )
        )

    @property
    def trying_to_add_unavailable_template_type(self):
        return all(
            (
                self.is_add_template_op,
                self.add_template_by_template_type.data,
                self.add_template_by_template_type.data not in self.available_template_types,
            )
        )

    def is_selected(self, template_folder_id):
        return template_folder_id in (self.templates_and_folders.data or [])

    def validate(self, *args, **kwargs):
        self.op = request.form.get("operation")

        self.is_move_op = self.op in {"move-to-existing-folder", "move-to-new-folder"}
        self.is_add_folder_op = self.op in {"add-new-folder", "move-to-new-folder"}
        self.is_add_template_op = self.op in {"add-new-template"}

        if not (self.is_add_folder_op or self.is_move_op or self.is_add_template_op):
            return False

        return super().validate(*args, **kwargs)

    def get_folder_name(self):
        if self.op == "add-new-folder":
            return self.add_new_folder_name.data
        elif self.op == "move-to-new-folder":
            return self.move_to_new_folder_name.data
        return None

    templates_and_folders = GovukCheckboxesField(
        "Choose templates or folders",
        validators=[required_for_ops("move-to-new-folder", "move-to-existing-folder")],
        choices=[],  # added to keep order of arguments, added properly in __init__
        param_extensions={"fieldset": {"legend": {"classes": "govuk-visually-hidden"}}},
    )

    # if no default set, it is set to None, which process_data transforms to '__NONE__'
    # this means '__NONE__' (self.ALL_TEMPLATES option) is selected when no form data has been submitted
    # set default to empty string so process_data method doesn't perform any transformation
    move_to = GovukNestedRadiosField(
        "Choose a folder", default="", validators=[required_for_ops("move-to-existing-folder"), Optional()]
    )

    add_new_folder_name = GovukTextInputField("Folder name", validators=[required_for_ops("add-new-folder")])
    move_to_new_folder_name = GovukTextInputField("Folder name", validators=[required_for_ops("move-to-new-folder")])
    add_template_by_template_type = GovukRadiosFieldWithRequiredMessage(
        "New template",
        validators=[
            required_for_ops("add-new-template"),
            Optional(),
        ],
        required_message="Select the type of template you want to add",
    )


class AdminClearCacheForm(StripWhitespaceForm):
    model_type = GovukCheckboxesField("What do you want to clear today")

    def validate_model_type(self, field):
        if not field.data:
            raise ValidationError("Select at least one type of cache")


class AdminOrganisationGoLiveNotesForm(StripWhitespaceForm):
    request_to_go_live_notes = GovukTextareaField(
        "Go live notes",
        filters=[lambda x: x or None],
    )


class AcceptAgreementForm(StripWhitespaceForm):
    @classmethod
    def from_organisation(cls, org):
        if org.agreement_signed_on_behalf_of_name and org.agreement_signed_on_behalf_of_email_address:
            who = "someone-else"
        elif org.agreement_signed_version:  # only set if user has submitted form previously
            who = "me"
        else:
            who = None

        return cls(
            version=org.agreement_signed_version,
            who=who,
            on_behalf_of_name=org.agreement_signed_on_behalf_of_name,
            on_behalf_of_email=org.agreement_signed_on_behalf_of_email_address,
        )

    version = GovukTextInputField(
        "Which version of the agreement do you want to accept?",
        validators=[NotifyDataRequired(thing="a version number")],
    )

    who = GovukRadiosField(
        "Who are you accepting the agreement for?",
        choices=[
            (
                "me",
                "Yourself",
            ),
            (
                "someone-else",
                "Someone else",
            ),
        ],
    )

    on_behalf_of_name = GovukTextInputField("What’s their name?")

    on_behalf_of_email = make_email_address_field(
        "What’s their email address?",
        required=False,
        gov_user=True,
    )

    def __validate_if_nominating(self, field):
        error_messages = {
            "on_behalf_of_name": "Enter the name of the person accepting the agreement",
            "on_behalf_of_email": "Enter the email address of the person accepting the agreement",
        }

        if self.who.data == "someone-else":
            if not field.data:
                error_message = error_messages[field.name]
                raise ValidationError(error_message)
        else:
            field.data = ""

    validate_on_behalf_of_name = __validate_if_nominating
    validate_on_behalf_of_email = __validate_if_nominating

    def validate_version(self, field):
        try:
            float(field.data)
        except (TypeError, ValueError) as e:
            raise ValidationError("Enter a version number in digits, like 3.1") from e


class ChangeSecurityKeyNameForm(StripWhitespaceForm):
    security_key_name = GovukTextInputField(
        "Name of key",
        validators=[
            DataRequired(message="Enter a name for this key"),
            MustContainAlphanumericCharacters(thing="the name of the key"),
            Length(max=255, thing="the name of the key"),
        ],
    )


def markup_for_crest_or_insignia(filename):
    return Markup(
        f"""
        <img
            src="{asset_fingerprinter.get_url(f"images/branding/insignia/{filename}")}"
            alt=""
            class="email-branding-crest-or-insignia"
        >
    """
    )


def markup_for_coloured_stripe(colour):
    return Markup(
        f"""
        <span
            class="email-branding-coloured-stripe"
            style="background: {colour};"
        ></span>
    """
    )


class GovernmentIdentityCoatOfArmsOrInsignia(StripWhitespaceForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.coat_of_arms_or_insignia.choices = [
            (name, markup_for_crest_or_insignia(f"{name}.png") + name)
            for name in sorted(get_government_identity_system_crests_or_insignia())
        ]

    coat_of_arms_or_insignia = GovukRadiosField(
        "Coat of arms or insignia",
        thing="a coat of arms or insignia",
    )


class GovernmentIdentityColour(StripWhitespaceForm):
    def __init__(self, *args, crest_or_insignia_image_filename, **kwargs):
        super().__init__(*args, **kwargs)
        self.colour.choices = [
            (
                colour,
                (
                    markup_for_coloured_stripe(colour)
                    + markup_for_crest_or_insignia(crest_or_insignia_image_filename)
                    + name
                ),
            )
            for name, colour in GOVERNMENT_IDENTITY_SYSTEM_COLOURS.items()
        ]

    colour = GovukRadiosField(
        "Colour for stripe",
        thing="a colour for the stripe",
    )


class SetAuthTypeForm(StripWhitespaceForm):
    sign_in_method = GovukRadiosField(
        "Sign-in method",
        choices=(
            (SIGN_IN_METHOD_TEXT, "Text message code"),
            (SIGN_IN_METHOD_TEXT_OR_EMAIL, "Email link or text message code"),
        ),
    )


class SetEmailAuthForUsersForm(StripWhitespaceForm):
    def __init__(self, all_service_users=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if all_service_users is not None:
            self.users.all_service_users = all_service_users
            self.users.choices = sorted(
                [(user.id, user.email_address if user.is_invited_user else user.name) for user in all_service_users],
                key=lambda t: t[1].lower(),
            )

    users = GovukCheckboxesField("Choose who can sign in using an email link")


class PlatformAdminSearchForm(StripWhitespaceForm):
    search = GovukSearchField(
        "Search",
        validators=[NotifyDataRequired(thing="a search term")],
    )


class PlatformAdminUsersListForm(StripWhitespaceForm):
    created_from_date = GovukDateField("Created (From)", thing="a start date", validators=[Optional()])
    created_to_date = GovukDateField("Created (To)", thing="an end date", validators=[Optional()])
    logged_from_date = GovukDateField("Logged In (From)", thing="a start date", validators=[Optional()])
    logged_to_date = GovukDateField("Logged In (To)", thing="an end date", validators=[Optional()])

    take_part_in_research = GovukRadiosField(
        label="Research Opt In?",
        choices=[("yes", "Yes"), ("no", "No")],
        validators=[Optional()],
    )

    permissions_field = GovukCheckboxesField(
        "Permissions",
        filters=[partial(filter_by_permissions, permissions=permission_options)],
        choices=list(permission_options),
        param_extensions={"hint": {"text": "Select the permissions to filter by"}},
    )

    custom_field_order: tuple = (
        "permissions_field",
        "created_from_date",
        "created_to_date",
        "logged_from_date",
        "logged_to_date",
        "take_part_in_research",
    )

    def validate(self, extra_validators=None):
        if not (
            self.created_from_date.data
            or self.created_to_date.data
            or self.logged_from_date.data
            or self.logged_to_date.data
            or self.take_part_in_research.data
            or self.permissions_field.data
        ):
            self.form_errors = ("You must provide at least one filter option",)
            return False

        if self.created_from_date.data and self.created_to_date.data:
            if self.created_from_date.data > self.created_to_date.data:
                self.created_to_date.errors = ("The 'Created (To)' date must be after 'Created (From)'",)
                return False

        if self.logged_from_date.data and self.logged_to_date.data:
            if self.logged_from_date.data > self.logged_to_date.data:
                self.logged_to_date.errors = ("The 'Logged In (To)' date must be after 'Logged In (From)'",)
                return False

        return super().validate(extra_validators=extra_validators)


class UniqueServiceForm(StripWhitespaceForm):
    is_unique = GovukRadiosField(
        label="Is the service unique?",
        choices=[("yes", "Yes"), ("no", "No"), ("unsure", "I‘m not sure")],
        validators=[DataRequired(message="Select ‘yes’ if this service is unique")],
    )

    def __init__(self, service_name, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.is_unique.label.text = f"Is ‘{service_name}’ unique?"


class ServiceGoLiveDecisionForm(OnOffSettingForm):
    rejection_reason = GovukTextareaField("Enter the reason for your decision")

    def validate(self, *args, **kwargs):
        if self.enabled.data is False:
            self.rejection_reason.validators = [
                NotifyDataRequired(thing="a reason"),
            ]

        return super().validate(*args, **kwargs)


class JoinServiceForm(StripWhitespaceForm):
    def __init__(self, users, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.users.choices = [(user.id, user.name) for user in users]

        self.users.param_extensions["items"] = [
            {
                "hint": {
                    "text": (
                        f"Last used Notify {format_date_human(user.logged_in_at)}"
                        if user.logged_in_at
                        else "Never used Notify"
                    )
                }
            }
            for user in users
        ]

    users = GovukCheckboxesField(
        "Select at least one team member who can approve your request",
        validators=[DataRequired(message="Select at least 1 person to ask")],
        param_extensions={
            "fieldset": {
                "legend": {
                    # This removes the `govuk-fieldset__legend--s` class, thereby
                    # making the form label font regular weight, not bold
                    "classes": "",
                },
            }
        },
    )
    reason = GovukTextareaField("Tell them why you want to join this service (optional)")


class CopyTemplateForm(StripWhitespaceForm, TemplateNameMixin):
    template_id = HiddenField(
        "The template ID to copy", validators=[NotifyDataRequired(thing="the template ID to copy")]
    )
    parent_folder_id = HiddenField("The folder ID to copy the template into")


class ProcessUnsubscribeRequestForm(StripWhitespaceForm):
    report_has_been_processed = GovukCheckboxField("Mark as completed")

    def __init__(self, is_a_batched_report, report_completed, *args, **kwargs):
        self.report_completed = report_completed
        super().__init__(*args, **kwargs)

        if is_a_batched_report:
            self.report_has_been_processed.param_extensions = {
                "items": [
                    {
                        "hint": {"text": "I have unsubscribed these recipients from our mailing list"},
                        "classes": "govuk-checkboxes__item--single-with-hint",
                    },
                ]
            }
        else:
            self.report_has_been_processed.param_extensions = {
                "items": [
                    {
                        "hint": {"text": "You cannot do this until you’ve downloaded the report"},
                        "disabled": True,
                        "classes": "govuk-checkboxes__item--single-with-hint",
                    },
                ]
            }

    def validate_report_has_been_processed(self, field):
        if not field.data and not self.report_completed:
            raise ValidationError(
                "There is a problem. You must confirm that you have removed the email addresses from your mailing list."
            )

        if field.data and self.report_completed:
            raise ValidationError("There is a problem. You have already marked the report as Completed")
