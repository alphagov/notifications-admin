from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, _attach_current_user, api_client_request_session


class ContactListApiClient(NotifyAdminAPIClient):
    def create_contact_list(
        self,
        *,
        service_id,
        upload_id,
        original_file_name,
        row_count,
        template_type,
    ):
        data = {
            "id": upload_id,
            "original_file_name": original_file_name,
            "row_count": row_count,
            "template_type": template_type,
        }

        data = _attach_current_user(data)
        job = self.post(url=f"/service/{service_id}/contact-list", data=data)

        return job

    def get_contact_lists(self, service_id):
        return self.get(f"/service/{service_id}/contact-list")

    def get_contact_list(self, *, service_id, contact_list_id):
        return self.get(f"/service/{service_id}/contact-list/{contact_list_id}")

    def delete_contact_list(self, *, service_id, contact_list_id):
        return self.delete(f"/service/{service_id}/contact-list/{contact_list_id}")


_contact_list_api_client_context_var: ContextVar[ContactListApiClient] = ContextVar("contact_list_api_client")
get_contact_list_api_client: LazyLocalGetter[ContactListApiClient] = LazyLocalGetter(
    _contact_list_api_client_context_var,
    lambda: ContactListApiClient(current_app, request_session=api_client_request_session),
)
memo_resetters.append(lambda: get_contact_list_api_client.clear())
contact_list_api_client = LocalProxy(get_contact_list_api_client)
