from app.models import JSONModel, ModelList
from app.notify_client.email_branding_client import email_branding_client
from app.notify_client.letter_branding_client import letter_branding_client
from app.notify_client.organisations_api_client import organisations_client


class Branding(JSONModel):
    ALLOWED_PROPERTIES = {"id", "name"}
    __sort_attribute__ = "name"

    def __bool__(self):
        return bool(self.id)


class EmailBranding(Branding):
    ALLOWED_PROPERTIES = Branding.ALLOWED_PROPERTIES | {
        "colour",
        "logo",
        "text",
        "brand_type",
    }

    NHS_ID = "a7dc4e56-660b-4db7-8cff-12c37b12b5ea"

    @classmethod
    def from_id(cls, id):
        if id is None:
            return cls({key: None for key in cls.ALLOWED_PROPERTIES} | {"name": "GOV.UK"})
        return cls(email_branding_client.get_email_branding(id)["email_branding"])

    @property
    def is_nhs(self):
        return self.id == self.NHS_ID

    @property
    def is_govuk(self):
        return self.id is None


class LetterBranding(Branding):
    ALLOWED_PROPERTIES = Branding.ALLOWED_PROPERTIES | {"filename"}

    @classmethod
    def from_id(cls, id):
        if id is None:
            return cls({key: None for key in cls.ALLOWED_PROPERTIES})
        return cls(letter_branding_client.get_letter_branding(id))

    @property
    def is_nhs(self):
        return self.name == "NHS"


class AllBranding(ModelList):
    @property
    def ids(self):
        return tuple(branding.id for branding in self)

    @property
    def as_id_and_name(self):
        return [(branding.id, branding.name) for branding in self]

    def get_item_by_id(self, id):
        for branding in self:
            if branding.id == id:
                return branding
        raise StopIteration


class AllEmailBranding(AllBranding):
    client_method = email_branding_client.get_all_email_branding
    model = EmailBranding


class EmailBrandingPool(AllEmailBranding):
    client_method = organisations_client.get_email_branding_pool

    def __init__(self, id):
        self.items = tuple()
        if id:
            self.items = self.client_method(id)


class AllLetterBranding(AllBranding):
    client_method = letter_branding_client.get_all_letter_branding
    model = LetterBranding
