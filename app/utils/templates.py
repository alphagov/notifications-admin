from notifications_utils.template import (
    BroadcastPreviewTemplate,
    EmailPreviewTemplate,
    SMSPreviewTemplate,
)
from notifications_utils.template import LetterImageTemplate as UtilsLetterImageTemplate


class PrecompiledLetterImageTemplate(UtilsLetterImageTemplate):
    pass


class TemplatedLetterImageTemplate(UtilsLetterImageTemplate):
    def __init__(
        self,
        template,
        values=None,
        image_url=None,
        contact_block=None,
        postage=None,
    ):
        super().__init__(
            template,
            values=values,
            image_url=image_url,
            page_count=1,
            contact_block=contact_block,
            postage=postage,
        )
        self._page_count = None

    @property
    def page_count(self):
        from app.template_previews import get_page_count_for_letter

        if self._page_count is None:
            self._page_count = get_page_count_for_letter(self._template, self.values)
        return self._page_count

    @property
    def values(self):
        return super().values

    @values.setter
    def values(self, value):
        # If the personalisation changes then we might need to recalculate the page count
        self._page_count = None
        super(UtilsLetterImageTemplate, type(self)).values.fset(self, value)


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
                postage=template["postage"],
                page_count=page_count,
            )
        return TemplatedLetterImageTemplate(
            template,
            image_url=letter_preview_url,
            contact_block=template["reply_to_text"],
            postage=template["postage"],
        )
    if "broadcast" == template["template_type"]:
        return BroadcastPreviewTemplate(
            template,
        )
