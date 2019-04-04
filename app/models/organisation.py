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
    }

    def __init__(self, _dict):

        super().__init__(_dict)

        if self._dict == {}:
            self.name, self.crown, self.agreement_signed = None, None, None

    @property
    def crown_status(self):
        return self.crown

    def as_human_readable(self, fallback_domain):
        if 'dwp.' in ''.join(self.domains):
            return 'DWP - Requires OED approval'
        if self.agreement_signed:
            return 'Yes, on behalf of {}'.format(self.name)
        elif self.name:
            return '{} (organisation is {}, {})'.format(
                {
                    False: 'No',
                    None: 'Can’t tell',
                }.get(self.agreement_signed),
                self.name,
                {
                    True: 'a crown body',
                    False: 'a non-crown body',
                    None: 'crown status unknown',
                }.get(self.crown_status),
            )
        else:
            return 'Can’t tell (domain is {})'.format(fallback_domain)

    def as_info_for_branding_request(self, fallback_domain):
        return self.name or 'Can’t tell (domain is {})'.format(fallback_domain)

    @property
    def as_jinja_template(self):
        if self.crown_status is None:
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

    def as_pricing_paragraph(self, **kwargs):
        return Markup(self._as_pricing_paragraph(**kwargs))

    def _as_pricing_paragraph(self, pricing_link, download_link, support_link, signed_in):

        if not signed_in:
            return ((
                '<a href="{}">Sign in</a> to download a copy or find '
                'out if one is already in place with your organisation.'
            ).format(pricing_link))

        if self.agreement_signed is None:
            return ((
                '<a href="{}">Download the agreement</a> or '
                '<a href="{}">contact us</a> to find out if we already '
                'have one in place with your organisation.'
            ).format(download_link, support_link))

        return (
            '<a href="{}">Download the agreement</a> '
            '({} {}).'.format(
                download_link,
                self.name,
                {
                    True: 'has already accepted it',
                    False: 'hasn’t accepted it yet'
                }.get(self.agreement_signed)
            )
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
        if self.crown_status is None:
            abort(404)
        return self.crown_status
