from datetime import datetime
from typing import Any

from markupsafe import Markup
from notifications_utils.letter_timings import get_letter_timings, letter_can_be_cancelled
from notifications_utils.template import (
    LetterPreviewTemplate,
    SMSBodyPreviewTemplate,
)
from werkzeug.utils import cached_property

from app.models import JSONModel, ModelList
from app.models.api_key import APIKey
from app.notify_client.notification_api_client import notification_api_client
from app.notify_client.service_api_client import service_api_client
from app.utils import DELIVERED_STATUSES, FAILURE_STATUSES
from app.utils.letters import get_letter_printing_statement
from app.utils.templates import EmailPreviewTemplate


class Notification(JSONModel):
    id: Any
    to: str
    recipient: str
    template: Any
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

    @classmethod
    def from_id_and_service_id(cls, id, service_id):
        return cls(notification_api_client.get_notification(service_id, str(id)))

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
    def key_type(self):
        return self._dict.get("key_type")

    @property
    def sent_with_test_key(self):
        return self.key_type == APIKey.TYPE_TEST

    @property
    def sent_by(self):
        return self._dict.get("sent_by")

    @property
    def _personalisation(self):
        if self.redact_personalisation:
            return {}
        return self._dict["personalisation"]

    @property
    def personalisation(self):
        if self.template["template_type"] == "email":
            return self._personalisation | {"email_address": self.to}

        if self.template["template_type"] == "sms":
            return self._personalisation | {"phone_number": self.to}

        return self._personalisation

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

    @cached_property
    def job(self):
        from app.models.job import Job

        if self._dict["job"]:
            return Job.from_id(self._dict["job"]["id"], self.service_id)

    @property
    def estimated_letter_delivery_date(self):
        if self.notification_type == "letter":
            return get_letter_timings(self.created_at.replace(tzinfo=None), postage=self.postage).latest_delivery

    @property
    def letter_can_be_cancelled(self):
        if self.notification_type == "letter":
            return letter_can_be_cancelled(self.status, self.created_at.replace(tzinfo=None))

    @property
    def letter_print_day(self):
        return get_letter_printing_statement(self.status, self.created_at)

    @property
    def is_precompiled_letter(self):
        return self.template["is_precompiled_letter"]

    @property
    def displayed_postage(self):
        if self.status == "validation-failed":
            return None
        return self.postage

    @property
    def finished(self):
        return self.status in (DELIVERED_STATUSES + FAILURE_STATUSES)


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
