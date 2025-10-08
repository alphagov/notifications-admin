from datetime import datetime
from typing import Any

from flask import abort, current_app
from notifications_utils.serialised_model import SerialisedModelCollection
from werkzeug.utils import cached_property

from app.constants import (
    SERVICE_JOIN_REQUEST_APPROVED,
    SERVICE_JOIN_REQUEST_CANCELLED,
    SERVICE_JOIN_REQUEST_PENDING,
    SERVICE_JOIN_REQUEST_REJECTED,
    SIGN_IN_METHOD_TEXT,
    SIGN_IN_METHOD_TEXT_OR_EMAIL,
)
from app.models import JSONModel
from app.models.api_key import APIKeys
from app.models.branding import EmailBranding, LetterBranding
from app.models.contact_list import ContactLists
from app.models.job import ImmediateJobs, PaginatedJobs, PaginatedUploads, ScheduledJobs
from app.models.organisation import Organisation
from app.models.unsubscribe_requests_report import UnsubscribeRequestsReports
from app.models.user import InvitedUsers, User, Users
from app.notify_client.billing_api_client import billing_api_client
from app.notify_client.inbound_number_client import inbound_number_client
from app.notify_client.invite_api_client import invite_api_client
from app.notify_client.job_api_client import job_api_client
from app.notify_client.organisations_api_client import organisations_client
from app.notify_client.service_api_client import service_api_client
from app.notify_client.template_folder_api_client import template_folder_api_client
from app.utils import get_default_sms_sender
from app.utils.templates import get_template as get_template_as_rich_object


class Service(JSONModel):
    active: bool
    billing_contact_email_addresses: str
    billing_contact_names: str
    billing_reference: str
    confirmed_unique: bool
    contact_link: str
    count_as_live: bool
    custom_email_sender_name: str
    email_sender_local_part: str
    go_live_at: datetime
    has_active_go_live_request: bool
    id: Any
    email_message_limit: int
    international_sms_message_limit: int
    sms_message_limit: int
    letter_message_limit: int
    rate_limit: int
    name: str
    notes: str
    prefix_sms: bool
    purchase_order_number: str
    service_callback_api: Any
    volume_email: int
    volume_sms: int
    volume_letter: int

    __sort_attribute__ = "name"

    TEMPLATE_TYPES = (
        "email",
        "sms",
        "letter",
    )

    ALL_PERMISSIONS = TEMPLATE_TYPES + (
        "edit_folder_permissions",
        "email_auth",
        "inbound_sms",
        "international_letters",
        "international_sms",
        "sms_to_uk_landlines",
    )

    @classmethod
    def from_id(cls, service_id):
        return cls(service_api_client.get_service(service_id)["data"])

    @property
    def _permissions(self):
        return self._dict.get("permissions", self.TEMPLATE_TYPES)

    @property
    def permissions(self):
        raise NotImplementedError('Use Service.has_permission("…") instead')

    @property
    def billing_details(self):
        billing_details = [
            self.billing_contact_email_addresses,
            self.billing_contact_names,
            self.billing_reference,
            self.purchase_order_number,
        ]
        if any(billing_details):
            return billing_details
        else:
            return None

    def update(self, **kwargs):
        return service_api_client.update_service(self.id, **kwargs)

    def update_count_as_live(self, count_as_live):
        return service_api_client.update_count_as_live(self.id, count_as_live=count_as_live)

    def update_status(self, live):
        return service_api_client.update_status(self.id, live=live)

    def switch_permission(self, permission):
        return self.force_permission(
            permission,
            on=not self.has_permission(permission),
        )

    def force_permission(self, permission, on=False):
        permissions, permission = set(self._permissions), {permission}

        return self.update_permissions(
            permissions | permission if on else permissions - permission,
        )

    def update_permissions(self, permissions):
        return self.update(permissions=list(permissions))

    @property
    def trial_mode(self):
        return self._dict["restricted"]

    @property
    def live(self):
        return not self.trial_mode

    def has_permission(self, permission):
        if permission not in self.ALL_PERMISSIONS:
            raise KeyError(f"{permission} is not a service permission")
        return permission in self._permissions

    def get_page_of_jobs(self, page):
        return PaginatedJobs(self.id, page=page)

    def get_page_of_uploads(self, page):
        return PaginatedUploads(self.id, page=page)

    @cached_property
    def has_jobs(self):
        return job_api_client.has_jobs(self.id)

    @cached_property
    def immediate_jobs(self):
        if not self.has_jobs:
            return []
        return ImmediateJobs(self.id)

    @cached_property
    def scheduled_jobs(self):
        if not self.has_jobs:
            return []
        return ScheduledJobs(self.id)

    @cached_property
    def scheduled_job_stats(self):
        if not self.has_jobs:
            return {"count": 0}
        return job_api_client.get_scheduled_job_stats(self.id)

    @cached_property
    def invited_users(self):
        return InvitedUsers(self.id)

    def invite_pending_for(self, email_address):
        return email_address.lower() in (invited_user.email_address.lower() for invited_user in self.invited_users)

    @cached_property
    def active_users(self):
        return Users(self.id)

    def active_users_with_permission(self, permission):
        return tuple(user for user in self.active_users if user.has_permission_for_service(self.id, permission))

    @cached_property
    def team_members(self):
        return self.invited_users + self.active_users

    def team_members_with_permission(self, permission):
        return tuple(user for user in self.team_members if user.has_permission_for_service(self.id, permission))

    @cached_property
    def has_team_members_with_manage_service_permission(self):
        return len(self.team_members_with_permission("manage_service")) > 1

    def cancel_invite(self, invited_user_id):
        if str(invited_user_id) not in {user.id for user in self.invited_users}:
            abort(404)

        return invite_api_client.cancel_invited_user(
            service_id=self.id,
            invited_user_id=str(invited_user_id),
        )

    def create_service_join_request(self, user_to_invite, *, service_id, service_managers_ids, reason):
        service_api_client.create_service_join_request(
            user_to_invite.id,
            service_id=service_id,
            service_managers_ids=service_managers_ids,
            reason=reason,
        )

    def get_team_member(self, user_id):
        if str(user_id) not in {user.id for user in self.active_users}:
            abort(404)

        return User.from_id(user_id)

    @cached_property
    def all_templates(self):
        templates = service_api_client.get_service_templates(self.id)["data"]

        return [template for template in templates if template["template_type"] in self.available_template_types]

    @cached_property
    def all_template_ids(self):
        return {template["id"] for template in self.all_templates}

    def get_template(self, template_id, version=None, **kwargs):
        template = service_api_client.get_service_template(self.id, template_id, version)["data"]
        return get_template_as_rich_object(template, service=self, **kwargs)

    def get_template_folder_with_user_permission_or_403(self, folder_id, user):
        template_folder = self.get_template_folder(folder_id)

        if not user.has_template_folder_permission(template_folder, service=self):
            abort(403)

        return template_folder

    def get_template_with_user_permission_or_403(self, template_id, user, **kwargs):
        template = self.get_template(template_id, **kwargs)
        self.get_template_folder_with_user_permission_or_403(template.get_raw("folder"), user)

        return template

    def get_precompiled_letter_template(self, *, letter_preview_url, page_count):
        return get_template_as_rich_object(
            service_api_client.get_precompiled_template(self.id),
            self,
            letter_preview_url=letter_preview_url,
            page_count=page_count,
        )

    @property
    def available_template_types(self):
        return list(filter(self.has_permission, self.TEMPLATE_TYPES))

    @property
    def has_templates(self):
        return bool(self.all_templates)

    def has_folders(self):
        return bool(self.all_template_folders)

    @property
    def has_multiple_template_types(self):
        return len({template["template_type"] for template in self.all_templates}) > 1

    @property
    def has_estimated_usage(self):
        return any(self.volumes_by_channel.values())

    def has_templates_of_type(self, template_type):
        return any(template for template in self.all_templates if template["template_type"] == template_type)

    @property
    def has_email_templates(self):
        return self.has_templates_of_type("email")

    @property
    def has_sms_templates(self):
        return self.has_templates_of_type("sms")

    @property
    def intending_to_send_email(self):
        if self.volume_email is None:
            return self.has_email_templates
        return self.volume_email > 0

    @property
    def intending_to_send_sms(self):
        if self.volume_sms is None:
            return self.has_sms_templates
        return self.volume_sms > 0

    @cached_property
    def email_reply_to_addresses(self):
        return service_api_client.get_reply_to_email_addresses(self.id)

    @property
    def has_email_reply_to_address(self):
        return bool(self.email_reply_to_addresses)

    @property
    def count_email_reply_to_addresses(self):
        return len(self.email_reply_to_addresses)

    @property
    def default_email_reply_to_address(self):
        return next((x["email_address"] for x in self.email_reply_to_addresses if x["is_default"]), None)

    def get_email_reply_to_address(self, id):
        return service_api_client.get_reply_to_email_address(self.id, id)

    @property
    def needs_to_add_email_reply_to_address(self):
        return self.intending_to_send_email and not self.has_email_reply_to_address

    @property
    def shouldnt_use_govuk_as_sms_sender(self):
        return self.organisation_type != Organisation.TYPE_CENTRAL

    @cached_property
    def sms_senders(self):
        return service_api_client.get_sms_senders(self.id)

    @property
    def sms_senders_with_hints(self):
        def attach_hint(sender):
            hints = []
            if sender["is_default"]:
                hints += ["default"]
            if sender["inbound_number_id"]:
                hints += ["receives replies"]
            if hints:
                sender["hint"] = "(" + " and ".join(hints) + ")"
            return sender

        return [attach_hint(sender) for sender in self.sms_senders]

    @property
    def default_sms_sender(self):
        return get_default_sms_sender(self.sms_senders)

    @property
    def count_sms_senders(self):
        return len(self.sms_senders)

    @property
    def sms_sender_is_govuk(self):
        return self.default_sms_sender in {"GOVUK", "None"}

    def get_sms_sender(self, id):
        return service_api_client.get_sms_sender(self.id, id)

    @property
    def needs_to_change_sms_sender(self):
        return all(
            (
                self.intending_to_send_sms,
                self.shouldnt_use_govuk_as_sms_sender,
                self.sms_sender_is_govuk,
            )
        )

    @cached_property
    def letter_contact_details(self):
        return service_api_client.get_letter_contacts(self.id)

    @property
    def count_letter_contact_details(self):
        return len(self.letter_contact_details)

    @property
    def default_letter_contact_block(self):
        return next(
            (
                letter_contact_block
                for letter_contact_block in self.letter_contact_details
                if letter_contact_block["is_default"]
            ),
            None,
        )

    def edit_letter_contact_block(self, id, contact_block, is_default):
        service_api_client.update_letter_contact(
            self.id,
            letter_contact_id=id,
            contact_block=contact_block,
            is_default=is_default,
        )

    def remove_default_letter_contact_block(self):
        if self.default_letter_contact_block:
            self.edit_letter_contact_block(
                self.default_letter_contact_block["id"],
                self.default_letter_contact_block["contact_block"],
                is_default=False,
            )

    def get_letter_contact_block(self, id):
        return service_api_client.get_letter_contact(self.id, id)

    @property
    def volumes_by_channel(self):
        return {channel: getattr(self, f"volume_{channel}") for channel in ("email", "sms", "letter")}

    @property
    def go_live_checklist_completed(self):
        return all(
            (
                any(self.volumes_by_channel.values()),
                self.has_team_members_with_manage_service_permission,
                self.has_templates,
                not self.needs_to_add_email_reply_to_address,
                not self.needs_to_change_sms_sender,
                self.confirmed_unique,
            )
        )

    @property
    def go_live_user(self):
        return User.from_id(self._dict["go_live_user"])

    def notify_organisation_users_of_request_to_go_live(self):
        if self.organisation.can_approve_own_go_live_requests:
            return organisations_client.notify_users_of_request_to_go_live_for_service(self.id)

    @cached_property
    def free_sms_fragment_limit(self):
        return billing_api_client.get_free_sms_fragment_limit_for_year(self.id) or 0

    @cached_property
    def data_retention(self):
        return service_api_client.get_service_data_retention(self.id)

    def get_data_retention_item(self, id):
        return next((dr for dr in self.data_retention if dr["id"] == id), None)

    def get_days_of_retention(self, notification_type):
        return next((dr for dr in self.data_retention if dr["notification_type"] == notification_type), {}).get(
            "days_of_retention", current_app.config["ACTIVITY_STATS_LIMIT_DAYS"]
        )

    def get_consistent_data_retention_period(self) -> int | None:
        """If the service's data retention periods are all the same, returns that period. Otherwise returns None."""
        consistent_data_retention = (
            self.get_days_of_retention("email")
            == self.get_days_of_retention("sms")
            == self.get_days_of_retention("letter")
        )
        return self.get_days_of_retention("email") if consistent_data_retention else None

    @property
    def email_branding_id(self):
        return self._dict["email_branding"]

    @cached_property
    def email_branding(self):
        return EmailBranding.from_id(self.email_branding_id)

    @property
    def needs_to_change_email_branding(self):
        return self.email_branding.is_govuk and self.organisation_type != Organisation.TYPE_CENTRAL

    @property
    def letter_branding_id(self):
        return self._dict["letter_branding"]

    @cached_property
    def letter_branding(self):
        return LetterBranding.from_id(self.letter_branding_id)

    @cached_property
    def organisation(self):
        return Organisation.from_id(self.organisation_id)

    @property
    def organisation_id(self):
        return self._dict["organisation"]

    @property
    def organisation_type(self):
        return self.organisation.organisation_type or self._dict["organisation_type"]

    @property
    def organisation_name(self):
        if not self.organisation_id:
            return None
        return organisations_client.get_organisation_name(self.organisation_id)

    @property
    def organisation_type_label(self):
        return Organisation.TYPE_LABELS.get(self.organisation_type)

    @property
    def is_nhs(self):
        return self.organisation_type in Organisation.NHS_TYPES

    @cached_property
    def inbound_number(self):
        return inbound_number_client.get_inbound_sms_number_for_service(self.id)["data"].get("number", "")

    @property
    def has_inbound_number(self):
        return bool(self.inbound_number)

    @cached_property
    def inbound_sms_summary(self):
        if not self.has_permission("inbound_sms"):
            return None
        return service_api_client.get_inbound_sms_summary(self.id)

    @cached_property
    def all_template_folders(self):
        return sorted(
            template_folder_api_client.get_template_folders(self.id),
            key=lambda folder: folder["name"].lower(),
        )

    @cached_property
    def all_template_folder_ids(self):
        return {folder["id"] for folder in self.all_template_folders}

    def get_template_folder(self, folder_id):
        if folder_id is None:
            return {
                "id": None,
                "name": "Templates",
                "parent_id": None,
            }
        return self._get_by_id(self.all_template_folders, folder_id)

    def get_template_folder_path(self, template_folder_id):
        folder = self.get_template_folder(template_folder_id)

        if folder["id"] is None:
            return [folder]

        return self.get_template_folder_path(folder["parent_id"]) + [self.get_template_folder(folder["id"])]

    def get_template_path(self, template):
        return self.get_template_folder_path(template["folder"]) + [
            template,
        ]

    @property
    def count_of_templates_and_folders(self):
        return len(self.all_templates + self.all_template_folders)

    def move_to_folder(self, ids_to_move, move_to):
        ids_to_move = set(ids_to_move)

        template_folder_api_client.move_to_folder(
            service_id=self.id,
            folder_id=move_to,
            template_ids=ids_to_move & self.all_template_ids,
            folder_ids=ids_to_move & self.all_template_folder_ids,
        )

    @cached_property
    def api_keys(self):
        return APIKeys(self.id)

    @property
    def able_to_accept_agreement(self):
        return self.organisation.agreement_signed is not None or self.organisation_type in {
            Organisation.TYPE_NHS_GP,
            Organisation.TYPE_NHS_LOCAL,
        }

    @cached_property
    def returned_letter_statistics(self):
        return service_api_client.get_returned_letter_statistics(self.id)

    @cached_property
    def returned_letter_summary(self):
        return service_api_client.get_returned_letter_summary(self.id)

    @property
    def count_of_returned_letters_in_last_7_days(self):
        return self.returned_letter_statistics["returned_letter_count"]

    @property
    def date_of_most_recent_returned_letter_report(self):
        return self.returned_letter_statistics["most_recent_report"]

    @property
    def has_returned_letters(self):
        return bool(self.date_of_most_recent_returned_letter_report)

    @property
    def contact_lists(self):
        return ContactLists(self.id)

    @property
    def email_branding_pool(self):
        return self.organisation.email_branding_pool

    @property
    def letter_branding_pool(self):
        return self.organisation.letter_branding_pool

    @property
    def can_use_govuk_branding(self):
        return self.organisation_type == Organisation.TYPE_CENTRAL and not self.organisation.email_branding

    def get_message_limit(self, notification_type):
        return getattr(self, f"{notification_type}_message_limit")

    def remaining_messages(self, notification_type):
        if notification_type == "international_sms" and not self.has_permission("international_sms"):
            return 0
        return self.get_message_limit(notification_type) - self.sent_today(notification_type)

    def sent_today(self, notification_type):
        return service_api_client.get_notification_count(self.id, notification_type=notification_type)

    @property
    def sign_in_method(self) -> str:
        if self.has_permission("email_auth"):
            return SIGN_IN_METHOD_TEXT_OR_EMAIL

        return SIGN_IN_METHOD_TEXT

    @property
    def email_sender_name(self) -> str:
        return self.custom_email_sender_name or self.name

    @property
    def unsubscribe_request_reports_summary(self):
        return UnsubscribeRequestsReports(self.id)

    @property
    def unsubscribe_requests_statistics(self) -> dict:
        return service_api_client.get_unsubscribe_request_statistics(self.id)

    @property
    def unsubscribe_requests_count(self) -> int:
        return self.unsubscribe_requests_statistics["unsubscribe_requests_count"]

    @property
    def datetime_of_latest_unsubscribe_request(self) -> str | None:
        return self.unsubscribe_requests_statistics["datetime_of_latest_unsubscribe_request"]

    @property
    def can_have_multiple_callbacks(self):
        if self.has_permission("inbound_sms") or self.has_permission("letter"):
            return True
        return False

    @property
    def inbound_sms_callback_details(self):
        return self.get_service_callback_details("inbound_sms")

    @property
    def delivery_status_callback_details(self):
        return self.get_service_callback_details("delivery_status")

    @property
    def returned_letters_callback_details(self):
        return self.get_service_callback_details("returned_letter")

    def get_service_callback_details(self, callback_type):
        if callback_api := self.service_callback_api:
            for row in callback_api:
                if row["callback_type"] == callback_type:
                    return service_api_client.get_service_callback_api(
                        self.id, row["callback_id"], row["callback_type"]
                    )


class Services(SerialisedModelCollection):
    model = Service


class ServiceJoinRequest(JSONModel):
    id: Any
    requester: Any
    service_id: Any
    created_at: datetime
    status_changed_at: datetime
    status_changed_by: Any
    reason: str
    status: str
    contacted_service_users: list[str]
    requested_service: Any
    permissions: list[str]

    __sort_attribute__ = "id"

    @property
    def is_pending(self):
        return self.status == SERVICE_JOIN_REQUEST_PENDING

    @property
    def is_approved(self):
        return self.status == SERVICE_JOIN_REQUEST_APPROVED

    @property
    def is_rejected(self):
        return self.status == SERVICE_JOIN_REQUEST_REJECTED

    @property
    def is_cancelled(self):
        return self.status == SERVICE_JOIN_REQUEST_CANCELLED

    @classmethod
    def from_id(cls, request_id, service_id):
        return cls(service_api_client.get_service_join_request(request_id, service_id))

    def update(self, **kwargs):
        return service_api_client.update_service_join_requests(self.id, self.requester["id"], self.service_id, **kwargs)
