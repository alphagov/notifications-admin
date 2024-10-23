from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient


class UploadApiClient(NotifyAdminAPIClient):
    def get_letters_by_service_and_print_day(
        self,
        service_id,
        *,
        letter_print_day,
        page=1,
    ):
        return self.get(url=f"/service/{service_id}/upload/uploaded-letters/{letter_print_day}?page={page}")


_upload_api_client_context_var: ContextVar[UploadApiClient] = ContextVar("upload_api_client")
get_upload_api_client: LazyLocalGetter[UploadApiClient] = LazyLocalGetter(
    _upload_api_client_context_var,
    lambda: UploadApiClient(current_app),
)
memo_resetters.append(lambda: get_upload_api_client.clear())
upload_api_client = LocalProxy(get_upload_api_client)
