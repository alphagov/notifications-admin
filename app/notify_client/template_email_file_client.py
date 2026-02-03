from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient


class TemplateEmailFileClient(NotifyAdminAPIClient):
    def create_file(
        self,
        *,
        file_id,
        service_id,
        template_id,
        filename,
        created_by_id,
        retention_period=90,
        validate_users_email=None,
    ):
        data = {
            "id": str(file_id),
            "filename": filename,
            "created_by_id": created_by_id,
            "retention_period": retention_period,
            "validate_users_email": bool(validate_users_email),
        }
        return self.post(f"/service/{service_id}/templates/{template_id}/template_email_files", data=data)

    def update_file(
        self,
        template_email_file_id,
        service_id,
        template_id,
        data,
    ):
        return self.post(
            f"/service/{service_id}/templates/{template_id}/template_email_files/{template_email_file_id}", data=data
        )


_template_email_file_api_client_context_var: ContextVar[TemplateEmailFileClient] = ContextVar(
    "template_email_file_api_client_context_var"
)
get_template_email_file_client: LazyLocalGetter[TemplateEmailFileClient] = LazyLocalGetter(
    _template_email_file_api_client_context_var,
    lambda: TemplateEmailFileClient(current_app),
)
memo_resetters.append(lambda: get_template_email_file_client.clear())
template_email_file_client = LocalProxy(get_template_email_file_client)
