from contextvars import ContextVar

from flask import current_app
from flask_login import current_user
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, api_client_request_session, cache


class LetterAttachmentClient(NotifyAdminAPIClient):
    def get_letter_attachment(self, letter_attachment_id):
        return self.get(url=f"/letter-attachment/{letter_attachment_id}")

    @cache.delete("service-{service_id}-templates")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def create_letter_attachment(self, *, upload_id, original_filename, page_count, template_id, service_id):
        data = {
            "upload_id": str(upload_id),
            "original_filename": original_filename,
            "page_count": page_count,
            "template_id": str(template_id),
            "created_by_id": str(current_user.id),
        }
        return self.post(url="/letter-attachment", data=data)

    @cache.delete("service-{service_id}-templates")
    @cache.delete_by_pattern("service-{service_id}-template-*")
    def archive_letter_attachment(self, *, letter_attachment_id, user_id, service_id):
        data = {
            "archived_by": str(user_id),
        }
        return self.post(url=f"/letter-attachment/{letter_attachment_id}/archive", data=data)


_letter_attachment_client_context_var: ContextVar[LetterAttachmentClient] = ContextVar("letter_attachment_client")
get_letter_attachment_client: LazyLocalGetter[LetterAttachmentClient] = LazyLocalGetter(
    _letter_attachment_client_context_var,
    lambda: LetterAttachmentClient(current_app, request_session=api_client_request_session),
)
memo_resetters.append(lambda: get_letter_attachment_client.clear())
letter_attachment_client = LocalProxy(get_letter_attachment_client)
