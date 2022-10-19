from app.models.organisation import Organisation

NHS_EMAIL_BRANDING_ID = "a7dc4e56-660b-4db7-8cff-12c37b12b5ea"


def get_email_choices(service):
    if (
        service.organisation_type == Organisation.TYPE_CENTRAL
        and service.email_branding_id is not None  # GOV.UK is not current branding
        and service.organisation.email_branding_id is None  # no default to supersede it (GOV.UK)
    ):
        yield ("govuk", "GOV.UK")

    if service.is_nhs and service.email_branding_id != NHS_EMAIL_BRANDING_ID:
        yield (NHS_EMAIL_BRANDING_ID, "NHS")

    if service.email_branding_pool:
        for branding in service.email_branding_pool:
            if not branding["id"] == service.email_branding_id:
                yield (branding["id"], branding["name"])
    else:
        # fake branding options
        if (
            service.organisation_type == Organisation.TYPE_CENTRAL
            and service.organisation
            and service.organisation.email_branding_id is None  # don't offer both if org has default
            and service.email_branding_name.lower() != f"GOV.UK and {service.organisation.name}".lower()
        ):
            yield ("govuk_and_org", f"GOV.UK and {service.organisation.name}")

        if (
            service.organisation
            and not service.is_nhs
            and (
                service.email_branding_id is None  # GOV.UK is current branding
                or service.email_branding_id != service.organisation.email_branding_id
            )
        ):
            yield ("organisation", service.organisation.name)


def get_letter_choices(service):

    if service.is_nhs and service.letter_branding_name != "NHS":
        yield ("nhs", "NHS")

    if (
        service.organisation
        and not service.is_nhs
        and (
            service.letter_branding_id is None  # GOV.UK is current branding
            or service.letter_branding_id != service.organisation.letter_branding_id
        )
    ):
        yield ("organisation", service.organisation.name)
