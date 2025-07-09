from datetime import date, datetime
from typing import Any

from flask import abort
from werkzeug.utils import cached_property

from app.constants import PERMISSION_CAN_MAKE_SERVICES_LIVE
from app.models import JSONModel, ModelList, SerialisedModelCollection
from app.models.branding import (
    EmailBranding,
    EmailBrandingPool,
    LetterBranding,
    LetterBrandingPool,
)
from app.notify_client.organisations_api_client import organisations_client


class Organisation(JSONModel):
    TYPE_CENTRAL = "central"
    TYPE_LOCAL = "local"
    TYPE_NHS_CENTRAL = "nhs_central"
    TYPE_NHS_LOCAL = "nhs_local"
    TYPE_NHS_GP = "nhs_gp"
    TYPE_EMERGENCY_SERVICE = "emergency_service"
    TYPE_SCHOOL_OR_COLLEGE = "school_or_college"
    TYPE_OTHER = "other"

    NHS_TYPES = (
        TYPE_NHS_CENTRAL,
        TYPE_NHS_LOCAL,
        TYPE_NHS_GP,
    )

    TYPE_LABELS = {
        TYPE_CENTRAL: "Central government",
        TYPE_LOCAL: "Local government",
        TYPE_NHS_CENTRAL: "NHS – central government agency or public body",
        TYPE_NHS_LOCAL: "NHS Trust or Integrated Care Board",
        TYPE_NHS_GP: "GP surgery",
        TYPE_EMERGENCY_SERVICE: "Emergency service",
        TYPE_SCHOOL_OR_COLLEGE: "School or college",
        TYPE_OTHER: "Other",
    }

    id: Any
    name: str
    active: bool
    crown: bool
    organisation_type: Any
    letter_branding_id: Any
    email_branding_id: Any
    agreement_signed: bool
    agreement_signed_at: datetime
    agreement_signed_by_id: Any
    agreement_signed_version: str
    agreement_signed_on_behalf_of_name: str
    agreement_signed_on_behalf_of_email_address: str
    domains: list
    request_to_go_live_notes: str
    count_of_live_services: int
    billing_contact_email_addresses: str
    billing_contact_names: str
    billing_reference: str
    purchase_order_number: str
    notes: str
    can_approve_own_go_live_requests: bool
    permissions: list

    __sort_attribute__ = "name"

    @classmethod
    def from_id(cls, org_id):
        if not org_id:
            return cls({})
        return cls(organisations_client.get_organisation(org_id))

    @classmethod
    def from_domain(cls, domain):
        return cls(organisations_client.get_organisation_by_domain(domain))

    @classmethod
    def from_service(cls, service_id):
        return cls(organisations_client.get_service_organisation(service_id))

    @classmethod
    def create_from_form(cls, form):
        return cls.create(
            name=form.name.data,
            crown={
                "crown": True,
                "non-crown": False,
                "unknown": None,
            }.get(form.crown_status.data),
            organisation_type=form.organisation_type.data,
        )

    @classmethod
    def create(cls, name, crown, organisation_type, agreement_signed=False):
        return cls(
            organisations_client.create_organisation(
                name=name,
                crown=crown,
                organisation_type=organisation_type,
                agreement_signed=agreement_signed,
            )
        )

    def __init__(self, _dict):
        super().__init__(_dict)

        if self._dict == {}:
            self.id = None
            self.name = None
            self.crown = None
            self.agreement_signed = None
            self.agreement_signed_by_id = None
            self.domains = []
            self.organisation_type = None
            self.request_to_go_live_notes = None
            self.email_branding_id = None
            self.letter_branding_id = None
            self.can_approve_own_go_live_requests = False
            self.permissions = []

    @property
    def organisation_type_label(self):
        return self.TYPE_LABELS.get(self.organisation_type)

    @property
    def crown_status_or_404(self):
        if self.crown is None:
            abort(404)
        return self.crown

    @property
    def billing_details(self):
        billing_details = [
            self.billing_contact_email_addresses,
            self.billing_contact_names,
            self.billing_reference,
            self.purchase_order_number,
        ]
        if any(billing_details):
            return billing_details
        else:
            return None

    @cached_property
    def services(self):
        from app.models.service import Services

        return Services(organisations_client.get_organisation_services(self.id))

    @cached_property
    def service_ids(self):
        return [s.id for s in self.services]

    @property
    def live_services(self):
        return [s for s in self.services if s.active and s.live]

    @property
    def trial_services(self):
        return [s for s in self.services if not s.active or s.trial_mode]

    @property
    def can_ask_to_join_a_service(self):
        return "can_ask_to_join_a_service" in self.permissions

    @cached_property
    def invited_users(self):
        from app.models.user import OrganisationInvitedUsers

        return OrganisationInvitedUsers(self.id)

    @cached_property
    def active_users(self):
        from app.models.user import OrganisationUsers

        return OrganisationUsers(self.id)

    @cached_property
    def team_members(self):
        return self.invited_users + self.active_users

    def get_team_member(self, user_id):
        from app import User

        if str(user_id) not in {user.id for user in self.active_users}:
            abort(404)

        return User.from_id(user_id)

    @cached_property
    def email_branding(self):
        return EmailBranding.from_id(self.email_branding_id)

    @cached_property
    def email_branding_pool(self):
        return EmailBrandingPool(self.id)

    @property
    def email_branding_pool_excluding_default(self):
        return self.email_branding_pool.excluding(self.email_branding_id)

    @cached_property
    def letter_branding(self):
        return LetterBranding.from_id(self.letter_branding_id)

    @cached_property
    def letter_branding_pool(self):
        return LetterBrandingPool(self.id)

    @property
    def letter_branding_pool_excluding_default(self):
        return self.letter_branding_pool.excluding(self.letter_branding_id)

    @cached_property
    def agreement_signed_by(self):
        if self.agreement_signed_by_id:
            from app.models.user import User

            return User.from_id(self.agreement_signed_by_id)

    def update(self, delete_services_cache=False, **kwargs):
        organisations_client.update_organisation(
            self.id, cached_service_ids=self.service_ids if delete_services_cache else None, **kwargs
        )

    def associate_service(self, service_id):
        organisations_client.update_service_organisation(service_id, self.id)

    def services_and_usage(self, financial_year) -> tuple[dict, date | None]:
        response = organisations_client.get_services_and_usage(self.id, financial_year)
        updated_at = response.get("updated_at")
        if updated_at:
            updated_at = datetime.fromisoformat(updated_at)
        return response["services"], updated_at

    def can_use_org_user_permission(self, permission: str):
        """Validate whether an organisation can see/access/edit a given org permission

        This is used currently because the 'approve own go live requests' is behind an org-level feature flag.
        Once that feature flag is removed we might be able to remove this method altogether as it's possibly not
        something that needs to live forever."""
        if permission == PERMISSION_CAN_MAKE_SERVICES_LIVE:
            return self.can_approve_own_go_live_requests

        return True


class Organisations(SerialisedModelCollection):
    model = Organisation


class AllOrganisations(ModelList, Organisations):
    @staticmethod
    def _get_items(*args, **kwargs):
        return organisations_client.get_organisations(*args, **kwargs)
