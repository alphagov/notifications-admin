from contextvars import ContextVar
from datetime import datetime

from flask import current_app
from notifications_utils.clients.redis import daily_limit_cache_key
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.constants import LetterLanguageOptions
from app.extensions import redis_client
from app.notify_client import NotifyAdminAPIClient, _attach_current_user, cache

ALLOWED_TEMPLATE_ATTRIBUTES = {
    "content",
    "letter_languages",
    "name",
    "postage",
    "subject",
    "letter_welsh_subject",
    "letter_welsh_content",
    "has_unsubscribe_link",
}


class ServiceAPIClient(NotifyAdminAPIClient):
    def __init__(self, app):
        super().__init__(app)

        self.admin_url = app.config["ADMIN_BASE_URL"]

    @cache.delete("user-{user_id}")
    def create_service(
        self,
        service_name,
        organisation_type,
        email_message_limit,
        international_sms_message_limit,
        sms_message_limit,
        letter_message_limit,
        restricted,
        user_id,
    ):
        """
        Create a service and return the json.
        """
        data = {
            "name": service_name,
            "organisation_type": organisation_type,
            "active": True,
            "email_message_limit": email_message_limit,
            "international_sms_message_limit": international_sms_message_limit,
            "sms_message_limit": sms_message_limit,
            "letter_message_limit": letter_message_limit,
            "user_id": user_id,
            "restricted": restricted,
        }
        data = _attach_current_user(data)
        return self.post("/service", data)["data"]["id"]

    @cache.set("service-{service_id}")
    def get_service(self, service_id):
        """
        Retrieve a service.
        """
        return self.get(f"/service/{service_id}")

    def get_service_statistics(self, service_id, limit_days=None):
        return self.get(f"/service/{service_id}/statistics", params={"limit_days": limit_days})["data"]

    def get_services(self, params_dict=None):
        """
        Retrieve a list of services.
        """
        return self.get("/service", params=params_dict)

    def find_services_by_name(self, service_name):
        return self.get("/service/find-services-by-name", params={"service_name": service_name})

    def get_live_services_data(self, params_dict=None):
        """
        Retrieve a list of live services data with contact names and notification counts.
        """
        return self.get("/service/live-services-data", params=params_dict)

    def get_active_services(self, params_dict=None):
        """
        Retrieve a list of active services.
        """
        params_dict["only_active"] = True
        return self.get_services(params_dict)

    @cache.delete("service-{service_id}")
    def update_service(self, service_id, **kwargs):
        """
        Update a service.
        """
        data = _attach_current_user(kwargs)
        disallowed_attributes = set(data.keys()) - {
            "active",
            "billing_contact_email_addresses",
            "billing_contact_names",
            "billing_reference",
            "confirmed_unique",
            "contact_link",
            "created_by",
            "count_as_live",
            "custom_email_sender_name",
            "email_branding",
            "free_sms_fragment_limit",
            "go_live_at",
            "go_live_user",
            "has_active_go_live_request",
            "letter_branding",
            "letter_contact_block",
            "email_message_limit",
            "international_sms_message_limit",
            "sms_message_limit",
            "letter_message_limit",
            "name",
            "notes",
            "organisation_type",
            "permissions",
            "prefix_sms",
            "purchase_order_number",
            "rate_limit",
            "reply_to_email_address",
            "restricted",
            "sms_sender",
            "volume_email",
            "volume_letter",
            "volume_sms",
        }
        if disallowed_attributes := ", ".join(disallowed_attributes):
            raise TypeError(f"Not allowed to update service attributes: {disallowed_attributes}")

        endpoint = f"/service/{service_id}"
        return self.post(endpoint, data)

    @cache.delete("live-service-and-organisation-counts")
    def update_status(self, service_id, live):
        from flask import current_app

        def get_daily_limit(live, channel):
            if live:
                return current_app.config["DEFAULT_LIVE_SERVICE_RATE_LIMITS"][channel]
            return current_app.config["DEFAULT_SERVICE_LIMIT"]

        return self.update_service(
            service_id,
            email_message_limit=get_daily_limit(live, "email"),
            sms_message_limit=get_daily_limit(live, "sms"),
            letter_message_limit=get_daily_limit(live, "letter"),
            restricted=(not live),
            go_live_at=str(datetime.utcnow()) if live else None,
            has_active_go_live_request=False,
        )

    @cache.delete("live-service-and-organisation-counts")
    def update_count_as_live(self, service_id, count_as_live):
        return self.update_service(
            service_id,
            count_as_live=count_as_live,
        )

    @cache.delete("service-{service_id}")
    @cache.delete_by_pattern("service-{service_id}-template*")
    def archive_service(self, service_id, cached_service_user_ids):
        if cached_service_user_ids:
            redis_client.delete(*map("user-{}".format, cached_service_user_ids))
        return self.post(f"/service/{service_id}/archive", data=None)

    @cache.delete("service-{service_id}")
    @cache.delete("user-{user_id}")
    def remove_user_from_service(self, service_id, user_id):
        """
        Remove a user from a service
        """
        endpoint = f"/service/{service_id}/users/{user_id}"
        data = _attach_current_user({})
        return self.delete(endpoint, data)

    @cache.delete("service-{service_id}-templates")
    def create_service_template(
        self,
        *,
        name,
        type_,
        content,
        service_id,
        subject=None,
        parent_folder_id=None,
        letter_languages: LetterLanguageOptions | None = None,
        letter_welsh_subject: str = None,
        letter_welsh_content: str = None,
        has_unsubscribe_link: bool | None = None,
    ):
        """
        Create a service template.
        """
        data = {
            "name": name,
            "template_type": type_,
            "content": content,
            "service": service_id,
            "has_unsubscribe_link": has_unsubscribe_link,
        }
        if subject:
            data.update({"subject": subject})
        if parent_folder_id:
            data.update({"parent_folder_id": parent_folder_id})
        if letter_languages is not None:
            data |= {
                "letter_languages": letter_languages,
                "letter_welsh_subject": letter_welsh_subject,
                "letter_welsh_content": letter_welsh_content,
            }
        if has_unsubscribe_link is not None:
            data |= {
                "has_unsubscribe_link": has_unsubscribe_link,
            }
        data = _attach_current_user(data)
        endpoint = f"/service/{service_id}/template"
        return self.post(endpoint, data)

    @cache.delete("service-{service_id}-templates")
    @cache.delete_by_pattern("service-{service_id}-template-{template_id}*")
    def update_service_template(self, service_id, template_id, **kwargs):
        """
        Update a service template.
        """
        disallowed_attributes = set(kwargs.keys()) - ALLOWED_TEMPLATE_ATTRIBUTES
        if disallowed_attributes:
            raise TypeError(f"Not allowed to update template attributes: {', '.join(disallowed_attributes)}")
        data = _attach_current_user(kwargs)
        endpoint = f"/service/{service_id}/template/{template_id}"
        return self.post(endpoint, data)

    @cache.delete("service-{service_id}-templates")
    @cache.delete_by_pattern("service-{service_id}-template-{id_}*")
    def redact_service_template(self, service_id, id_):
        return self.post(
            f"/service/{service_id}/template/{id_}",
            _attach_current_user({"redact_personalisation": True}),
        )

    @cache.delete("service-{service_id}-templates")
    @cache.delete_by_pattern("service-{service_id}-template-{template_id}*")
    def update_service_template_sender(self, service_id, template_id, reply_to):
        data = {
            "reply_to": reply_to,
        }
        data = _attach_current_user(data)
        return self.post(f"/service/{service_id}/template/{template_id}", data)

    @cache.set("service-{service_id}-template-{template_id}-version-{version}")
    def get_service_template(self, service_id, template_id, version=None):
        """
        Retrieve a service template.
        """
        endpoint = f"/service/{service_id}/template/{template_id}"
        if version:
            endpoint = f"{endpoint}/version/{version}"
        return self.get(endpoint)

    @cache.set("service-{service_id}-template-{template_id}-versions")
    def get_service_template_versions(self, service_id, template_id):
        """
        Retrieve a list of versions for a template
        """
        endpoint = f"/service/{service_id}/template/{template_id}/versions"
        return self.get(endpoint)

    @cache.set("service-{service_id}-template-precompiled")
    def get_precompiled_template(self, service_id):
        """
        Returns the precompiled template for a service, creating it if it doesn't already exist
        """
        return self.get(f"/service/{service_id}/template/precompiled")

    @cache.set("service-{service_id}-templates")
    def get_service_templates(self, service_id):
        """
        Retrieve all templates for service.
        """
        endpoint = f"/service/{service_id}/template?detailed=False"
        return self.get(endpoint)

    # This doesn’t need caching because it calls through to a method which is cached
    def count_service_templates(self, service_id, template_type=None):
        return len(
            [
                template
                for template in self.get_service_templates(service_id)["data"]
                if (not template_type or template["template_type"] == template_type)
            ]
        )

    @cache.delete("service-{service_id}-templates")
    @cache.delete_by_pattern("service-{service_id}-template-{template_id}*")
    def delete_service_template(self, service_id, template_id):
        """
        Set a service template's archived flag to True
        """
        endpoint = f"/service/{service_id}/template/{template_id}"
        data = {"archived": True}
        data = _attach_current_user(data)
        return self.post(endpoint, data=data)

    # Temp access of service history data. Includes service and api key history
    def get_service_history(self, service_id):
        return self.get(f"/service/{service_id}/history")["data"]

    def get_service_service_history(self, service_id):
        return self.get_service_history(service_id)["service_history"]

    def get_service_api_key_history(self, service_id):
        return self.get_service_history(service_id)["api_key_history"]

    def get_monthly_notification_stats(self, service_id, year):
        return self.get(f"/service/{service_id}/notifications/monthly?year={year}")

    def get_guest_list(self, service_id):
        return self.get(f"/service/{service_id}/guest-list")

    @cache.delete("service-{service_id}")
    def update_guest_list(self, service_id, data):
        return self.put(f"/service/{service_id}/guest-list", data=data)

    def get_inbound_sms(self, service_id, user_number=""):
        # POST prevents the user phone number leaking into our logs
        return self.post(
            f"/service/{service_id}/inbound-sms",
            data={"phone_number": user_number},
        )

    def get_most_recent_inbound_sms(self, service_id, page=None):
        return self.get(
            f"/service/{service_id}/inbound-sms/most-recent",
            params={"page": page},
        )

    def get_inbound_sms_by_id(self, service_id, notification_id):
        return self.get(f"/service/{service_id}/inbound-sms/{notification_id}")

    def get_inbound_sms_summary(self, service_id):
        return self.get(f"/service/{service_id}/inbound-sms/summary")

    @cache.delete("service-{service_id}")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def remove_service_inbound_sms(self, service_id, archive: bool):
        return self.post(f"/service/{service_id}/inbound-sms/remove", data={"archive": archive})

    def get_most_recent_inbound_number_usage_date(self, service_id):
        return self.get(
            f"/service/{service_id}/inbound-sms/most-recent-usage",
        )

    def get_reply_to_email_addresses(self, service_id):
        return self.get(f"/service/{service_id}/email-reply-to")

    def get_reply_to_email_address(self, service_id, reply_to_email_id):
        return self.get(f"/service/{service_id}/email-reply-to/{reply_to_email_id}")

    def verify_reply_to_email_address(self, service_id, email_address):
        return self.post(f"/service/{service_id}/email-reply-to/verify", data={"email": email_address})

    @cache.delete("service-{service_id}")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def add_reply_to_email_address(self, service_id, email_address, is_default=False):
        return self.post(
            f"/service/{service_id}/email-reply-to",
            data={"email_address": email_address, "is_default": is_default},
        )

    @cache.delete("service-{service_id}")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def update_reply_to_email_address(self, service_id, reply_to_email_id, email_address, is_default=False):
        return self.post(
            f"/service/{service_id}/email-reply-to/{reply_to_email_id}",
            data={"email_address": email_address, "is_default": is_default},
        )

    @cache.delete("service-{service_id}")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def delete_reply_to_email_address(self, service_id, reply_to_email_id):
        return self.post(f"/service/{service_id}/email-reply-to/{reply_to_email_id}/archive", data=None)

    def get_letter_contacts(self, service_id):
        return self.get(f"/service/{service_id}/letter-contact")

    def get_letter_contact(self, service_id, letter_contact_id):
        return self.get(f"/service/{service_id}/letter-contact/{letter_contact_id}")

    @cache.delete("service-{service_id}")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def add_letter_contact(self, service_id, contact_block, is_default=False):
        return self.post(
            f"/service/{service_id}/letter-contact",
            data={"contact_block": contact_block, "is_default": is_default},
        )

    @cache.delete("service-{service_id}")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def update_letter_contact(self, service_id, letter_contact_id, contact_block, is_default=False):
        return self.post(
            f"/service/{service_id}/letter-contact/{letter_contact_id}",
            data={"contact_block": contact_block, "is_default": is_default},
        )

    @cache.delete("service-{service_id}")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def delete_letter_contact(self, service_id, letter_contact_id):
        return self.post(f"/service/{service_id}/letter-contact/{letter_contact_id}/archive", data=None)

    def get_sms_senders(self, service_id):
        return self.get(f"/service/{service_id}/sms-sender")

    def get_sms_sender(self, service_id, sms_sender_id):
        return self.get(f"/service/{service_id}/sms-sender/{sms_sender_id}")

    @cache.delete("service-{service_id}")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def add_sms_sender(self, service_id, sms_sender, is_default=False):
        data = {"sms_sender": sms_sender, "is_default": is_default}

        return self.post(f"/service/{service_id}/sms-sender", data=data)

    @cache.delete("service-{service_id}")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def update_sms_sender(self, service_id, sms_sender_id, sms_sender, is_default=False):
        return self.post(
            f"/service/{service_id}/sms-sender/{sms_sender_id}",
            data={"sms_sender": sms_sender, "is_default": is_default},
        )

    @cache.delete("service-{service_id}")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def delete_sms_sender(self, service_id, sms_sender_id):
        return self.post(f"/service/{service_id}/sms-sender/{sms_sender_id}/archive", data=None)

    @cache.delete("service-{service_id}-data-retention")
    def create_service_data_retention(self, service_id, notification_type, days_of_retention):
        data = {"notification_type": notification_type, "days_of_retention": days_of_retention}

        return self.post(f"/service/{service_id}/data-retention", data)

    @cache.delete("service-{service_id}-data-retention")
    def update_service_data_retention(self, service_id, data_retention_id, days_of_retention):
        data = {"days_of_retention": days_of_retention}
        return self.post(f"/service/{service_id}/data-retention/{data_retention_id}", data)

    @cache.delete("service-{service_id}")
    def create_service_callback_api(self, service_id, url, bearer_token, user_id, callback_type):
        data = {"url": url, "bearer_token": bearer_token, "updated_by_id": user_id, "callback_type": callback_type}
        return self.post(f"/service/{service_id}/callback-api", data)

    @cache.delete("service-{service_id}")
    def update_service_callback_api(self, service_id, url, bearer_token, user_id, callback_api_id, callback_type):
        data = {"url": url, "updated_by_id": user_id, "callback_type": callback_type}
        if bearer_token:
            data["bearer_token"] = bearer_token
        return self.post(f"/service/{service_id}/callback-api/{callback_api_id}", data)

    @cache.delete("service-{service_id}")
    def delete_service_callback_api(self, service_id, callback_api_id, callback_type):
        return self.delete(f"/service/{service_id}/callback-api/{callback_api_id}?callback_type={callback_type}")

    def get_service_callback_api(self, service_id, callback_api_id, callback_type):
        return self.get(f"/service/{service_id}/callback-api/{callback_api_id}?callback_type={callback_type}")["data"]

    @cache.set("service-{service_id}-data-retention")
    def get_service_data_retention(self, service_id):
        return self.get(f"/service/{service_id}/data-retention")

    @cache.delete("service-{service_id}-data-retention")
    def set_service_data_retention(self, service_id, days_of_retention):
        current_retention = self.get_service_data_retention(service_id)

        for notification_type in ["email", "sms", "letter"]:
            retention = next(
                filter(lambda retention: retention["notification_type"] == notification_type, current_retention), None
            )
            if retention:
                self.update_service_data_retention(service_id, retention["id"], days_of_retention=days_of_retention)
            else:
                self.create_service_data_retention(
                    service_id, notification_type=notification_type, days_of_retention=days_of_retention
                )

    @cache.set("service-{service_id}-returned-letters-statistics")
    def get_returned_letter_statistics(self, service_id):
        return self.get(f"service/{service_id}/returned-letter-statistics")

    @cache.set("service-{service_id}-returned-letters-summary")
    def get_returned_letter_summary(self, service_id):
        return self.get(f"service/{service_id}/returned-letter-summary")

    def get_returned_letters(self, service_id, reported_at):
        return self.get(f"service/{service_id}/returned-letters?reported_at={reported_at}")

    def get_notification_count(self, service_id, notification_type):
        # if cache is not set return 0
        count = redis_client.get(daily_limit_cache_key(service_id, notification_type=notification_type)) or 0
        return int(count)

    @cache.set("service-{service_id}-unsubscribe-request-reports-summary")
    def get_unsubscribe_reports_summary(self, service_id):
        return self.get(f"service/{service_id}/unsubscribe-request-reports-summary")

    @cache.delete("service-{service_id}-unsubscribe-request-reports-summary")
    @cache.delete("service-{service_id}-unsubscribe-request-statistics")
    def process_unsubscribe_request_report(self, service_id, batch_id, data):
        return self.post(f"service/{service_id}/process-unsubscribe-request-report/{batch_id}", data=data)

    @cache.set("service-{service_id}-unsubscribe-request-statistics")
    def get_unsubscribe_request_statistics(self, service_id):
        return self.get(f"service/{service_id}/unsubscribe-request-statistics")

    @cache.delete("service-{service_id}-unsubscribe-request-reports-summary")
    def create_unsubscribe_request_report(self, service_id, data):
        return self.post(f"service/{service_id}/create-unsubscribe-request-report", data)

    def get_unsubscribe_request_report(self, service_id, batch_id):
        return self.get(f"service/{service_id}/unsubscribe-request-report/{batch_id}")

    @classmethod
    def parse_edit_service_http_error(cls, http_error):
        """Inspect the HTTPError from a create_service/update_service call and return a human-friendly error message"""
        if http_error.message.get("normalised_service_name"):
            return "Service name cannot include characters from a non-Latin alphabet"

        elif http_error.message.get("name"):
            return "This service name is already in use - enter a unique name"

        return None

    @classmethod
    def parse_custom_email_sender_name_http_error(cls, http_error):
        """Inspect the HTTPError from a update_service call and return a human-friendly error message"""
        if http_error.message.get("email_sender_local_part"):
            return "Sender name cannot include characters from a non-Latin alphabet"

        return None

    def create_service_join_request(self, user_to_invite_id, *, service_id, service_managers_ids, reason):
        data = {
            "requester_id": user_to_invite_id,
            "contacted_user_ids": service_managers_ids,
            "invite_link_host": self.admin_url,
            "reason": reason,
        }
        return self.post(f"/service/{service_id}/service-join-request", data=data)

    @cache.set("service-join-request-{request_id}")
    def get_service_join_request(self, request_id, service_id):
        return self.get(f"/service/{service_id}/service-join-request/{request_id}")

    @cache.delete("service-join-request-{request_id}")
    @cache.delete("user-{requester_id}")
    @cache.delete("service-{service_id}-template-folders")
    def update_service_join_requests(self, request_id, requester_id, service_id, **kwargs):
        data = dict(**kwargs)
        return self.post(f"/service/{service_id}/service-join-request/{request_id}", data)


_service_api_client_context_var: ContextVar[ServiceAPIClient] = ContextVar("service_api_client")
get_service_api_client: LazyLocalGetter[ServiceAPIClient] = LazyLocalGetter(
    _service_api_client_context_var,
    lambda: ServiceAPIClient(current_app),
)
memo_resetters.append(lambda: get_service_api_client.clear())
service_api_client = LocalProxy(get_service_api_client)
