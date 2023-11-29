import json
from typing import Optional

from flask import current_app, render_template
from markupsafe import Markup
from notifications_utils.countries import Postage
from notifications_utils.formatters import formatted_list
from notifications_utils.template import (
    BaseLetterTemplate,
    BroadcastPreviewTemplate,
    EmailPreviewTemplate,
    SMSPreviewTemplate,
)

from app.extensions import redis_client
from app.models import JSONModel
from app.notify_client import cache


class BaseLetterImageTemplate(BaseLetterTemplate):
    first_page_number = 1
    allowed_postage_types = (
        Postage.FIRST,
        Postage.SECOND,
        Postage.EUROPE,
        Postage.REST_OF_WORLD,
    )

    def __init__(
        self,
        template,
        values=None,
        image_url=None,
        page_count=None,
        contact_block=None,
    ):
        super().__init__(template, values, contact_block=contact_block)
        self.image_url = image_url
        self._page_count = page_count
        self.postage = template.get("postage")

    @property
    def jinja_template(self):
        return current_app.jinja_env.get_template("partials/templates/letter_image_template.jinja2")

    @property
    def page_count(self):
        return self._page_count

    @property
    def postage(self):
        if self.postal_address.international:
            return self.postal_address.postage
        return self._postage

    @postage.setter
    def postage(self, value):
        if value not in [None] + list(self.allowed_postage_types):
            raise TypeError(
                "postage must be None, {}".format(
                    formatted_list(
                        self.allowed_postage_types,
                        conjunction="or",
                        before_each="'",
                        after_each="'",
                    )
                )
            )
        self._postage = value

    @property
    def last_page_number(self):
        return min(self.page_count, self.max_page_count) + self.first_page_number

    @property
    def page_numbers(self):
        return list(range(self.first_page_number, self.last_page_number))

    @property
    def postage_description(self):
        return {
            Postage.FIRST: "first class",
            Postage.SECOND: "second class",
            Postage.EUROPE: "international",
            Postage.REST_OF_WORLD: "international",
        }.get(self.postage)

    @property
    def postage_class_value(self):
        return {
            Postage.FIRST: "letter-postage-first",
            Postage.SECOND: "letter-postage-second",
            Postage.EUROPE: "letter-postage-international",
            Postage.REST_OF_WORLD: "letter-postage-international",
        }.get(self.postage)

    @property
    def jinja_render_data(self):
        return {
            "template": self,
            "image_url": self.image_url,
            "page_numbers": self.page_numbers,
            "address": self._address_block,
            "contact_block": self._contact_block,
            "date": self._date,
            "subject": self.subject,
            "message": self._message,
            "show_postage": bool(self.postage),
            "postage_description": self.postage_description,
            "postage_class_value": self.postage_class_value,
        }

    def __str__(self):
        for attr in ("page_count", "image_url"):
            if not getattr(self, attr):
                raise TypeError(f"{attr} is required to render {type(self).__name__}")

        return Markup(render_template(self.jinja_template, **self.jinja_render_data))


class PrecompiledLetterImageTemplate(BaseLetterImageTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override pre compiled letter template postage to None as it has not
        # yet been picked even though the pre compiled letter template has its
        # postage set as second class as the DB currently requires a non null
        # value of postage for letter templates
        self.postage = None


class TemplatedLetterImageTemplate(BaseLetterImageTemplate):
    def __init__(
        self,
        template,
        values=None,
        image_url=None,
        contact_block=None,
        include_letter_edit_ui_overlay=False,
    ):
        super().__init__(template, values, image_url=image_url, page_count=None, contact_block=contact_block)
        self._all_page_counts = None
        self.include_letter_edit_ui_overlay = include_letter_edit_ui_overlay

    @property
    def all_page_counts(self):
        from app.template_previews import get_page_counts_for_letter

        if self._all_page_counts:
            return self._all_page_counts

        if self.values:
            self._all_page_counts = get_page_counts_for_letter(self._template, self.values)
            return self._all_page_counts

        cache_key = f"service-{self._template['service']}-template-{self.id}-all-page-counts"
        if cached_value := redis_client.get(cache_key):
            self._all_page_counts = json.loads(cached_value)
            return self._all_page_counts

        self._all_page_counts = get_page_counts_for_letter(self._template, self.values)
        redis_client.set(cache_key, json.dumps(self._all_page_counts), ex=cache.DEFAULT_TTL)

        return self._all_page_counts

    @property
    def page_count(self):
        return self.all_page_counts["count"]

    @property
    def welsh_page_count(self) -> int:
        return self.all_page_counts["welsh_page_count"]

    @property
    def english_page_count(self) -> int:
        return self.page_count - self.welsh_page_count - self.attachment_page_count

    @property
    def attachment_page_count(self) -> int:
        return self.all_page_counts["attachment_page_count"]

    @property
    def first_english_page(self) -> int:
        return self.welsh_page_count + 1

    @property
    def first_attachment_page(self) -> Optional[int]:
        if not self.attachment:
            return None

        return self.welsh_page_count + self.english_page_count + 1

    @property
    def values(self):
        return super().values

    @values.setter
    def values(self, value):
        # If the personalisation changes then we might need to recalculate the page count
        self._all_page_counts = None
        super(BaseLetterImageTemplate, type(self)).values.fset(self, value)

    @property
    def attachment(self):
        if attachment := self.get_raw("letter_attachment"):
            return LetterAttachment(attachment)

    @property
    def jinja_render_data(self):
        return super().jinja_render_data | {
            "first_page_of_attachment": self.first_attachment_page,
            "first_page_of_english": self.first_english_page,
        }


class LetterAttachment(JSONModel):
    ALLOWED_PROPERTIES = {
        "id",
        "original_filename",
        "page_count",
    }
    __sort_attribute__ = "original_filename"


def get_sample_template(template_type):
    if template_type == "email":
        return EmailPreviewTemplate({"content": "any", "subject": "", "template_type": "email"})
    if template_type == "sms":
        return SMSPreviewTemplate({"content": "any", "template_type": "sms"})
    if template_type == "letter":
        return TemplatedLetterImageTemplate({"content": "any", "subject": "", "template_type": "letter"})


def get_template(
    template,
    service,
    show_recipient=False,
    letter_preview_url=None,
    page_count=None,
    redact_missing_personalisation=False,
    email_reply_to=None,
    sms_sender=None,
    include_letter_edit_ui_overlay=False,
):
    if "email" == template["template_type"]:
        return EmailPreviewTemplate(
            template,
            from_name=service.email_sender_name,
            show_recipient=show_recipient,
            redact_missing_personalisation=redact_missing_personalisation,
            reply_to=email_reply_to,
        )
    if "sms" == template["template_type"]:
        return SMSPreviewTemplate(
            template,
            prefix=service.name,
            show_prefix=service.prefix_sms,
            sender=sms_sender,
            show_sender=bool(sms_sender),
            show_recipient=show_recipient,
            redact_missing_personalisation=redact_missing_personalisation,
        )
    if "letter" == template["template_type"]:
        if template.get("is_precompiled_letter"):
            return PrecompiledLetterImageTemplate(
                template,
                image_url=letter_preview_url,
                page_count=page_count,
            )
        return TemplatedLetterImageTemplate(
            template,
            image_url=letter_preview_url,
            contact_block=template["reply_to_text"],
            include_letter_edit_ui_overlay=include_letter_edit_ui_overlay,
        )
    if "broadcast" == template["template_type"]:
        return BroadcastPreviewTemplate(
            template,
        )
