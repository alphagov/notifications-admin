from datetime import datetime
from typing import Any

from flask import abort

from app.models import JSONModel, ModelList
from app.notify_client.api_key_api_client import api_key_api_client


class APIKey(JSONModel):
    created_at: datetime
    created_by: Any
    expiry_date: datetime
    id: Any
    key_type: str
    name: str

    __sort_attribute__ = "name"

    # must match key types in notifications-api/app/models.py
    TYPE_NORMAL = "normal"
    TYPE_TEAM = "team"
    TYPE_TEST = "test"

    @classmethod
    def create(cls, service_id, name, key_type):
        return api_key_api_client.create_api_key(service_id=service_id, key_name=name, key_type=key_type)

    def revoke(self, *, service_id):
        api_key_api_client.revoke_api_key(service_id=service_id, key_id=self.id)


class APIKeys(ModelList):
    model = APIKey

    @staticmethod
    def _get_items(*args, **kwargs):
        return api_key_api_client.get_api_keys(*args, **kwargs)["apiKeys"]

    def get(self, id):
        for api_key in self:
            if api_key.id == id:
                return api_key
        abort(404)
