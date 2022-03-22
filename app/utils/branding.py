from app.models.organisation import Organisation


def get_available_choices(service, branding_type):
    if branding_type == "email":
        organisation_branding_id = service.organisation.email_branding_id if service.organisation else None
        service_branding_id = service.email_branding_id
        service_branding_name = service.email_branding_name
    elif branding_type == "letter":
        organisation_branding_id = service.organisation.letter_branding_id if service.organisation else None
        service_branding_id = service.letter_branding_id
        service_branding_name = service.letter_branding_name

    if (
        service.organisation_type == Organisation.TYPE_CENTRAL
        and organisation_branding_id is None
        and service_branding_id is not None
        and branding_type == "email"
    ):
        yield ('govuk', 'GOV.UK')

    if (
        service.organisation_type == Organisation.TYPE_CENTRAL
        and service.organisation
        and organisation_branding_id is None
        and service_branding_name.lower() != 'GOV.UK and {}'.format(service.organisation.name).lower()
        and branding_type == "email"
    ):
        yield ('govuk_and_org', 'GOV.UK and {}'.format(service.organisation.name))

    if (
        service.organisation_type in {
            Organisation.TYPE_NHS_CENTRAL,
            Organisation.TYPE_NHS_LOCAL,
            Organisation.TYPE_NHS_GP,
        }
        and service_branding_name != 'NHS'
    ):
        yield ('nhs', 'NHS')

    if (
        service.organisation
        and service.organisation_type not in {
            Organisation.TYPE_NHS_LOCAL,
            Organisation.TYPE_NHS_CENTRAL,
            Organisation.TYPE_NHS_GP,
        }
        and (
            service_branding_id is None
            or service_branding_id != organisation_branding_id
        )
    ):
        yield ('organisation', service.organisation.name)
