from pathlib import Path

from app.models import JSONModel, ModelList
from app.notify_client.email_branding_client import email_branding_client
from app.notify_client.letter_branding_client import letter_branding_client
from app.notify_client.organisations_api_client import organisations_client


class Branding(JSONModel):
    ALLOWED_PROPERTIES = {"id", "name"}
    __sort_attribute__ = "name"

    def __bool__(self):
        return bool(self.id)

    @classmethod
    def with_default_values(cls, **kwargs):
        return cls({key: None for key in cls.ALLOWED_PROPERTIES} | kwargs)


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
            return cls.with_default_values(name="GOV.UK")
        return cls(email_branding_client.get_email_branding(id)["email_branding"])

    @property
    def is_nhs(self):
        return self.id == self.NHS_ID

    @property
    def is_govuk(self):
        return self.id is None

    def serialize(self):
        return self._dict.copy()


class LetterBranding(Branding):
    ALLOWED_PROPERTIES = Branding.ALLOWED_PROPERTIES | {"filename"}

    @classmethod
    def from_id(cls, id):
        if id is None:
            return cls.with_default_values()
        return cls(letter_branding_client.get_letter_branding(id))

    @property
    def is_nhs(self):
        return self.name == "NHS"


class AllBranding(ModelList):
    class NotFound(Exception):
        pass

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
        raise self.NotFound

    def excluding(self, *ids_to_exclude):
        return tuple(branding for branding in self if branding.id not in ids_to_exclude)


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


class LetterBrandingPool(AllLetterBranding):
    client_method = organisations_client.get_letter_branding_pool

    def __init__(self, id):
        self.items = tuple()
        if id:
            self.items = self.client_method(id)


GOVERNMENT_IDENTITY_SYSTEM_COLOURS = [
    {
        "colour": "#9f1888",
        "name": "Attorney General’s Office",
    },
    {
        "colour": "#005abb",
        "name": "Cabinet Office",
    },
    {
        "colour": "#af292e",
        "name": "Civil Service",
    },
    {
        "colour": "#003479",
        "name": "Department for Business Innovation & Skills",
    },
    {
        "colour": "#d40072",
        "name": "Department for Digital, Culture, Media & Sport",
    },
    {
        "colour": "#003a69",
        "name": "Department for Education",
    },
    {
        "colour": "#00a33b",
        "name": "Department for Environment Food & Rural Affairs",
    },
    {
        "colour": "#002878",
        "name": "Department for International Development",
    },
    {
        "colour": "#cf102d",
        "name": "Department for International Trade",
    },
    {
        "colour": "#012169",
        "name": "Department for Levelling Up, Housing & Communities",
    },
    {
        "colour": "#006c56",
        "name": "Department for Transport",
    },
    {
        "colour": "#00beb7",
        "name": "Department for Work & Pensions",
    },
    {
        "colour": "#00ad93",
        "name": "Department of Health & Social Care",
    },
    {
        "colour": "#012169",
        "name": "Foreign, Commonwealth & Development Office",
    },
    {
        "colour": "#9325b2",
        "name": "Government Equalities Office",
    },
    {
        "colour": "#0076c0",
        "name": "HM Government",
    },
    {
        "colour": "#009390",
        "name": "HM Revenue & Customs",
    },
    {
        "colour": "#af292e",
        "name": "HM Treasury",
    },
    {
        "colour": "#9325b2",
        "name": "Home Office",
    },
    {
        "colour": "#4d2942",
        "name": "Ministry of Defence",
    },
    {
        "colour": "#231f20",
        "name": "Ministry of Justice",
    },
    {
        "colour": "#002663",
        "name": "Northern Ireland Office",
    },
    {
        "colour": "#002663",
        "name": "Office of the Advocate General for Scotland",
    },
    {
        "colour": "#317023",
        "name": "Office of the Leader of the House of Commons",
    },
    {
        "colour": "#9c132e",
        "name": "Office of the Leader of the House of Lords",
    },
    {
        "colour": "#002663",
        "name": "Scotland Office",
    },
    {
        "colour": "#005747",
        "name": "UK Export Finance",
    },
    {
        "colour": "#a33038",
        "name": "Wales Office",
    },
]

INSIGNIA_ASSETS_PATH = Path(__file__) / "../../assets/images/branding/insignia/"

GOVERNMENT_IDENTITY_SYSTEM_CRESTS_OR_INSIGNIA = tuple(
    item.stem for item in INSIGNIA_ASSETS_PATH.resolve().iterdir() if item.is_file()
)
