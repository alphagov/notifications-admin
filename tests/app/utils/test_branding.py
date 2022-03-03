import pytest

from app.models.service import Service
from app.utils.branding import get_available_choices


@pytest.mark.parametrize('branding_type', ['email', 'letter'])
@pytest.mark.parametrize('org_type, existing_branding, expected_options', [
    ('central', None, []),
    ('local', None, []),
    ('nhs_central', None, [('nhs', 'NHS')]),
    ('nhs_local', None, [('nhs', 'NHS')]),
    ('nhs_gp', None, [('nhs', 'NHS')]),
    ('emergency_service', None, []),
    ('other', None, []),
])
def test_get_available_choices_no_org(
    service_one,
    branding_type,
    org_type,
    existing_branding,
    expected_options,
):
    service_one['organisation_type'] = org_type
    service = Service(service_one)

    options = get_available_choices(service, branding_type=branding_type)
    assert list(options) == expected_options
