from flask import abort
from werkzeug.utils import cached_property

from app.models import JSONModel, ModelList
from app.notify_client.organisations_api_client import organisations_client


class Organisation(JSONModel):

    TYPES = (
        ('central', 'Central government'),
        ('local', 'Local government'),
        ('nhs_central', 'NHS – central government agency or public body'),
        ('nhs_local', 'NHS Trust or Clinical Commissioning Group'),
        ('nhs_gp', 'GP practice'),
        ('emergency_service', 'Emergency service'),
        ('school_or_college', 'School or college'),
        ('other', 'Other'),
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
    }

    @classmethod
    def from_id(cls, org_id):
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

    def as_agreement_statement_for_go_live_request(self, fallback_domain):
        if self.agreement_signed:
            agreement_statement = 'Yes, on behalf of {}.'.format(self.name)
        elif self.name:
            agreement_statement = '{} (organisation is {}, {}).'.format(
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
        else:
            agreement_statement = 'Can’t tell (domain is {}).'.format(fallback_domain)

        if self.request_to_go_live_notes:
            agreement_statement = agreement_statement + ' ' + self.request_to_go_live_notes

        return agreement_statement

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

    @cached_property
    def services(self):
        return organisations_client.get_organisation_services(self.id)

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

    def update(self, **kwargs):
        response = organisations_client.update_organisation(self.id, **kwargs)
        self.__init__(response)

    def associate_service(self, service_id):
        organisations_client.update_service_organisation(
            str(service_id),
            self.id
        )


class Organisations(ModelList):
    client = organisations_client.get_organisations
    model = Organisation
