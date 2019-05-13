from flask import Markup, abort

from app.models import JSONModel


class Organisation(JSONModel):

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
        'domains',
        'request_to_go_live_notes',
    }

    def __init__(self, _dict):

        super().__init__(_dict)

        if self._dict == {}:
            self.name = None
            self.crown = None
            self.agreement_signed = None
            self.domains = []
            self.organisation_type = None
            self.request_to_go_live_notes = None

    def as_human_readable(self, fallback_domain):
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
    def as_jinja_template(self):
        if self.crown is None:
            return 'agreement-choose'
        if self.agreement_signed:
            return 'agreement-signed'
        return 'agreement'

    def as_terms_of_use_paragraph(self, **kwargs):
        return Markup(self._as_terms_of_use_paragraph(**kwargs))

    def _as_terms_of_use_paragraph(self, terms_link, download_link, support_link, signed_in):

        if not signed_in:
            return ((
                '{} <a href="{}">Sign in</a> to download a copy '
                'or find out if one is already in place.'
            ).format(self._acceptance_required, terms_link))

        if self.agreement_signed is None:
            return ((
                '{} <a href="{}">Download the agreement</a> or '
                '<a href="{}">contact us</a> to find out if we already '
                'have one in place with your organisation.'
            ).format(self._acceptance_required, download_link, support_link))

        if self.agreement_signed is False:
            return ((
                '{} <a href="{}">Download a copy</a>.'
            ).format(self._acceptance_required, download_link))

        return (
            'Your organisation ({}) has already accepted the '
            'GOV.UK&nbsp;Notify data sharing and financial '
            'agreement.'.format(self.name)
        )

    @property
    def _acceptance_required(self):
        return (
            'Your organisation {} must also accept our data sharing '
            'and financial agreement.'.format(
                '({})'.format(self.name) if self.name else '',
            )
        )

    @property
    def crown_status_or_404(self):
        if self.crown is None:
            abort(404)
        return self.crown
