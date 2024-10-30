from datetime import datetime
from typing import Any

from markupsafe import Markup
from notifications_utils.template import (
    LetterPreviewTemplate,
    SMSBodyPreviewTemplate,
)

from app.models import JSONModel, ModelList
from app.notify_client.notification_api_client import notification_api_client
from app.notify_client.service_api_client import service_api_client
from app.utils.templates import EmailPreviewTemplate


class Notification(JSONModel):
    id: Any
    to: str
    recipient: str
    template: Any
    job: Any
    sent_at: datetime
    created_at: datetime
    created_by: Any
    updated_at: datetime
    job_row_number: int
    service: Any
    template_version: int
    postage: str
    notification_type: str
    reply_to_text: str
    client_reference: str
    created_by_name: str
    created_by_email_address: str
    job_name: str
    api_key_name: str

    __sort_attribute__ = "created_at"

    @property
    def status(self):
        return self._dict["status"]

    @property
    def content(self):
        return self.template["content"]

    @property
    def redact_personalisation(self):
        return self.template.get("redact_personalisation")

    @property
    def personalisation(self):
        if self.redact_personalisation:
            return {}
        return self._dict["personalisation"]

    @property
    def preview_of_content(self):
        if self.template["is_precompiled_letter"]:
            return self.client_reference

        if self.template["template_type"] == "sms":
            return str(
                SMSBodyPreviewTemplate(
                    self.template,
                    self.personalisation,
                )
            )

        if self.template["template_type"] == "email":
            return Markup(
                EmailPreviewTemplate(
                    self.template,
                    self.personalisation,
                    redact_missing_personalisation=True,
                ).subject
            )

        if self.template["template_type"] == "letter":
            return Markup(
                LetterPreviewTemplate(
                    self.template,
                    self.personalisation,
                ).subject
            )


class APINotification(Notification):
    key_name: str

    @property
    def status(self):
        if self.notification_type == "letter":
            if self._dict["status"] in ("created", "sending"):
                return "accepted"

            if self._dict["status"] in ("delivered", "returned-letter"):
                return "received"

        return self._dict["status"]


class Notifications(ModelList):
    model = Notification

    @staticmethod
    def _get_items(*args, **kwargs):
        return notification_api_client.get_notifications_for_service(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        resp = self._get_items(*args, **kwargs)
        self.items = resp["notifications"]
        self.prev = resp.get("links", {}).get("prev", None)
        self.next = resp.get("links", {}).get("next", None)


class NotificationForCSV(Notification):
    row_number: Any  # Can be an empty string so can’t cast to `int`
    created_at: str  # API returns this field pre-formatted in Europe/London timezone
    template_name: str
    template_type: str


class NotificationsForCSV(Notifications):
    model = NotificationForCSV

    @staticmethod
    def _get_items(*args, **kwargs):
        return notification_api_client.get_notifications_for_service_for_csv(*args, **kwargs)


class APINotifications(Notifications):
    model = APINotification

    def __init__(self, service_id):
        super().__init__(
            service_id,
            include_jobs=False,
            include_from_test_key=True,
            include_one_off=False,
            count_pages=False,
        )


class InboundSMSMessage(JSONModel):
    user_number: str
    notify_number: str
    content: str
    created_at: datetime
    id: Any

    __sort_attribute__ = "created_at"

    personalisation = None
    redact_personalisation = False
    status = None


class InboundSMSMessages(ModelList):
    model = InboundSMSMessage

    @staticmethod
    def _get_items(*args, **kwargs):
        return service_api_client.get_inbound_sms(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        self.items = self._get_items(*args, **kwargs)["data"]
