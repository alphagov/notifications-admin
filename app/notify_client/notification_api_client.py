from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, _attach_current_user, api_client_request_session


class NotificationApiClient(NotifyAdminAPIClient):
    def get_notifications_for_service(
        self,
        service_id,
        job_id=None,
        template_type=None,
        status=None,
        page=None,
        page_size=None,
        count_pages=None,
        limit_days=None,
        include_jobs=None,
        include_from_test_key=None,
        to=None,
        include_one_off=None,
    ):
        params = {
            "page": page,
            "page_size": page_size,
            "template_type": template_type,
            "status": status,
            "include_jobs": include_jobs,
            "include_from_test_key": include_from_test_key,
            "to": to,
            "include_one_off": include_one_off,
            "count_pages": count_pages,
        }

        params = {k: v for k, v in params.items() if v is not None}

        # if `to` is set it is likely PII like an email address or mobile which
        # we do not want in our logs, so we do a POST request instead of a GET
        method = self.post if to else self.get
        kwargs = {"data": params} if to else {"params": params}

        if job_id:
            return method(url=f"/service/{service_id}/job/{job_id}/notifications", **kwargs)
        else:
            if limit_days is not None:
                params["limit_days"] = limit_days
            return method(url=f"/service/{service_id}/notifications", **kwargs)

    def get_notifications_for_service_for_csv(
        self,
        service_id,
        job_id=None,
        template_type=None,
        status=None,
        older_than=None,
        page=None,
        page_size=None,
        limit_days=None,
    ):
        params = {
            "older_than": older_than,
            "page": page,
            "page_size": page_size,
            "template_type": template_type,
            "status": status,
        }

        params = {k: v for k, v in params.items() if v is not None}
        kwargs = {"params": params}

        if job_id:
            params["format_for_csv"] = True
            return self.get(url=f"/service/{service_id}/job/{job_id}/notifications", **kwargs)
        else:
            if limit_days is not None:
                params["limit_days"] = limit_days
            return self.get(url=f"/service/{service_id}/notifications/csv", **kwargs)

    def send_notification(self, service_id, *, template_id, recipient, personalisation, sender_id):
        data = {
            "template_id": template_id,
            "to": recipient,
            "personalisation": personalisation,
        }
        if sender_id:
            data["sender_id"] = sender_id
        data = _attach_current_user(data)
        return self.post(url=f"/service/{service_id}/send-notification", data=data)

    def send_precompiled_letter(self, service_id, filename, file_id, postage, recipient_address):
        data = {"filename": filename, "file_id": file_id, "postage": postage, "recipient_address": recipient_address}
        data = _attach_current_user(data)
        return self.post(url=f"/service/{service_id}/send-pdf-letter", data=data)

    def get_notification(self, service_id, notification_id):
        return self.get(url=f"/service/{service_id}/notifications/{notification_id}")

    def get_notification_letter_preview(self, service_id, notification_id, file_type, page=None):
        get_url = "/service/{}/template/preview/{}/{}{}".format(
            service_id, notification_id, file_type, f"?page={page}" if page else ""
        )

        return self.get(url=get_url)

    def update_notification_to_cancelled(self, service_id, notification_id):
        return self.post(url=f"/service/{service_id}/notifications/{notification_id}/cancel", data={})

    def get_notification_status_by_service(self, start_date, end_date):
        return self.get(
            url="service/monthly-data-by-service",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )

    def get_notification_count_for_job_id(self, *, service_id, job_id):
        return self.get(url=f"/service/{service_id}/job/{job_id}/notification_count")["count"]

    def get_notifications_count_for_service(self, service_id, template_type, limit_days):
        params = {
            "template_type": template_type,
            "limit_days": limit_days,
        }

        response = self.get(url=f"/service/{service_id}/notifications/count", params=params)

        return response.get("notifications_sent_count")


_notification_api_client_context_var: ContextVar[NotificationApiClient] = ContextVar("notification_api_client")
get_notification_api_client: LazyLocalGetter[NotificationApiClient] = LazyLocalGetter(
    _notification_api_client_context_var,
    lambda: NotificationApiClient(current_app, request_session=api_client_request_session),
)
memo_resetters.append(lambda: get_notification_api_client.clear())
notification_api_client = LocalProxy(get_notification_api_client)
