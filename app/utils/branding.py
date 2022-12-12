from app.models.branding import EmailBranding


def get_email_choices(service):
    if service.can_use_govuk_branding and not service.email_branding.is_govuk:
        yield ("govuk", "GOV.UK")

    if (
        service.organisation
        and service.can_use_govuk_branding
        and not service.email_branding.name_like(f"GOV.UK and {service.organisation.name}")
        and not service.email_branding_pool.contains_name(f"GOV.UK and {service.organisation.name}")
    ):
        yield ("govuk_and_org", f"GOV.UK and {service.organisation.name}")

    if service.is_nhs and not service.email_branding.is_nhs:
        yield (EmailBranding.NHS_ID, "NHS")

    if service.email_branding_pool:
        for branding in service.email_branding_pool.excluding(service.email_branding_id):
            yield (branding.id, branding.name)
    elif service.organisation:
        yield ("organisation", service.organisation.name)


def get_letter_choices(service):

    if service.is_nhs and not service.letter_branding.is_nhs:
        yield ("nhs", "NHS")

    if (
        service.organisation
        and not service.is_nhs
        and (not service.letter_branding_id or service.letter_branding_id != service.organisation.letter_branding_id)
    ):
        yield ("organisation", service.organisation.name)
