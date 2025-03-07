import base64
import json

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

    @property
    def url(self, custom=False):
        if not self.file_name:
            return
        if custom:
            return f"{self.BASE_URL}/f/{base64.b64encode(self.file_name.encode()).decode()}"
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

    def __getitem__(self, placeholder_name):
        if placeholder_name not in self:
            self[placeholder_name] = {
                "file_name": None,
                "weeks_of_retention": 26,
                "email_confirmation": True,
            }
        return TemplateAttachment(
            super().__getitem__(placeholder_name),
            parent=self,
            placeholder_name=placeholder_name,
        )

    def __setitem__(self, placeholder_name, value):
        super().__setitem__(placeholder_name, value)
        redis_client.set(self.cache_key, json.dumps(self))

    def __delitem__(self, placeholder_name):
        super().__delitem__(InsensitiveDict.make_key(placeholder_name))
        redis_client.set(self.cache_key, json.dumps(self))

    def __bool__(self):
        return self.count > 0

    def __contains__(self, key):
        if not super().__contains__(key):
            return False
        return bool(TemplateAttachment(super().__getitem__(key), parent=self, placeholder_name=key))

    @property
    def count(self):
        return sum(bool(self[key]) for key in self if key in InsensitiveSet(self._template.all_placeholders))

    @property
    def as_personalisation(self):
        return {placeholder: self[placeholder].url for placeholder in self if self[placeholder]}

    def prune_orphans(self):
        for placeholder in self.keys():
            if placeholder not in InsensitiveSet(self._template.all_placeholders):
                del self[placeholder]
