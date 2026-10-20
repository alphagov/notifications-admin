import json
from datetime import datetime

from app.models import JSONModel, UUIDStr


class Token(JSONModel):
    user_id: UUIDStr
    email: str
    created_at: datetime
    secret_code: str

    __sort_attribute__ = "created_at"

    def __init__(self, json_data):
        return super().__init__(json.loads(json_data))
