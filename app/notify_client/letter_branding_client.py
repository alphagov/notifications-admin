from contextvars import ContextVar

from flask import current_app
from notifications_utils.local_vars import LazyLocalGetter
from werkzeug.local import LocalProxy

from app import memo_resetters
from app.notify_client import NotifyAdminAPIClient, cache


class LetterBrandingClient(NotifyAdminAPIClient):
    @cache.set("letter_branding-{branding_id}")
    def get_letter_branding(self, branding_id):
        return self.get(url=f"/letter-branding/{branding_id}")

    @cache.set("letter_branding")
    def get_all_letter_branding(self):
        return self.get(url="/letter-branding")

    def get_unique_name_for_letter_branding(self, name):
        return self.post(url="/letter-branding/get-unique-name", data={"name": name})["name"]

    @cache.delete("letter_branding")
    def create_letter_branding(self, *, filename, name, created_by_id):
        data = {
            "filename": filename,
            "name": name,
            "created_by_id": created_by_id,
        }
        return self.post(url="/letter-branding", data=data)

    @cache.delete("letter_branding")
    @cache.delete("letter_branding-{branding_id}")
    @cache.delete_by_pattern("organisation-*-letter-branding-pool")
    def update_letter_branding(self, *, branding_id, filename, name, updated_by_id):
        data = {
            "filename": filename,
            "name": name,
            "updated_by_id": updated_by_id,
        }
        return self.post(url=f"/letter-branding/{branding_id}", data=data)

    def get_orgs_and_services_associated_with_branding(self, branding_id):
        return self.get(url=f"/letter-branding/{branding_id}/orgs_and_services")


_letter_branding_client_context_var: ContextVar[LetterBrandingClient] = ContextVar("letter_branding_client")
get_letter_branding_client: LazyLocalGetter[LetterBrandingClient] = LazyLocalGetter(
    _letter_branding_client_context_var,
    lambda: LetterBrandingClient(current_app),
)
memo_resetters.append(lambda: get_letter_branding_client.clear())
letter_branding_client = LocalProxy(get_letter_branding_client)
