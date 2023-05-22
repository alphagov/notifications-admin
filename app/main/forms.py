import math
import weakref
from contextlib import suppress
from datetime import datetime, timedelta
from itertools import chain
from numbers import Number

import pytz
from flask import Markup, request
from flask_login import current_user
from flask_wtf import FlaskForm as Form
from flask_wtf.file import FileAllowed, FileSize
from flask_wtf.file import FileField as FileField_wtf
from notifications_utils.countries.data import Postage
from notifications_utils.formatters import strip_all_whitespace
from notifications_utils.insensitive_dict import InsensitiveDict
from notifications_utils.postal_address import PostalAddress
from notifications_utils.recipients import (
    InvalidPhoneError,
    normalise_phone_number,
    validate_phone_number,
)
from orderedset import OrderedSet
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
    URL,
    UUID,
    DataRequired,
    InputRequired,
    Length,
    Optional,
    Regexp,
)

from app import asset_fingerprinter
from app.formatters import (
    format_auth_type,
    format_thousands,
    guess_name_from_email_address,
    message_count_noun,
    sentence_case,
)
from app.main.validators import (
    BroadcastLength,
    CharactersNotAllowed,
    CommonlyUsedPassword,
    CsvFileValidator,
    DoesNotStartWithDoubleZero,
    FileIsVirusFree,
    LettersNumbersSingleQuotesFullStopsAndUnderscoresOnly,
    MustContainAlphanumericCharacters,
    NoCommasInPlaceHolders,
    NoEmbeddedImagesInSVG,
    NoPlaceholders,
    NoTextInSVG,
    OnlySMSCharacters,
    StringsNotAllowed,
    ValidEmail,
    ValidGovEmail,
)
from app.models.branding import (
    GOVERNMENT_IDENTITY_SYSTEM_COLOURS,
    GOVERNMENT_IDENTITY_SYSTEM_CRESTS_OR_INSIGNIA,
)
from app.models.feedback import PROBLEM_TICKET_TYPE, QUESTION_TICKET_TYPE
from app.models.organisation import Organisation
from app.utils import branding
from app.utils.constants import SIGN_IN_METHOD_TEXT, SIGN_IN_METHOD_TEXT_OR_EMAIL
from app.utils.govuk_frontend_field import (
    GovukFrontendWidgetMixin,
    render_govuk_frontend_macro,
)
from app.utils.image_processing import CorruptImage, ImageProcessor, WrongImageFormat
from app.utils.user import distinct_email_addresses
from app.utils.user_permissions import (
    all_ui_permissions,
    broadcast_permission_options,
    permission_options,
)


def get_time_value_and_label(future_time):
    return (
        future_time.replace(tzinfo=None).isoformat(),
        "{} at {}".format(
            get_human_day(future_time.astimezone(pytz.timezone("Europe/London"))),
            get_human_time(future_time.astimezone(pytz.timezone("Europe/London"))),
        ),
    )


def get_human_time(time):
    return {"0": "midnight", "12": "midday"}.get(time.strftime("%-H"), time.strftime("%-I%p").lower())


def get_human_day(time, prefix_today_with="T"):
    #  Add 1 hour to get ‘midnight today’ instead of ‘midnight tomorrow’
    time = (time - timedelta(hours=1)).strftime("%A")
    if time == datetime.utcnow().strftime("%A"):
        return f"{prefix_today_with}oday"
    if time == (datetime.utcnow() + timedelta(days=1)).strftime("%A"):
        return "Tomorrow"
    return time


def get_furthest_possible_scheduled_time():
    return (datetime.utcnow() + timedelta(days=4)).replace(hour=0)


def get_next_hours_until(until):
    now = datetime.utcnow()
    hours = int((until - now).total_seconds() / (60 * 60))
    return [
        (now + timedelta(hours=i)).replace(minute=0, second=0, microsecond=0).replace(tzinfo=pytz.utc)
        for i in range(1, hours + 1)
    ]


def get_next_days_until(until):
    now = datetime.utcnow()
    days = int((until - now).total_seconds() / (60 * 60 * 24))
    return [
        get_human_day((now + timedelta(days=i)).replace(tzinfo=pytz.utc), prefix_today_with="Later t")
        for i in range(0, days + 1)
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


def email_address(label="Email address", gov_user=True, required=True):

    validators = [
        ValidEmail(),
    ]

    if gov_user:
        validators.append(ValidGovEmail())

    if required:
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
            "value": value,
            "type": self.input_type,
        }

        return params


class UKMobileNumber(GovukTextInputFieldMixin, TelField):
    input_type = "tel"

    def pre_validate(self, form):
        try:
            validate_phone_number(self.data)
        except InvalidPhoneError as e:
            raise ValidationError(str(e)) from e


class InternationalPhoneNumber(UKMobileNumber, GovukTextInputFieldMixin, TelField):
    def pre_validate(self, form):
        try:
            if self.data:
                validate_phone_number(self.data, international=True)
        except InvalidPhoneError as e:
            raise ValidationError(str(e)) from e


def uk_mobile_number(label="Mobile number"):
    return UKMobileNumber(label, validators=[DataRequired(message="Cannot be empty")])


def international_phone_number(label="Mobile number"):
    return InternationalPhoneNumber(label, validators=[DataRequired(message="Cannot be empty")])


def password(label="Password"):
    return GovukPasswordField(
        label,
        validators=[
            DataRequired(message="Cannot be empty"),
            Length(8, 255, message="Must be at least 8 characters"),
            CommonlyUsedPassword(message="Choose a password that’s harder to guess"),
        ],
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


class GovukDateField(GovukTextInputFieldMixin, DateField):
    pass


class SMSCode(GovukTextInputField):
    # the design system recommends against ever using `type="number"`. "tel" makes mobile browsers
    # show a phone keypad input rather than a full qwerty keyboard.
    input_type = "tel"
    param_extensions = {"attributes": {"pattern": "[0-9]*"}}
    validators = [
        DataRequired(message="Cannot be empty"),
        Regexp(regex=r"^\d+$", message="Numbers only"),
        Length(min=5, message="Not enough numbers"),
        Length(max=5, message="Too many numbers"),
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
                raise ValidationError(f"{sentence_case(self.things)} must be a whole number")

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
        Regexp(regex="^$|^#?(?:[0-9a-fA-F]{3}){1,2}$", message="Must be a valid hex colour code"),
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


class NestedRadioField(RadioFieldWithNoneOption, NestedFieldMixin):
    pass


class NestedCheckboxesField(SelectMultipleField, NestedFieldMixin):
    NONE_OPTION_VALUE = None


class HiddenFieldWithNoneOption(FieldWithNoneOption, HiddenField):
    pass


class RadioFieldWithRequiredMessage(RadioField):
    def __init__(self, *args, required_message="Not a valid choice", **kwargs):
        self.required_message = required_message
        super().__init__(*args, **kwargs)

    def pre_validate(self, form):
        try:
            return super().pre_validate(form)
        except ValueError as e:
            raise ValidationError(self.required_message) from e


class StripWhitespaceForm(Form):
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


class PostalAddressField(TextAreaField):
    def process_formdata(self, valuelist):
        if valuelist:
            self.data = PostalAddress(valuelist[0]).normalised


class VirusScannedFileField(FileField_wtf, RequiredValidatorsMixin):
    required_validators = [
        FileIsVirusFree(),
    ]


class LoginForm(StripWhitespaceForm):
    email_address = GovukEmailField(
        "Email address", validators=[Length(min=5, max=255), DataRequired(message="Cannot be empty"), ValidEmail()]
    )
    password = GovukPasswordField("Password", validators=[DataRequired(message="Enter your password")])


class RegisterUserForm(StripWhitespaceForm):
    name = GovukTextInputField("Full name", validators=[DataRequired(message="Cannot be empty")])
    email_address = email_address()
    mobile_number = international_phone_number()
    password = password()
    # always register as sms type
    auth_type = HiddenField("auth_type", default="sms_auth")


class RegisterUserFromInviteForm(RegisterUserForm):
    def __init__(self, invited_user):
        super().__init__(
            service=invited_user.service,
            email_address=invited_user.email_address,
            auth_type=invited_user.auth_type,
            name=guess_name_from_email_address(invited_user.email_address),
        )

    mobile_number = InternationalPhoneNumber("Mobile number", validators=[])
    service = HiddenField("service")
    email_address = HiddenField("email_address")
    auth_type = HiddenField("auth_type", validators=[DataRequired()])

    def validate_mobile_number(self, field):
        if self.auth_type.data == "sms_auth" and not field.data:
            raise ValidationError("Cannot be empty")


class RegisterUserFromOrgInviteForm(StripWhitespaceForm):
    def __init__(self, invited_org_user):
        super().__init__(
            organisation=invited_org_user.organisation,
            email_address=invited_org_user.email_address,
        )

    name = GovukTextInputField("Full name", validators=[DataRequired(message="Cannot be empty")])

    mobile_number = InternationalPhoneNumber("Mobile number", validators=[DataRequired(message="Cannot be empty")])
    password = password()
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


class GovukTextareaField(GovukFrontendWidgetMixin, TextAreaField):
    govuk_frontend_component_name = "textarea"

    def prepare_params(self, **kwargs):
        # error messages
        error_message = None
        if self.errors:
            error_message = {"text": self.errors[0]}

        params = {
            "name": self.name,
            "id": self.id,
            "rows": 8,
            "label": {"text": self.label.text, "classes": None, "isPageHeading": False},
            "hint": {"text": None},
            "errorMessage": error_message,
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

    def prepare_params(self, **kwargs):
        # returns either a list or a hierarchy of lists
        # depending on how get_items_from_options is implemented
        items = self.get_items_from_options(self)

        return {
            "name": self.name,
            "fieldset": {
                "attributes": {"id": self.name},
                "legend": {"text": self.label.text, "classes": "govuk-fieldset__legend--s"},
            },
            "errorMessage": self.get_error_message(),
            "items": items,
        }


class OptionalGovukRadiosField(GovukRadiosField):
    def pre_validate(self, form):
        if self.data is None:
            return
        super().pre_validate(form)


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
            yield (value, label, (self.data in {value, self.coerce(value)}))


class OrganisationTypeField(GovukRadiosField):
    def __init__(self, *args, include_only=None, validators=None, **kwargs):
        super().__init__(
            *args,
            choices=[
                (value, label)
                for value, label in Organisation.TYPE_LABELS.items()
                if not include_only or value in include_only
            ],
            thing="the type of organisation",
            validators=validators or [],
            **kwargs,
        )


class GovukRadiosFieldWithNoneOption(FieldWithNoneOption, GovukRadiosField):
    pass


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
        return {
            "name": option.name,
            "id": option.id,
            "text": option.label.text,
            "value": str(option.data),  # to protect against non-string types like uuids
            "checked": option.checked,
            "image": self.image_data[option.data],
        }


# guard against data entries that aren't a known permission
def filter_by_permissions(valuelist):
    if valuelist is None:
        return None
    else:
        return [entry for entry in valuelist if any(entry in option for option in permission_options)]


# guard against data entries that aren't a known broadcast permission
def filter_by_broadcast_permissions(valuelist):
    if valuelist is None:
        return None
    else:
        return [entry for entry in valuelist if any(entry in option for option in broadcast_permission_options)]


class AuthTypeForm(StripWhitespaceForm):
    auth_type = GovukRadiosField(
        "Sign in using",
        choices=[
            ("sms_auth", format_auth_type("sms_auth")),
            ("email_auth", format_auth_type("email_auth")),
        ],
    )


class BasePermissionsForm(StripWhitespaceForm):
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
                            "phone number to their profile"
                        },
                        "disabled": True,
                    },
                    {"checked": True},
                ]
            }

    folder_permissions = GovukCollapsibleNestedCheckboxesField("Folders this team member can see", field_label="folder")

    login_authentication = GovukRadiosField(
        "Sign in using",
        choices=[
            ("sms_auth", "Text message code"),
            ("email_auth", "Email link"),
        ],
        thing="how this team member should sign in",
        validators=[DataRequired()],
    )

    permissions_field = GovukCheckboxesField(
        "Permissions",
        filters=[filter_by_permissions],
        choices=[(value, label) for value, label in permission_options],
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


class PermissionsForm(BasePermissionsForm):
    pass


class BroadcastPermissionsForm(BasePermissionsForm):
    permissions_field = GovukCheckboxesField(
        "Permissions",
        choices=[(value, label) for value, label in broadcast_permission_options],
        filters=[filter_by_broadcast_permissions],
        param_extensions={"hint": {"text": "Team members who can create or approve alerts can also reject them."}},
    )

    @property
    def permissions(self):
        return {"view_activity"} | super().permissions


class BaseInviteUserForm:
    email_address = email_address(gov_user=False)

    def __init__(self, inviter_email_address, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inviter_email_address = inviter_email_address

    def validate_email_address(self, field):
        if current_user.platform_admin:
            return
        if field.data.lower() == self.inviter_email_address.lower():
            raise ValidationError("You cannot send an invitation to yourself")


class InviteUserForm(BaseInviteUserForm, PermissionsForm):
    pass


class BroadcastInviteUserForm(BaseInviteUserForm, BroadcastPermissionsForm):
    email_address = email_address(gov_user=True)

    def validate_email_address(self, field):
        if not distinct_email_addresses(field.data, self.inviter_email_address):
            raise ValidationError("You cannot send an invitation to yourself")


class InviteOrgUserForm(BaseInviteUserForm, StripWhitespaceForm):
    pass


class TwoFactorForm(StripWhitespaceForm):
    def __init__(self, validate_code_func, *args, **kwargs):
        """
        Keyword arguments:
        validate_code_func -- Validates the code with the API.
        """
        self.validate_code_func = validate_code_func
        super(TwoFactorForm, self).__init__(*args, **kwargs)

    sms_code = SMSCode("Text message code")

    def validate(self):

        if not self.sms_code.validate(self):
            return False

        is_valid, reason = self.validate_code_func(self.sms_code.data)

        if not is_valid:
            self.sms_code.errors.append(reason)
            return False

        return True


class TextNotReceivedForm(StripWhitespaceForm):
    mobile_number = international_phone_number()


class RenameServiceForm(StripWhitespaceForm):
    name = GovukTextInputField(
        "Service name",
        validators=[
            DataRequired(message="Cannot be empty"),
            MustContainAlphanumericCharacters(),
            Length(max=255, message="Service name must be 255 characters or fewer"),
        ],
    )


class RenameOrganisationForm(StripWhitespaceForm):
    name = GovukTextInputField(
        "Organisation name",
        validators=[
            DataRequired(message="Cannot be empty"),
            MustContainAlphanumericCharacters(),
            Length(max=255, message="Organisation name must be 255 characters or fewer"),
        ],
    )


class AddGPOrganisationForm(StripWhitespaceForm):
    def __init__(self, *args, service_name="unknown", **kwargs):
        super().__init__(*args, **kwargs)
        self.same_as_service_name.label.text = f"Is your GP practice called ‘{service_name}’?"
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
        "Is your GP practice called the same name as your service?",
        choices=[
            (True, "Yes"),
            (False, "No"),
        ],
    )

    name = GovukTextInputField(
        "What’s your practice called?",
    )

    def validate_name(self, field):
        if self.same_as_service_name.data is False:
            if not field.data:
                raise ValidationError("Cannot be empty")
        else:
            field.data = ""


class AddNHSLocalOrganisationForm(StripWhitespaceForm):
    def __init__(self, *args, organisation_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organisations.choices = organisation_choices

    organisations = GovukRadiosField(
        "Which NHS Trust or Clinical Commissioning Group do you work for?",
        thing="an NHS Trust or Clinical Commissioning Group",
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
        thing="whether this organisation is a crown body",
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


class AdminOrganisationDomainsForm(StripWhitespaceForm):
    def populate(self, domains_list):
        for index, value in enumerate(domains_list):
            self.domains[index].data = value

    domains = FieldList(
        StripWhitespaceStringField(
            "",
            validators=[
                CharactersNotAllowed("@"),
                StringsNotAllowed("nhs.uk", "nhs.net"),
                Optional(),
            ],
            default="",
        ),
        min_entries=20,
        max_entries=20,
        label="Domain names",
    )


class CreateServiceForm(StripWhitespaceForm):
    name = GovukTextInputField(
        "Service name",
        validators=[
            DataRequired(message="Cannot be empty"),
            MustContainAlphanumericCharacters(),
            Length(max=255, message="Service name must be 255 characters or fewer"),
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


class AdminServiceSMSAllowanceForm(StripWhitespaceForm):
    free_sms_allowance = GovukIntegerField(
        "Numbers of text message fragments per year",
        things="text message fragments",
        validators=[InputRequired(message="Cannot be empty")],
    )


class AdminServiceMessageLimitForm(StripWhitespaceForm):
    message_limit = GovukIntegerField(
        "",
        things="number of messages",
        validators=[DataRequired(message="Cannot be empty")],
    )

    def __init__(self, notification_type, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.message_limit.label.text = f"Daily {message_count_noun(1, notification_type)} limit"
        self.message_limit.things = f"Number of {message_count_noun(999, notification_type)}"
        self.message_limit.param_extensions = {
            "hint": {
                "text": (
                    f"Number of {message_count_noun(999, notification_type)} the service is allowed to send each day"
                )
            }
        }


class AdminServiceRateLimitForm(StripWhitespaceForm):
    rate_limit = GovukIntegerField(
        "Number of messages the service can send in a rolling 60 second window",
        things="number of messages",
        validators=[DataRequired(message="Cannot be empty")],
    )


class ConfirmPasswordForm(StripWhitespaceForm):
    def __init__(self, validate_password_func, *args, **kwargs):
        self.validate_password_func = validate_password_func
        super(ConfirmPasswordForm, self).__init__(*args, **kwargs)

    password = GovukPasswordField("Enter password")

    def validate_password(self, field):
        if not self.validate_password_func(field.data):
            raise ValidationError("Invalid password")


class NewBroadcastForm(StripWhitespaceForm):
    content = GovukRadiosField(
        "New alert",
        choices=[
            ("freeform", "Write your own message"),
            ("template", "Use a template"),
        ],
        param_extensions={"fieldset": {"legend": {"classes": "govuk-visually-hidden"}}},
    )

    @property
    def use_template(self):
        return self.content.data == "template"


class ConfirmBroadcastForm(StripWhitespaceForm):
    def __init__(self, *args, service_is_live, channel, max_phones, **kwargs):
        super().__init__(*args, **kwargs)

        self.confirm.label.text = self.generate_label(channel, max_phones)

        if service_is_live:
            self.confirm.validators += (DataRequired("You need to confirm that you understand"),)

    confirm = GovukCheckboxField("Confirm")

    @staticmethod
    def generate_label(channel, max_phones):
        if channel in {"test", "operator"}:
            return f"I understand this will alert anyone who has switched on the {channel} channel"
        if channel == "severe":
            return f"I understand this will alert {ConfirmBroadcastForm.format_number_generic(max_phones)} of people"
        if channel == "government":
            return (
                f"I understand this will alert {ConfirmBroadcastForm.format_number_generic(max_phones)} "
                "of people, even if they’ve opted out"
            )

    @staticmethod
    def format_number_generic(count):
        for threshold, message in (
            (1_000_000, "millions"),
            (100_000, "hundreds of thousands"),
            (10_000, "tens of thousands"),
            (1_000, "thousands"),
            (100, "hundreds"),
            (-math.inf, "an unknown number"),
        ):
            if count >= threshold:
                return message


class BaseTemplateForm(StripWhitespaceForm):
    name = GovukTextInputField("Template name", validators=[DataRequired(message="Cannot be empty")])

    template_content = TextAreaField(
        "Message", validators=[DataRequired(message="Cannot be empty"), NoCommasInPlaceHolders()]
    )


class SMSTemplateForm(BaseTemplateForm):
    def validate_template_content(self, field):
        OnlySMSCharacters(template_type="sms")(None, field)


class BroadcastTemplateForm(SMSTemplateForm):
    def validate_template_content(self, field):
        OnlySMSCharacters(template_type="broadcast")(None, field)
        NoPlaceholders()(None, field)
        BroadcastLength()(None, field)


class LetterAddressForm(StripWhitespaceForm):
    def __init__(self, *args, allow_international_letters=False, **kwargs):
        self.allow_international_letters = allow_international_letters
        super().__init__(*args, **kwargs)

    address = PostalAddressField("Address", validators=[DataRequired(message="Cannot be empty")])

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
            raise ValidationError("The last line of a BFPO address must not be a country.")

        if not address.has_valid_last_line:
            if self.allow_international_letters:
                raise ValidationError("Last line of the address must be a UK postcode or another country")
            if address.international:
                raise ValidationError("You do not have permission to send letters to other countries")
            raise ValidationError("Last line of the address must be a real UK postcode")

        if address.has_invalid_characters:
            raise ValidationError(
                "Address lines must not start with any of the following characters: @ ( ) = [ ] ” \\ / , < > ~"
            )


class EmailTemplateForm(BaseTemplateForm):
    subject = TextAreaField("Subject", validators=[DataRequired(message="Cannot be empty")])


class LetterTemplateForm(EmailTemplateForm):
    subject = TextAreaField("Main heading", validators=[DataRequired(message="Cannot be empty")])

    template_content = TextAreaField(
        "Body", validators=[DataRequired(message="Cannot be empty"), NoCommasInPlaceHolders()]
    )


class LetterTemplatePostageForm(StripWhitespaceForm):
    postage = GovukRadiosField(
        "Choose the postage for this letter template",
        choices=[
            ("first", "First class"),
            ("second", "Second class"),
        ],
        thing="first class or second class",
        validators=[DataRequired()],
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
            ("first", "First class post"),
            ("second", "Second class post"),
        ],
        default="second",
        validators=[DataRequired()],
    )


class ForgotPasswordForm(StripWhitespaceForm):
    email_address = email_address(gov_user=False)


class NewPasswordForm(StripWhitespaceForm):
    new_password = password()


class ChangePasswordForm(StripWhitespaceForm):
    def __init__(self, validate_password_func, *args, **kwargs):
        self.validate_password_func = validate_password_func
        super(ChangePasswordForm, self).__init__(*args, **kwargs)

    old_password = password("Current password")
    new_password = password("New password")

    def validate_old_password(self, field):
        if not self.validate_password_func(field.data):
            raise ValidationError("Invalid password")


class CsvUploadForm(StripWhitespaceForm):
    file = FileField(
        "Add recipients",
        validators=[
            DataRequired(message="Please pick a file"),
            CsvFileValidator(),
            FileSize(max_size=10 * 1024 * 1024, message="File must be smaller than 10MB"),
        ],
    )


class ChangeNameForm(StripWhitespaceForm):
    new_name = GovukTextInputField("Your name")


class ChangeEmailForm(StripWhitespaceForm):
    def __init__(self, validate_email_func, *args, **kwargs):
        self.validate_email_func = validate_email_func
        super(ChangeEmailForm, self).__init__(*args, **kwargs)

    email_address = email_address()

    def validate_email_address(self, field):
        # The validate_email_func can be used to call API to check if the email address is already in
        # use. We don't want to run that check for invalid email addresses, since that will cause an error.
        # If there are any other validation errors on the email_address, we should skip this check.
        if self.email_address.errors:
            return

        is_valid = self.validate_email_func(field.data)
        if is_valid:
            raise ValidationError("The email address is already in use")


class ChangeNonGovEmailForm(ChangeEmailForm):
    email_address = email_address(gov_user=False)


class ChangeMobileNumberForm(StripWhitespaceForm):
    mobile_number = international_phone_number()


class ChooseTimeForm(StripWhitespaceForm):
    def __init__(self, *args, **kwargs):
        super(ChooseTimeForm, self).__init__(*args, **kwargs)
        self.scheduled_for.choices = [("", "Now")] + [
            get_time_value_and_label(hour) for hour in get_next_hours_until(get_furthest_possible_scheduled_time())
        ]
        self.scheduled_for.categories = get_next_days_until(get_furthest_possible_scheduled_time())

    scheduled_for = GovukRadiosField(
        "When should Notify send these messages?",
        default="",
    )


class CreateKeyForm(StripWhitespaceForm):
    def __init__(self, existing_keys, *args, **kwargs):
        self.existing_key_names = [key["name"].lower() for key in existing_keys if not key["expiry_date"]]
        super().__init__(*args, **kwargs)

    key_type = GovukRadiosField(
        "Type of key",
        thing="the type of key",
    )

    key_name = GovukTextInputField(
        "Name for this key", validators=[DataRequired(message="You need to give the key a name")]
    )

    def validate_key_name(self, key_name):
        if key_name.data.lower() in self.existing_key_names:
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
    name = GovukTextInputField("Name (optional)")
    email_address = email_address(label="Email address", gov_user=False, required=True)
    feedback = TextAreaField("Your message", validators=[DataRequired(message="Cannot be empty")])


class Triage(StripWhitespaceForm):
    severe = GovukRadiosField(
        "Is it an emergency?",
        choices=[
            ("yes", "Yes"),
            ("no", "No"),
        ],
        thing="yes or no",
    )


class EstimateUsageForm(StripWhitespaceForm):
    volume_email = GovukIntegerField(
        "How many emails do you expect to send in the next year?",
        things="number of emails",
    )
    volume_sms = GovukIntegerField(
        "How many text messages do you expect to send in the next year?",
        things="number of text messages",
    )
    volume_letter = GovukIntegerField(
        "How many letters do you expect to send in the next year?",
        things="number of letters",
    )
    consent_to_research = GovukRadiosField(
        "Can we contact you when we’re doing user research?",
        choices=[
            ("yes", "Yes"),
            ("no", "No"),
        ],
        thing="yes or no",
        param_extensions={"hint": {"text": "You do not have to take part and you can unsubscribe at any time"}},
    )

    at_least_one_volume_filled = True

    def validate(self, *args, **kwargs):
        if self.volume_email.data == self.volume_sms.data == self.volume_letter.data == 0:
            self.at_least_one_volume_filled = False
            return False

        return super().validate(*args, **kwargs)


class AdminProviderRatioForm(Form):
    def __init__(self, providers):
        self._providers = providers

        # hack: https://github.com/wtforms/wtforms/issues/736
        self._unbound_fields = [
            (
                provider["identifier"],
                GovukIntegerField(
                    f"{provider['display_name']} (%)",
                    things="percentage",
                    validators=[validators.NumberRange(min=0, max=100, message="Must be between 0 and 100")],
                    param_extensions={
                        "classes": "govuk-input--width-3",
                    },
                ),
            )
            for provider in providers
        ]

        super().__init__(data={provider["identifier"]: provider["priority"] for provider in providers})

    def validate(self):
        if not super().validate():
            return False

        total = sum(getattr(self, provider["identifier"]).data for provider in self._providers)

        if total == 100:
            return True

        for provider in self._providers:
            getattr(self, provider["identifier"]).errors += ["Must add up to 100%"]

        return False


class ServiceContactDetailsForm(StripWhitespaceForm):
    contact_details_type = GovukRadiosField(
        "Type of contact details",
        choices=[
            ("url", "Link"),
            ("email_address", "Email address"),
            ("phone_number", "Phone number"),
        ],
    )

    url = GovukTextInputField("URL")
    email_address = GovukEmailField("Email address")
    # This is a text field because the number provided by the user can also be a short code
    phone_number = GovukTextInputField("Phone number")

    def validate(self):

        if self.contact_details_type.data == "url":
            self.url.validators = [DataRequired(), URL(message="Must be a valid URL")]

        elif self.contact_details_type.data == "email_address":
            self.email_address.validators = [DataRequired(), Length(min=5, max=255), ValidEmail()]

        elif self.contact_details_type.data == "phone_number":
            # we can't use the existing phone number validation functions here since we want to allow landlines
            # and disallow emergency 3-digit numbers
            def valid_non_emergency_phone_number(self, num):
                try:
                    normalised_number = normalise_phone_number(num.data)
                except InvalidPhoneError as e:
                    raise ValidationError("Must be a valid phone number") from e

                if normalised_number in {"999", "112"}:
                    raise ValidationError("Must not be an emergency number")

                return True

            self.phone_number.validators = [
                DataRequired(),
                Length(min=3, max=20),
                valid_non_emergency_phone_number,
            ]

        return super().validate()


class ServiceReplyToEmailForm(StripWhitespaceForm):
    email_address = email_address(label="Reply-to email address", gov_user=False)
    is_default = GovukCheckboxField("Make this email address the default")


class ServiceSmsSenderForm(StripWhitespaceForm):
    sms_sender = GovukTextInputField(
        "Text message sender",
        validators=[
            DataRequired(message="Cannot be empty"),
            Length(max=11, message="Enter 11 characters or fewer"),
            Length(min=3, message="Enter 3 characters or more"),
            LettersNumbersSingleQuotesFullStopsAndUnderscoresOnly(),
            DoesNotStartWithDoubleZero(),
        ],
    )
    is_default = GovukCheckboxField("Make this text message sender the default")


class ServiceEditInboundNumberForm(StripWhitespaceForm):
    is_default = GovukCheckboxField("Make this text message sender the default")


class AdminNotesForm(StripWhitespaceForm):
    notes = TextAreaField(validators=[])


class AdminBillingDetailsForm(StripWhitespaceForm):
    billing_contact_email_addresses = GovukTextInputField("Contact email addresses")
    billing_contact_names = GovukTextInputField("Contact names")
    billing_reference = GovukTextInputField("Reference")
    purchase_order_number = GovukTextInputField("Purchase order number")
    notes = TextAreaField(validators=[])


class ServiceLetterContactBlockForm(StripWhitespaceForm):
    letter_contact_block = TextAreaField(validators=[DataRequired(message="Cannot be empty"), NoCommasInPlaceHolders()])
    is_default = GovukCheckboxField("Set as your default address")

    def validate_letter_contact_block(self, field):
        line_count = field.data.strip().count("\n")
        if line_count >= 10:
            raise ValidationError(f"Contains {line_count + 1} lines, maximum is 10")


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
        super().__init__(name, *args, truthy="Yes", falsey="No", **kwargs)


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
    file = VirusScannedFileField("Upload a PNG logo", validators=[FileAllowed(["png"], "PNG Images only!")])
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
            raise ValidationError("This field is required")

    def validate(self):
        rv = super().validate()

        op = request.form.get("operation")
        if op == "email-branding-details":
            # we only want to validate alt_text/text if we're editing the fields, not the file

            if self.alt_text.data and self.text.data:
                self.alt_text.errors.append("Must be empty if you enter logo text")
                return False

            if not (self.alt_text.data or self.text.data):
                self.alt_text.errors.append("Cannot be empty if you do not have logo text")
                return False

        return rv


class AdminChangeOrganisationDefaultEmailBrandingForm(StripWhitespaceForm):
    email_branding_id = HiddenField(
        "Email branding id",
        validators=[DataRequired()],
    )


class AdminChangeOrganisationDefaultLetterBrandingForm(StripWhitespaceForm):
    letter_branding_id = HiddenField(
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
    name = GovukTextInputField("Name of brand", validators=[DataRequired()])


class AdminEditLetterBrandingSVGUploadForm(StripWhitespaceForm):
    file = VirusScannedFileField(
        "Upload an SVG logo",
        validators=[
            FileAllowed(["svg"], "SVG Images only!"),
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
            FileSize(max_size=2 * 1024 * 1024, message="File must be smaller than 2MB"),
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
            FileSize(max_size=2 * 1024 * 1024, message="File must be smaller than 2MB"),
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
            FileAllowed(["pdf"], "Save your letter as a PDF and try again."),
            DataRequired(message="You need to choose a file to upload"),
            FileSize(max_size=2 * 1024 * 1024, message="File must be smaller than 2MB"),
        ],
    )


class EmailFieldInGuestList(GovukEmailField, StripWhitespaceStringField):
    pass


class InternationalPhoneNumberInGuestList(InternationalPhoneNumber, StripWhitespaceStringField):
    pass


class GuestList(StripWhitespaceForm):
    def populate(self, email_addresses, phone_numbers):
        for form_field, existing_guest_list in (
            (self.email_addresses, email_addresses),
            (self.phone_numbers, phone_numbers),
        ):
            for index, value in enumerate(existing_guest_list):
                form_field[index].data = value

    email_addresses = FieldList(
        EmailFieldInGuestList("", validators=[Optional(), ValidEmail()], default=""),
        min_entries=5,
        max_entries=5,
        label="Email addresses",
    )

    phone_numbers = FieldList(
        InternationalPhoneNumberInGuestList("", validators=[Optional()], default=""),
        min_entries=5,
        max_entries=5,
        label="Mobile numbers",
    )


class DateFilterForm(StripWhitespaceForm):
    start_date = GovukDateField("Start Date", [validators.optional()])
    end_date = GovukDateField("End Date", [validators.optional()])
    include_from_test_key = GovukCheckboxField("Include test keys")


class RequiredDateFilterForm(StripWhitespaceForm):
    start_date = GovukDateField("Start Date")
    end_date = GovukDateField("End Date")


class BillingReportDateFilterForm(StripWhitespaceForm):
    start_date = GovukDateField("First day covered by report")
    end_date = GovukDateField("Last day covered by report")


class SearchByNameForm(StripWhitespaceForm):
    search = GovukSearchField(
        "Search by name",
        validators=[DataRequired("You need to enter full or partial name to search by.")],
    )


class AdminSearchUsersByEmailForm(StripWhitespaceForm):
    search = GovukSearchField(
        "Search by name or email address",
        validators=[DataRequired("You need to enter full or partial email address to search by.")],
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
        validators=[DataRequired(message="Cannot be empty"), Length(min=10, message="Must be at least 10 characters")],
    )

    def validate(self):
        return super().validate() or self.url.data == ""


class SMSPrefixForm(StripWhitespaceForm):
    enabled = OnOffField("")  # label is assigned on instantiation


def get_placeholder_form_instance(
    placeholder_name,
    dict_to_populate_from,
    template_type,
    allow_international_phone_numbers=False,
):
    if InsensitiveDict.make_key(placeholder_name) == "emailaddress" and template_type == "email":
        field = email_address(label=placeholder_name, gov_user=False)
    elif InsensitiveDict.make_key(placeholder_name) == "phonenumber" and template_type == "sms":
        if allow_international_phone_numbers:
            field = international_phone_number(label=placeholder_name)
        else:
            field = uk_mobile_number(label=placeholder_name)
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
        validators=[DataRequired("Cannot be empty")],
    )


class EmailBrandingChooseLogoForm(StripWhitespaceForm):
    BRANDING_OPTIONS_DATA = {
        "single_identity": {
            "label": "Create a government identity logo",
            "image": {
                "url": asset_fingerprinter.get_url("images/branding/single_identity.png"),
                "alt_text": "An example of an email with a government identity logo,"
                " including a blue stripe, a crest and department's name",
                "dimensions": {"width": 606, "height": 404},
            },
        },
        "org": {
            "label": "Upload a logo",
            "image": {
                "url": asset_fingerprinter.get_url("images/branding/org.png"),
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


class EmailBrandingChooseBanner(Form):
    BANNER_CHOICES_DATA = {
        "org_banner": {
            "label": "Yes",
            "image": {
                "url": asset_fingerprinter.get_url("images/branding/org_banner.png"),
                "alt_text": "An example of an email with a logo on a blue banner.",
                "dimensions": {"width": 404, "height": 454},
            },
        },
        "org": {
            "label": "No",
            "image": {
                "url": asset_fingerprinter.get_url("images/branding/org.png"),
                "alt_text": "An example of an email with a logo on a clear background.",
                "dimensions": {"width": 404, "height": 454},
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


class AdminServiceAddDataRetentionForm(StripWhitespaceForm):
    notification_type = GovukRadiosField(
        "What notification type?",
        choices=[
            ("email", "Email"),
            ("sms", "SMS"),
            ("letter", "Letter"),
        ],
        thing="notification type",
    )
    days_of_retention = GovukIntegerField(
        label="Days of retention",
        things="days of retention",
        validators=[validators.NumberRange(min=3, max=90, message="Must be between 3 and 90")],
    )


class AdminServiceEditDataRetentionForm(StripWhitespaceForm):
    days_of_retention = GovukIntegerField(
        label="Days of retention",
        things="days of retention",
        validators=[validators.NumberRange(min=3, max=90, message="Must be between 3 and 90")],
    )


class AdminReturnedLettersForm(StripWhitespaceForm):
    references = TextAreaField(
        "Letter references",
        validators=[
            DataRequired(message="Cannot be empty"),
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
            raise validators.StopValidation("Cannot be empty")

    return validate


class TemplateAndFoldersSelectionForm(Form):
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
        *args,
        **kwargs,
    ):

        super().__init__(*args, **kwargs)

        self.available_template_types = available_template_types

        self.templates_and_folders.choices = [(item.id, item.name) for item in template_list]

        self.op = None
        self.is_move_op = self.is_add_folder_op = self.is_add_template_op = False

        self.move_to.all_template_folders = all_template_folders
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
                    ("broadcast", "Broadcast") if "broadcast" in available_template_types else None,
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

    def validate(self):
        self.op = request.form.get("operation")

        self.is_move_op = self.op in {"move-to-existing-folder", "move-to-new-folder"}
        self.is_add_folder_op = self.op in {"add-new-folder", "move-to-new-folder"}
        self.is_add_template_op = self.op in {"add-new-template"}

        if not (self.is_add_folder_op or self.is_move_op or self.is_add_template_op):
            return False

        return super().validate()

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
    move_to = NestedRadioField(
        "Choose a folder", default="", validators=[required_for_ops("move-to-existing-folder"), Optional()]
    )
    add_new_folder_name = GovukTextInputField("Folder name", validators=[required_for_ops("add-new-folder")])
    move_to_new_folder_name = GovukTextInputField("Folder name", validators=[required_for_ops("move-to-new-folder")])

    add_template_by_template_type = RadioFieldWithRequiredMessage(
        "New template",
        validators=[
            required_for_ops("add-new-template"),
            Optional(),
        ],
        required_message="Select the type of template you want to add",
    )


class AdminClearCacheForm(StripWhitespaceForm):
    model_type = GovukCheckboxesField(
        "What do you want to clear today",
    )

    def validate_model_type(self, field):
        if not field.data:
            raise ValidationError("Select at least one option")


class AdminOrganisationGoLiveNotesForm(StripWhitespaceForm):
    request_to_go_live_notes = TextAreaField(
        "Go live notes",
        filters=[lambda x: x or None],
    )


class ServiceBroadcastAccountTypeField(GovukRadiosField):
    # After validation we split the value back into its parts of service_mode
    # broadcast_channel and provider_restriction to be used by the flask route to send to the
    # API
    def post_validate(self, form, validation_stopped):
        if not validation_stopped and self.data:
            split_values = self.data.split("-")
            self.service_mode = split_values[0]
            self.broadcast_channel = split_values[1]
            self.provider_restriction = split_values[2]


class ServiceBroadcastChannelForm(StripWhitespaceForm):
    channel = GovukRadiosField(
        "Emergency alerts settings",
        thing="mode or channel",
        choices=[
            ("training", "Training mode"),
            ("operator", "Operator channel"),
            ("test", "Test channel"),
            ("severe", "Live channel"),
            ("government", "Government channel"),
        ],
    )


class ServiceBroadcastNetworkForm(StripWhitespaceForm):
    def __init__(self, broadcast_channel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.broadcast_channel = broadcast_channel

    all_networks = OnOffField(
        "Choose a mobile network",
        choices=((True, "All networks"), (False, "A single network")),
    )
    network = OptionalGovukRadiosField(
        "Choose a mobile network",
        thing="a mobile network",
        choices=(
            ("ee", "EE"),
            ("o2", "O2"),
            ("vodafone", "Vodafone"),
            ("three", "Three"),
        ),
    )

    @property
    def account_type(self):
        if self.all_networks.data:
            provider = "all"
        else:
            provider = self.network.data

        return f"live-{self.broadcast_channel}-{provider}"

    def validate_network(self, field):
        if not self.all_networks.data and not field.data:
            raise ValidationError("Select a mobile network")


class ServiceBroadcastAccountTypeForm(StripWhitespaceForm):
    account_type = ServiceBroadcastAccountTypeField(
        "Change cell broadcast service type",
        thing="which type of account this cell broadcast service is",
        choices=[("training-test-all", "")]
        + [
            (f"live-{broadcast_channel}-{provider}", "")
            for broadcast_channel in ["test", "operator", "severe", "government"]
            for provider in ["all", "ee", "o2", "three", "vodafone"]
        ],
        validators=[DataRequired()],
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

    version = GovukTextInputField("Which version of the agreement do you want to accept?")

    who = RadioField(
        "Who are you accepting the agreement for?",
        choices=(
            (
                "me",
                "Yourself",
            ),
            (
                "someone-else",
                "Someone else",
            ),
        ),
    )

    on_behalf_of_name = GovukTextInputField("What’s their name?")

    on_behalf_of_email = email_address(
        "What’s their email address?",
        required=False,
        gov_user=False,
    )

    def __validate_if_nominating(self, field):
        if self.who.data == "someone-else":
            if not field.data:
                raise ValidationError("Cannot be empty")
        else:
            field.data = ""

    validate_on_behalf_of_name = __validate_if_nominating
    validate_on_behalf_of_email = __validate_if_nominating

    def validate_version(self, field):
        try:
            float(field.data)
        except (TypeError, ValueError) as e:
            raise ValidationError("Must be a number") from e


class BroadcastAreaForm(StripWhitespaceForm):
    areas = GovukCheckboxesField("Choose areas to broadcast to")

    def __init__(self, choices, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.areas.choices = choices
        self.areas.render_as_list = True
        self.areas.param_extensions = {"fieldset": {"legend": {"classes": "govuk-visually-hidden"}}}

    @classmethod
    def from_library(cls, library):
        return cls(choices=[(area.id, area.name) for area in sorted(library)])


class BroadcastAreaFormWithSelectAll(BroadcastAreaForm):
    select_all = GovukCheckboxField("Select all")

    @classmethod
    def from_library(cls, library, select_all_choice):
        instance = super().from_library(library)
        (
            instance.select_all.area_slug,
            instance.select_all.label.text,
        ) = select_all_choice
        return instance

    @property
    def selected_areas(self):
        if self.select_all.data:
            return [self.select_all.area_slug]
        return self.areas.data


class ChangeSecurityKeyNameForm(StripWhitespaceForm):
    security_key_name = GovukTextInputField(
        "Name of key",
        validators=[
            DataRequired(message="Cannot be empty"),
            MustContainAlphanumericCharacters(),
            Length(max=255, message="Name of key must be 255 characters or fewer"),
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

    coat_of_arms_or_insignia = GovukRadiosField(
        "Coat of arms or insignia",
        choices=[
            (name, markup_for_crest_or_insignia(f"{name}.png") + name)
            for name in sorted(GOVERNMENT_IDENTITY_SYSTEM_CRESTS_OR_INSIGNIA)
        ],
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
        "Sign in method",
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


class FindByUuidForm(StripWhitespaceForm):
    search = GovukSearchField(
        "Find anything by UUID",
        validators=[DataRequired("Cannot be empty"), UUID("Enter a valid UUID")],
    )
