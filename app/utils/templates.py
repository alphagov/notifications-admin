from notifications_utils.template import (
    BroadcastPreviewTemplate,
    EmailPreviewTemplate,
    SMSPreviewTemplate,
)
from notifications_utils.template import LetterImageTemplate as UtilsLetterImageTemplate

from app.extensions import redis_client
from app.models import JSONModel
from app.notify_client import cache


class PrecompiledLetterImageTemplate(UtilsLetterImageTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override pre compiled letter template postage to None as it has not
        # yet been picked even though the pre compiled letter template has its
        # postage set as second class as the DB currently requires a non null
        # value of postage for letter templates
        self.postage = None


class TemplatedLetterImageTemplate(UtilsLetterImageTemplate):
    @property
    def page_count(self):
        from app.template_previews import get_page_count_for_letter

        if self._page_count:
            return self._page_count

        if self.values:
            self._page_count = get_page_count_for_letter(self._template, self.values)
            return self._page_count

        cache_key = f"service-{self._template['service']}-template-{self.id}-page-count"

        if cached_value := redis_client.get(cache_key):
            return cached_value

        self._page_count = get_page_count_for_letter(self._template)

        redis_client.set(cache_key, self._page_count, ex=cache.DEFAULT_TTL)

        return self._page_count

    @property
    def values(self):
        return super().values

    @values.setter
    def values(self, value):
        # If the personalisation changes then we might need to recalculate the page count
        self._page_count = None
        super(UtilsLetterImageTemplate, type(self)).values.fset(self, value)

    @property
    def attachment(self):
        if attachment := self.get_raw("letter_attachment"):
            return LetterAttachment(attachment)


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
):
    if "email" == template["template_type"]:
        return EmailPreviewTemplate(
            template,
            from_name=service.name,
            from_address=f"{service.email_from}@notifications.service.gov.uk",
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
        )
    if "broadcast" == template["template_type"]:
        return BroadcastPreviewTemplate(
            template,
        )
