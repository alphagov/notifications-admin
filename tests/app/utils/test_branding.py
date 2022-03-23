from unittest.mock import PropertyMock

import pytest

from app.models.service import Service
from app.utils.branding import (
    NHS_EMAIL_BRANDING_ID,
    get_email_choices,
    get_letter_choices,
)
from tests import organisation_json


@pytest.mark.parametrize('function', [get_email_choices, get_letter_choices])
@pytest.mark.parametrize('org_type, expected_options', [
    ('central', []),
    ('local', []),
    ('nhs_central', [('nhs', 'NHS')]),
])
def test_get_choices_service_not_assigned_to_org(
    service_one,
    function,
    org_type,
    expected_options,
):
    service_one['organisation_type'] = org_type
    service = Service(service_one)

    options = function(service)
    assert list(options) == expected_options


@pytest.mark.parametrize('org_type, branding_id, expected_options', [
    ('central', None, [
        ('govuk_and_org', 'GOV.UK and Test Organisation'),
        ('organisation', 'Test Organisation'),
    ]),
    ('central', 'some-branding-id', [
        ('govuk', 'GOV.UK'),  # central orgs can switch back to GOV.UK
        ('govuk_and_org', 'GOV.UK and Test Organisation'),
        ('organisation', 'Test Organisation'),
    ]),
    ('local', None, [
        ('organisation', 'Test Organisation')
    ]),
    ('local', 'some-branding-id', [
        ('organisation', 'Test Organisation')
    ]),
    ('nhs_central', None, [
        ('nhs', 'NHS')
    ]),
    ('nhs_central', NHS_EMAIL_BRANDING_ID, [
        # don't show NHS if it's the current branding
    ]),
])
def test_get_email_choices_service_assigned_to_org(
    mocker,
    service_one,
    org_type,
    branding_id,
    expected_options,
    mock_get_service_organisation,
    mock_get_email_branding
):
    service = Service(service_one)

    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(organisation_type=org_type)
    )
    mocker.patch(
        'app.models.service.Service.email_branding_id',
        new_callable=PropertyMock,
        return_value=branding_id
    )

    options = get_email_choices(service)
    assert list(options) == expected_options


@pytest.mark.parametrize('org_type, branding_id, expected_options', [
    ('central', None, [
        ('organisation', 'Test Organisation')
    ]),
    ('local', None, [
        ('organisation', 'Test Organisation')
    ]),
    ('local', 'some-random-branding', [
        ('organisation', 'Test Organisation')
    ]),
    ('nhs_central', None, [
        ('nhs', 'NHS')
    ]),
])
def test_get_letter_choices_service_assigned_to_org(
    mocker,
    service_one,
    org_type,
    branding_id,
    expected_options,
    mock_get_service_organisation,
):
    service = Service(service_one)

    mocker.patch(
        'app.organisations_client.get_organisation',
        return_value=organisation_json(organisation_type=org_type)
    )
    mocker.patch(
        'app.models.service.Service.letter_branding_id',
        new_callable=PropertyMock,
        return_value=branding_id,
    )

    options = get_letter_choices(service)
    assert list(options) == expected_options
