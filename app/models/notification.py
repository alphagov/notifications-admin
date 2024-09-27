from datetime import datetime
from typing import Any

from markupsafe import Markup
from notifications_utils.template import (
    EmailPreviewTemplate,
    LetterPreviewTemplate,
    SMSBodyPreviewTemplate,
)

from app.models import JSONModel, ModelList
from app.notify_client.notification_api_client import notification_api_client


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
    row_number: int
    job_row_number: int
    service: Any
    template_version: int
    personalisation: dict
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
    def preview_of_content(self):
        if self.template.get("redact_personalisation"):
            self.personalisation = {}

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
