from datetime import datetime
from pathlib import Path
from typing import Any

from flask import current_app
from flask_login import current_user
from notifications_utils.safe_string import make_string_safe

from app import asset_fingerprinter
from app.models import JSONModel, ModelList
from app.notify_client.email_branding_client import email_branding_client
from app.notify_client.letter_branding_client import letter_branding_client
from app.notify_client.organisations_api_client import organisations_client
from app.notify_client.user_api_client import user_api_client


class Branding(JSONModel):
    id: Any
    name: str
    created_by: Any
    created_at: datetime
    updated_at: datetime

    __sort_attribute__ = "name"

    def __bool__(self):
        return bool(self.id)

    @classmethod
    def with_default_values(cls, **kwargs):
        return cls(dict.fromkeys(cls.__annotations__) | kwargs)

    def name_like(self, name):
        return make_string_safe(name, whitespace="") == make_string_safe(self.name, whitespace="")

    def serialize(self):
        return self._dict.copy()


class EmailBranding(Branding):
    colour: str
    logo: str
    alt_text: str
    text: str
    brand_type: str

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

    @property
    def is_used_by_orgs_or_services(self):
        orgs_and_services = email_branding_client.get_orgs_and_services_associated_with_branding(self.id)["data"]

        return len(orgs_and_services["services"]) > 0 or len(orgs_and_services["organisations"]) > 0

    @property
    def organisations(self):
        orgs_and_services = email_branding_client.get_orgs_and_services_associated_with_branding(self.id)["data"]

        return orgs_and_services["organisations"]

    @property
    def services(self):
        orgs_and_services = email_branding_client.get_orgs_and_services_associated_with_branding(self.id)["data"]

        return orgs_and_services["services"]

    @property
    def created_by_user(self):
        if self.created_by:
            return user_api_client.get_user(self.created_by)
        return None


class LetterBranding(Branding):
    filename: str

    NHS_ID = "2cd354bb-6b85-eda3-c0ad-6b613150459f"

    @classmethod
    def create(
        cls,
        *,
        name,
        filename,
    ):
        new_letter_branding = letter_branding_client.create_letter_branding(
            name=name,
            filename=filename,
            created_by_id=current_user.id,
        )
        return cls(new_letter_branding)

    @classmethod
    def from_id(cls, id):
        if id is None:
            return cls.with_default_values()
        return cls(letter_branding_client.get_letter_branding(id))

    @property
    def is_nhs(self):
        return self.name == "NHS"

    @property
    def organisations(self):
        orgs_and_services = letter_branding_client.get_orgs_and_services_associated_with_branding(self.id)["data"]

        return orgs_and_services["organisations"]

    @property
    def services(self):
        orgs_and_services = letter_branding_client.get_orgs_and_services_associated_with_branding(self.id)["data"]

        return orgs_and_services["services"]

    @property
    def created_by_user(self):
        if self.created_by:
            return user_api_client.get_user(self.created_by)
        return None


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
    model = EmailBranding

    @staticmethod
    def _get_items(*args, **kwargs):
        return email_branding_client.get_all_email_branding(*args, **kwargs)

    @property
    def example_government_identity_branding(self):
        for branding in self:
            if branding.name_like("Department for Education"):
                return branding


class EmailBrandingPool(AllEmailBranding):
    @staticmethod
    def _get_items(*args, **kwargs):
        return organisations_client.get_email_branding_pool(*args, **kwargs)

    def __init__(self, id):
        self.items = ()
        if id:
            self.items = self._get_items(id)


class AllLetterBranding(AllBranding):
    model = LetterBranding

    @staticmethod
    def _get_items(*args, **kwargs):
        return letter_branding_client.get_all_letter_branding(*args, **kwargs)


class LetterBrandingPool(AllLetterBranding):
    @staticmethod
    def _get_items(*args, **kwargs):
        return organisations_client.get_letter_branding_pool(*args, **kwargs)

    def __init__(self, id):
        self.items = ()
        if id:
            self.items = self._get_items(id)


GOVERNMENT_IDENTITY_SYSTEM_COLOURS = {
    "Attorney General’s Office": "#9f1888",
    "Cabinet Office": "#005abb",
    "Civil Service": "#af292e",
    "Department for Business & Trade": "#cf102d",
    "Department for Business Innovation & Skills": "#003479",
    "Department for Digital, Culture, Media & Sport": "#d40072",
    "Department for Education": "#003a69",
    "Department for Environment Food & Rural Affairs": "#00a33b",
    "Department for International Development": "#002878",
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


def get_insignia_asset_path():
    return Path(asset_fingerprinter._filesystem_path) / "images/branding/insignia/"


def get_government_identity_system_crests_or_insignia():
    return tuple(item.stem for item in get_insignia_asset_path().resolve().iterdir() if item.is_file())
