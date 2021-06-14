from flask import current_app
from notifications_utils.template import (
    BroadcastPreviewTemplate,
    EmailPreviewTemplate,
    LetterImageTemplate,
    LetterPreviewTemplate,
    SMSPreviewTemplate,
)


def get_sample_template(template_type):
    if template_type == 'email':
        return EmailPreviewTemplate({'content': 'any', 'subject': '', 'template_type': 'email'})
    if template_type == 'sms':
        return SMSPreviewTemplate({'content': 'any', 'template_type': 'sms'})
    if template_type == 'letter':
        return LetterImageTemplate(
            {'content': 'any', 'subject': '', 'template_type': 'letter'}, postage='second', image_url='x', page_count=1
        )


def get_template(
    template,
    service,
    show_recipient=False,
    letter_preview_url=None,
    page_count=1,
    redact_missing_personalisation=False,
    email_reply_to=None,
    sms_sender=None,
):
    if 'email' == template['template_type']:
        return EmailPreviewTemplate(
            template,
            from_name=service.name,
            from_address='{}@notifications.service.gov.uk'.format(service.email_from),
            show_recipient=show_recipient,
            redact_missing_personalisation=redact_missing_personalisation,
            reply_to=email_reply_to,
        )
    if 'sms' == template['template_type']:
        return SMSPreviewTemplate(
            template,
            prefix=service.name,
            show_prefix=service.prefix_sms,
            sender=sms_sender,
            show_sender=bool(sms_sender),
            show_recipient=show_recipient,
            redact_missing_personalisation=redact_missing_personalisation,
        )
    if 'letter' == template['template_type']:
        if letter_preview_url:
            return LetterImageTemplate(
                template,
                image_url=letter_preview_url,
                page_count=int(page_count),
                contact_block=template['reply_to_text'],
                postage=template['postage'],
            )
        else:
            return LetterPreviewTemplate(
                template,
                contact_block=template['reply_to_text'],
                admin_base_url=current_app.config['ADMIN_BASE_URL'],
                redact_missing_personalisation=redact_missing_personalisation,
            )
    if 'broadcast' == template['template_type']:
        return BroadcastPreviewTemplate(
            template,
        )
