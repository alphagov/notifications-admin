import base64
import json

from notifications_utils.insensitive_dict import InsensitiveDict, InsensitiveSet

from app.extensions import redis_client
from app.models import JSONModel


class TemplateAttachment(JSONModel):
    file_name: str
    weeks_of_retention: int
    email_confirmation: bool

    __sort_attribute__ = "file_name"

    def __init__(self, *args, parent, placeholder_name, **kwargs):
        super().__init__(*args, **kwargs)
        self._parent = parent
        self._placeholder_name = placeholder_name

    def __repr__(self):
        return f"{self.__class__.__name__}(<{self._dict}>)"

    def __setattr__(self, name, value):
        if name not in self.__annotations__.keys() or not hasattr(self, name):
            return super().__setattr__(name, value)
        self._dict[name] = value
        self._parent[self._placeholder_name] = self._dict

    def __bool__(self):
        return bool(self.file_name)


class TemplateAttachments:
    BASE_URL = "https://www.download.example.gov.uk/f/"

    def __init__(self, template):
        self._template = template
        self._dict = InsensitiveDict(json.loads(redis_client.get(self.cache_key) or "{}"))

    @property
    def cache_key(self):
        return f"template-{self._template.id}-attachments"

    def __getitem__(self, placeholder_name):
        if placeholder_name not in self._dict:
            self._dict[placeholder_name] = {
                "file_name": None,
                "weeks_of_retention": 26,
                "email_confirmation": True,
            }
        return TemplateAttachment(self._dict[placeholder_name], parent=self, placeholder_name=placeholder_name)

    def __setitem__(self, placeholder_name, value):
        self._dict[InsensitiveDict.make_key(placeholder_name)] = value
        redis_client.set(self.cache_key, json.dumps(self._dict))

    def __delitem__(self, placeholder_name):
        self._dict.pop(InsensitiveDict.make_key(placeholder_name))
        redis_client.set(self.cache_key, json.dumps(self._dict))

    @property
    def count(self):
        return sum(
            bool(self[key]) for key in self._dict if key in InsensitiveDict.from_keys(self._template.all_placeholders)
        )

    @property
    def as_personalisation(self):
        return {
            placeholder: f"{self.BASE_URL}{base64.b64encode(attachment['file_name'].encode()).decode()}"
            if attachment["file_name"]
            else None
            for placeholder, attachment in self._dict.items()
        }
