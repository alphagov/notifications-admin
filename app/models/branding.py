from pathlib import Path

from flask import current_app
from flask_login import current_user

from app import asset_fingerprinter
from app.formatters import email_safe
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

    def name_like(self, name):
        return email_safe(name, whitespace="") == email_safe(self.name, whitespace="")

    def serialize(self):
        return self._dict.copy()


class EmailBranding(Branding):
    ALLOWED_PROPERTIES = Branding.ALLOWED_PROPERTIES | {
        "colour",
        "logo",
        "alt_text",
        "text",
        "brand_type",
    }

    NHS_ID = "a7dc4e56-660b-4db7-8cff-12c37b12b5ea"

    @classmethod
    def from_id(cls, id):
        if id is None:
            return cls.with_default_values(name="GOV.UK", brand_type="govuk")
        return cls(email_branding_client.get_email_branding(id)["email_branding"])

    @classmethod
    def govuk_branding(cls):
        return cls.from_id(None)

    @classmethod
    def create(
        cls,
        *,
        logo,
        alt_text,
        colour,
        brand_type,
    ):
        name = email_branding_client.get_email_branding_name_for_alt_text(alt_text)
        if brand_type == "both":
            name = f"GOV.UK and {name}"

        new_email_branding = email_branding_client.create_email_branding(
            name=name,
            alt_text=alt_text,
            text=None,
            created_by_id=current_user.id,
            logo=logo,
            colour=colour,
            brand_type=brand_type,
        )
        return cls(new_email_branding)

    @property
    def is_nhs(self):
        return self.id == self.NHS_ID

    @property
    def is_govuk(self):
        return self.brand_type == "govuk"

    @property
    def has_govuk_banner(self):
        return self.is_govuk or self.brand_type == "both"

    @property
    def has_brand_banner(self):
        return self.brand_type == "org_banner"

    @property
    def logo_url(self):
        if self.logo:
            return f"https://{current_app.config['LOGO_CDN_DOMAIN']}/{self.logo}"


class LetterBranding(Branding):
    ALLOWED_PROPERTIES = Branding.ALLOWED_PROPERTIES | {"filename"}
    NHS_ID = "2cd354bb-6b85-eda3-c0ad-6b613150459f"

    @classmethod
    def create(
        cls,
        *,
        name,
        filename,
    ):
        # TODO: rename temp to non-temp and clean up temp files
        new_letter_branding = letter_branding_client.create_letter_branding(name=name, filename=filename)
        return cls(new_letter_branding)

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

    def contains_name(self, name):
        return any(branding.name_like(name) for branding in self)


class AllEmailBranding(AllBranding):
    client_method = email_branding_client.get_all_email_branding
    model = EmailBranding

    @property
    def example_government_identity_branding(self):
        for branding in self:
            if branding.name_like("Department for Education"):
                return branding


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


GOVERNMENT_IDENTITY_SYSTEM_COLOURS = {
    "Attorney General’s Office": "#9f1888",
    "Cabinet Office": "#005abb",
    "Civil Service": "#af292e",
    "Department for Business Innovation & Skills": "#003479",
    "Department for Digital, Culture, Media & Sport": "#d40072",
    "Department for Education": "#003a69",
    "Department for Environment Food & Rural Affairs": "#00a33b",
    "Department for International Development": "#002878",
    "Department for International Trade": "#cf102d",
    "Department for Levelling Up, Housing & Communities": "#012169",
    "Department for Transport": "#006c56",
    "Department for Work & Pensions": "#00beb7",
    "Department of Health & Social Care": "#00ad93",
    "Foreign, Commonwealth & Development Office": "#012169",
    "Government Equalities Office": "#9325b2",
    "HM Government": "#0076c0",
    "HM Revenue & Customs": "#009390",
    "HM Treasury": "#af292e",
    "Home Office": "#9325b2",
    "Ministry of Defence": "#4d2942",
    "Ministry of Justice": "#231f20",
    "Northern Ireland Office": "#002663",
    "Office of the Advocate General for Scotland": "#002663",
    "Office of the Leader of the House of Commons": "#317023",
    "Office of the Leader of the House of Lords": "#9c132e",
    "Scotland Office": "#002663",
    "UK Export Finance": "#005747",
    "Wales Office": "#a33038",
}

INSIGNIA_ASSETS_PATH = Path(asset_fingerprinter._filesystem_path) / "images/branding/insignia/"

GOVERNMENT_IDENTITY_SYSTEM_CRESTS_OR_INSIGNIA = tuple(
    item.stem for item in INSIGNIA_ASSETS_PATH.resolve().iterdir() if item.is_file()
)
