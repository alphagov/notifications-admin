from app.extensions import redis_client
from app.models import JSONModel


class TemplateAttachment(JSONModel):
    file_name: str
    weeks_of_retention: int
    email_confirmation: bool

    __sort_attribute__ = "file_name"


class TemplateAttachments():
    def __init__(self, template_id):
        self._dict = redis_client.get(f"template-{id}-attachments") or {}

    def __getitem__(self, placeholder_name):
        try:
            return TemplateAttachment(self._dict[placeholder_name])
        except KeyError:
            return TemplateAttachment({
                "file_name": None,
                "weeks_of_retention": 26,
                "email_confirmation": True,
            })
