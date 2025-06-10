import base64
import json
import uuid

from typing import Any

from notifications_utils.insensitive_dict import InsensitiveDict
from notifications_utils.insensitive_dict import InsensitiveSet as UtilsInsensitiveSet

from app.extensions import redis_client
from app.models import JSONModel


# Implements https://github.com/alphagov/notifications-utils/pull/1197/files
class InsensitiveSet(UtilsInsensitiveSet):
    def __contains__(self, key):
        return key in InsensitiveDict.from_keys(self)


class TemplateAttachment(JSONModel):
    BASE_URL = "https://documents.service.gov.uk"

    file_name: str
    weeks_of_retention: int
    email_confirmation: bool
    link_text: str
    id: Any

    __sort_attribute__ = "file_name"

    def __init__(self, *args, parent, **kwargs):
        super().__init__(*args, **kwargs)
        self._parent = parent

    def __repr__(self):
        return f"{self.__class__.__name__}(<{self._dict}>)"

    def __setattr__(self, name, value):
        if name not in self.__annotations__.keys() or not hasattr(self, name):
            return super().__setattr__(name, value)
        self._dict[name] = value
        self._parent[self.id] = self._dict

    def __bool__(self):
        return bool(self.file_name)

    @property
    def url(self):
        if not self.file_name:
            return
        if self.link_text:
            return (
                f"[{self.link_text}]"
                f"("
                f"{self.BASE_URL}"
                "/d/YlxDzgNUQYi1Qg6QxIpptA/WiwkEBFmSy6WYJ0gLemPdg"
                "?key=oe78i7L5xPD-VZVfPAUHyxr5YVBwMB73Hu7sAl-HnXU"
                f")"
            )
        return (
            f"{self.BASE_URL}"
            "/d/YlxDzgNUQYi1Qg6QxIpptA/WiwkEBFmSy6WYJ0gLemPdg"
            "?key=oe78i7L5xPD-VZVfPAUHyxr5YVBwMB73Hu7sAl-HnXU"
        )


class TemplateAttachments(InsensitiveDict):
    def __init__(self, template):
        self._template = template
        super().__init__(json.loads(redis_client.get(self.cache_key) or "{}"))

    @property
    def cache_key(self):
        return f"template-{self._template.id}-attachments"

    def __getitem__(self, id):
        if id not in self:
            self[id] = {
                "file_name": None,
                "weeks_of_retention": 26,
                "email_confirmation": True,
                "link_text": None,
                "id": id
            }
        return TemplateAttachment(
            super().__getitem__(id),
            parent=self,
        )

    def __setitem__(self, id, value):
        super().__setitem__(id, value)
        redis_client.set(self.cache_key, json.dumps(self))

    def __delitem__(self, id):
        super().__delitem__(InsensitiveDict.make_key(id))
        redis_client.set(self.cache_key, json.dumps(self))

    def __bool__(self):
        return self.count > 0

    @property
    def all(self):
        return tuple(self[key] for key in self)

    def create(self):
        return self[str(uuid.uuid4())]

    @property
    def count(self):
        return len(self)

    @property
    def as_personalisation(self):
        return {attachment.file_name: attachment.url for attachment in self.all}

    def prune_orphans(self):
        for attachment in self.all:
            if attachment.file_name not in InsensitiveSet(self._template.all_placeholders):
                del self[attachment.id]
