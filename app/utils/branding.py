from app.models.organisation import Organisation

NHS_TYPES = dict(Organisation.NHS_TYPES).keys()
NHS_EMAIL_BRANDING_ID = 'a7dc4e56-660b-4db7-8cff-12c37b12b5ea'


def get_email_choices(service):
    organisation_branding_id = service.organisation.email_branding_id if service.organisation else None
    service_branding_id = service.email_branding_id

    if (
        service.organisation_type == Organisation.TYPE_CENTRAL
        and organisation_branding_id is None
        and service_branding_id is not None
    ):
        yield ('govuk', 'GOV.UK')

    if (
        service.organisation_type == Organisation.TYPE_CENTRAL
        and service.organisation
        and organisation_branding_id is None
        and service.email_branding_name.lower() != 'GOV.UK and {}'.format(service.organisation.name).lower()
    ):
        yield ('govuk_and_org', 'GOV.UK and {}'.format(service.organisation.name))

    if (
        service.organisation_type in NHS_TYPES
        and service_branding_id != NHS_EMAIL_BRANDING_ID
    ):
        yield ('nhs', 'NHS')

    if (
        service.organisation
        and service.organisation_type not in NHS_TYPES
        and (
            service_branding_id is None
            or service_branding_id != organisation_branding_id
        )
    ):
        yield ('organisation', service.organisation.name)


def get_letter_choices(service):
    organisation_branding_id = service.organisation.letter_branding_id if service.organisation else None
    service_branding_id = service.letter_branding_id

    if (
        service.organisation_type in NHS_TYPES
        and service.letter_branding_name != 'NHS'
    ):
        yield ('nhs', 'NHS')

    if (
        service.organisation
        and service.organisation_type not in NHS_TYPES
        and (
            service_branding_id is None
            or service_branding_id != organisation_branding_id
        )
    ):
        yield ('organisation', service.organisation.name)
