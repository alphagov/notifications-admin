from flask import abort
from werkzeug.utils import cached_property

from app.models import JSONModel, ModelList
from app.notify_client.email_branding_client import email_branding_client
from app.notify_client.letter_branding_client import letter_branding_client
from app.notify_client.organisations_api_client import organisations_client


class Organisation(JSONModel):

    TYPE_CENTRAL = 'central'
    TYPE_LOCAL = 'local'
    TYPE_NHS_CENTRAL = 'nhs_central'
    TYPE_NHS_LOCAL = 'nhs_local'
    TYPE_NHS_GP = 'nhs_gp'
    TYPE_EMERGENCY_SERVICE = 'emergency_service'
    TYPE_SCHOOL_OR_COLLEGE = 'school_or_college'
    TYPE_OTHER = 'other'

    TYPES = (
        (TYPE_CENTRAL, 'Central government'),
        (TYPE_LOCAL, 'Local government'),
        (TYPE_NHS_CENTRAL, 'NHS – central government agency or public body'),
        (TYPE_NHS_LOCAL, 'NHS Trust or Clinical Commissioning Group'),
        (TYPE_NHS_GP, 'GP practice'),
        (TYPE_EMERGENCY_SERVICE, 'Emergency service'),
        (TYPE_SCHOOL_OR_COLLEGE, 'School or college'),
        (TYPE_OTHER, 'Other'),
    )

    ALLOWED_PROPERTIES = {
        'id',
        'name',
        'active',
        'crown',
        'organisation_type',
        'letter_branding_id',
        'email_branding_id',
        'agreement_signed',
        'agreement_signed_at',
        'agreement_signed_by_id',
        'agreement_signed_version',
        'agreement_signed_on_behalf_of_name',
        'agreement_signed_on_behalf_of_email_address',
        'domains',
        'request_to_go_live_notes',
        'count_of_live_services',
        'billing_contact_email_addresses',
        'billing_contact_names',
        'billing_reference',
        'purchase_order_number',
        'notes',
    }

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
                'crown': True,
                'non-crown': False,
                'unknown': None,
            }.get(form.crown_status.data),
            organisation_type=form.organisation_type.data,
        )

    @classmethod
    def create(cls, name, crown, organisation_type, agreement_signed=False):
        return cls(organisations_client.create_organisation(
            name=name,
            crown=crown,
            organisation_type=organisation_type,
            agreement_signed=agreement_signed,
        ))

    def __init__(self, _dict):

        super().__init__(_dict)

        if self._dict == {}:
            self.name = None
            self.crown = None
            self.agreement_signed = None
            self.domains = []
            self.organisation_type = None
            self.request_to_go_live_notes = None
            self.email_branding_id = None

    def as_agreement_statement_for_go_live_request(self, fallback_domain):
        if self.name:
            return '{} (organisation is {}, {}).'.format(
                {
                    False: 'No',
                    None: 'Can’t tell',
                }.get(self.agreement_signed),
                self.name,
                {
                    True: 'a crown body',
                    False: 'a non-crown body',
                    None: 'crown status unknown',
                }.get(self.crown),
            )
        return 'Can’t tell (domain is {}).'.format(fallback_domain)

    def as_info_for_branding_request(self, fallback_domain):
        return self.name or 'Can’t tell (domain is {})'.format(fallback_domain)

    @property
    def organisation_type_label(self):
        return dict(self.TYPES).get(self.organisation_type)

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
            self.purchase_order_number
        ]
        if any(billing_details):
            return billing_details
        else:
            return None

    @cached_property
    def services(self):
        return organisations_client.get_organisation_services(self.id)

    @cached_property
    def service_ids(self):
        return [s['id'] for s in self.services]

    @property
    def live_services(self):
        return [s for s in self.services if s['active'] and not s['restricted']]

    @property
    def trial_services(self):
        return [s for s in self.services if not s['active'] or s['restricted']]

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
        return sorted(
            self.invited_users + self.active_users,
            key=lambda user: user.email_address.lower(),
        )

    @cached_property
    def email_branding(self):
        if self.email_branding_id:
            return email_branding_client.get_email_branding(
                self.email_branding_id
            )['email_branding']

    @property
    def email_branding_name(self):
        if self.email_branding_id:
            return self.email_branding['name']
        return 'GOV.UK'

    @cached_property
    def letter_branding(self):
        if self.letter_branding_id:
            return letter_branding_client.get_letter_branding(
                self.letter_branding_id
            )

    @cached_property
    def agreement_signed_by(self):
        if self.agreement_signed_by_id:
            from app.models.user import User
            return User.from_id(self.agreement_signed_by_id)

    def update(self, delete_services_cache=False, **kwargs):
        response = organisations_client.update_organisation(
            self.id,
            cached_service_ids=self.service_ids if delete_services_cache else None,
            **kwargs
        )
        self.__init__(response)

    def associate_service(self, service_id):
        organisations_client.update_service_organisation(
            service_id,
            self.id
        )

    def services_and_usage(self, financial_year):
        return organisations_client.get_services_and_usage(self.id, financial_year)


class Organisations(ModelList):
    client_method = organisations_client.get_organisations
    model = Organisation
