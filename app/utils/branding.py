import os

from app.models.branding import EmailBranding, LetterBranding


def get_email_choices(service):
    if service.can_use_govuk_branding:

        if not service.email_branding.is_govuk:
            yield ("govuk", "GOV.UK")

        if service.organisation and not (
            service.email_branding.name_like(f"GOV.UK and {service.organisation.name}")
            or service.email_branding_pool.contains_name(f"GOV.UK and {service.organisation.name}")
        ):
            yield ("govuk_and_org", f"GOV.UK and {service.organisation.name}")

    if service.is_nhs and not service.email_branding.is_nhs:
        yield (EmailBranding.NHS_ID, "NHS")

    for branding in service.email_branding_pool.excluding(service.email_branding_id):
        yield (branding.id, branding.name)

    if service.organisation and not service.email_branding_pool:
        yield ("organisation", service.organisation.name)


def get_letter_choices(service):

    if service.is_nhs and not service.letter_branding.is_nhs:
        yield (LetterBranding.NHS_ID, "NHS")

    if service.letter_branding_pool:
        for branding in service.letter_branding_pool.excluding(service.letter_branding_id):
            yield (branding.id, branding.name)

    if service.organisation and not service.letter_branding_pool:
        yield ("organisation", service.organisation.name)


def letter_filename_for_db_from_logo_key(logo_key):
    # For letters, we store just the filename without extension - note this is different to EmailBranding where we
    # store a full filepathFor letters, in the DB we store the filename without the extension.
    # TODO: store full filepath with folder and extension
    return os.path.splitext(os.path.basename(logo_key))[0]
