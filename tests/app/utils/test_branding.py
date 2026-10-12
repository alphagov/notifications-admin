from datetime import datetime
from unittest.mock import PropertyMock
from uuid import UUID

import pytest

from app.models.branding import Branding, EmailBranding, LetterBranding
from app.models.service import Service
from app.utils.branding import get_email_choices, get_letter_choices
from tests import organisation_json
from tests.conftest import create_email_branding


@pytest.mark.parametrize(
    "function, org_type, expected_options",
    [
        (get_email_choices, "central", []),
        (get_letter_choices, "central", []),
        (get_email_choices, "local", []),
        (get_letter_choices, "local", []),
        (get_email_choices, "nhs_central", [(EmailBranding.NHS_ID, "NHS")]),
        (get_letter_choices, "nhs_central", [(LetterBranding.NHS_ID, "NHS")]),
    ],
)
def test_get_choices_service_not_assigned_to_org(
    service_one,
    function,
    mock_get_empty_email_branding_pool,
    org_type,
    expected_options,
):
    service_one["organisation_type"] = org_type
    service = Service(service_one)

    options = function(service)
    assert list(options) == expected_options


@pytest.mark.parametrize(
    "org_type, branding_id, expected_options",
    [
        (
            "central",
            None,
            [
                ("govuk_and_org", "GOV.UK and Test Organisation"),
                ("organisation", "Test Organisation"),
            ],
        ),
        (
            "central",
            UUID(version=4, bytes=b"some-branding-id"),
            [
                ("govuk", "GOV.UK"),  # central orgs can switch back to GOV.UK
                ("govuk_and_org", "GOV.UK and Test Organisation"),
                ("organisation", "Test Organisation"),
            ],
        ),
        ("local", None, [("organisation", "Test Organisation")]),
        ("local", UUID(version=4, bytes=b"some-branding-id"), [("organisation", "Test Organisation")]),
        (
            "nhs_central",
            None,
            [
                (EmailBranding.NHS_ID, "NHS"),
                ("organisation", "Test Organisation"),
            ],
        ),
        (
            "nhs_central",
            EmailBranding.NHS_ID,
            [
                # don't show NHS if it's the current branding
                ("organisation", "Test Organisation"),
            ],
        ),
    ],
)
def test_get_email_choices_service_assigned_to_org(
    notify_admin,
    service_one,
    org_type,
    branding_id,
    expected_options,
    mock_get_empty_email_branding_pool,
    mock_get_service_organisation,
    mock_get_email_branding,
    mocker,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type=org_type)
    )
    mocker.patch("app.models.service.Service.email_branding_id", new_callable=PropertyMock, return_value=branding_id)

    options = get_email_choices(service)
    assert list(options) == expected_options


@pytest.mark.parametrize(
    "org_type, expected_options",
    [
        (
            "central",
            [
                ("govuk", "GOV.UK"),
                ("govuk_and_org", "GOV.UK and Test Organisation"),
                ("organisation", "Test Organisation"),
            ],
        ),
        (
            "local",
            [
                ("organisation", "Test Organisation"),
            ],
        ),
    ],
)
def test_get_email_choices_org_has_default_branding(
    notify_admin,
    service_one,
    org_type,
    expected_options,
    mock_get_empty_email_branding_pool,
    mock_get_service_organisation,
    mock_get_email_branding,
    mocker,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(organisation_type=org_type),
    )
    mocker.patch(
        "app.models.service.Service.email_branding_id",
        new_callable=PropertyMock,
        return_value=str(UUID(version=4, int=999)),
    )

    options = get_email_choices(service)
    assert list(options) == expected_options


@pytest.mark.parametrize(
    "branding_name, expected_options",
    [
        (
            "GOV.UK and something else",
            [
                ("govuk", "GOV.UK"),
                ("govuk_and_org", "GOV.UK and Test Organisation"),
                ("organisation", "Test Organisation"),
            ],
        ),
        (
            "GOv.Uk and test OrganisatioN",
            [
                ("govuk", "GOV.UK"),
                ("organisation", "Test Organisation"),
            ],
        ),
    ],
)
def test_get_email_choices_branding_name_in_use(
    notify_admin,
    service_one,
    branding_name,
    expected_options,
    mock_get_empty_email_branding_pool,
    mock_get_service_organisation,
    mocker,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type="central")
    )
    mocker.patch(
        "app.models.service.Service.email_branding_id",
        new_callable=PropertyMock,
        return_value=UUID(version=4, bytes=b"some-branding-id"),
    )
    mocker.patch(
        "app.email_branding_client.get_email_branding",
        return_value=create_email_branding(UUID(version=4, int=999), {"name": branding_name}),
    )

    options = get_email_choices(service)
    # don't show option if its name is similar to current branding
    assert list(options) == expected_options


@pytest.mark.parametrize(
    "branding_pool, expected_options",
    (
        (
            [
                {
                    "logo": "example_1.png",
                    "name": "Email branding name 1",
                    "text": "Email branding text 1",
                    "id": str(UUID(version=4, int=1)),
                    "colour": "#f00",
                    "brand_type": "org",
                },
                {
                    "logo": "example_2.png",
                    "name": "Email branding name 2",
                    "text": "Email branding text 2",
                    "id": str(UUID(version=4, int=2)),
                    "colour": "#f00",
                    "brand_type": "org",
                },
            ],
            [
                ("govuk", "GOV.UK"),
                ("govuk_and_org", "GOV.UK and Test Organisation"),
                (str(UUID(version=4, int=2)), "Email branding name 2"),
            ],
        ),
        (
            [
                {
                    "logo": "example_1.png",
                    "name": "GOV.UK and test organisation",
                    "text": "test organisation",
                    "id": str(UUID(version=4, bytes=b"govuk-and-org-id")),
                    "colour": None,
                    "brand_type": "both",
                },
            ],
            [
                ("govuk", "GOV.UK"),
                (str(UUID(version=4, bytes=b"govuk-and-org-id")), "GOV.UK and test organisation"),
            ],
        ),
    ),
)
def test_current_email_branding_is_not_displayed_in_email_branding_pool_options(
    notify_admin,
    service_one,
    mock_get_email_branding_pool,
    mock_get_service_organisation,
    mock_get_email_branding,
    branding_pool,
    expected_options,
    mocker,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type="central")
    )
    mocker.patch(
        "app.models.service.Service.email_branding_id",
        new_callable=PropertyMock,
        return_value=str(UUID(version=4, int=1)),
    )

    mocker.patch("app.models.branding.EmailBrandingPool._get_items", return_value=branding_pool)

    options = get_email_choices(service)
    assert list(options) == expected_options


@pytest.mark.parametrize(
    "org_type, branding_id, expected_options",
    [
        ("central", None, [("organisation", "Test Organisation")]),
        ("local", None, [("organisation", "Test Organisation")]),
        ("local", str(UUID(version=4, int=1)), [("organisation", "Test Organisation")]),
        ("nhs_central", None, [(LetterBranding.NHS_ID, "NHS"), ("organisation", "Test Organisation")]),
    ],
)
def test_get_letter_choices_service_assigned_to_org(
    notify_admin,
    service_one,
    org_type,
    branding_id,
    expected_options,
    mock_get_service_organisation,
    mock_get_empty_letter_branding_pool,
    mocker,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type=org_type)
    )
    mocker.patch(
        "app.models.service.Service.letter_branding_id",
        new_callable=PropertyMock,
        return_value=branding_id,
    )

    options = get_letter_choices(service)
    assert list(options) == expected_options


def test_get_letter_choices_shows_org_branding_if_org_has_empty_pool(
    notify_admin,
    service_one,
    mock_get_service_organisation,
    mock_get_empty_letter_branding_pool,
    mocker,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(
            organisation_type="central",
            letter_branding_id=str(UUID(version=4, bytes=b"org-branding-id-")),
        ),
    )
    mocker.patch(
        "app.models.service.Service.letter_branding_id",
        new_callable=PropertyMock,
        return_value=UUID(version=4, bytes=b"some-branding-id"),
    )
    options = get_letter_choices(service)
    assert list(options) == [
        ("organisation", "Test Organisation"),
    ]


@pytest.mark.parametrize(
    "branding_name, expected_options",
    [
        (
            "NHS something else",
            [
                (LetterBranding.NHS_ID, "NHS"),
                ("organisation", "Test Organisation"),
            ],
        ),
        (
            "NHS",
            [
                # don't show NHS option if it's the current branding
                ("organisation", "Test Organisation"),
            ],
        ),
    ],
)
def test_get_letter_choices_shows_nhs_branding_for_nhs_services(
    notify_admin,
    service_one,
    branding_name,
    expected_options,
    mock_get_service_organisation,
    mock_get_empty_letter_branding_pool,
    mocker,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type="nhs_central")
    )
    mocker.patch(
        "app.models.service.Service.letter_branding_id",
        new_callable=PropertyMock,
        return_value=str(UUID(version=4, bytes=b"org-branding-id-")),
    )
    mocker.patch("app.letter_branding_client.get_letter_branding", return_value={"name": branding_name})

    options = get_letter_choices(service)
    assert list(options) == expected_options


def test_current_letter_branding_is_not_displayed_in_letter_branding_pool_options(
    notify_admin,
    service_one,
    mock_get_letter_branding_pool,
    mock_get_service_organisation,
    mocker,
):
    service = Service(service_one)

    mocker.patch(
        "app.organisations_client.get_organisation", return_value=organisation_json(organisation_type="central")
    )
    mocker.patch(
        "app.models.service.Service.letter_branding_id",
        new_callable=PropertyMock,
        side_effect=[str(UUID(version=4, int=1))],
    )

    branding_pool = [
        {
            "filename": "example_1.png",
            "name": "Letter branding name 1",
            "id": str(UUID(version=4, int=1)),
        },
        {
            "filename": "example_2.png",
            "name": "Letter branding name 2",
            "id": str(UUID(version=4, int=2)),
        },
    ]

    # note: no organisation option visible since the org already has a branding pool
    expected_options = [
        (str(UUID(version=4, int=2)), "Letter branding name 2"),
    ]
    mocker.patch("app.models.branding.LetterBrandingPool._get_items", return_value=branding_pool)

    options = get_letter_choices(service)
    assert list(options) == expected_options


def test_branding_serialize_returns_expected_dict_and_is_a_copy():
    data = {
        "id": str(UUID(version=4, int=123)),
        "name": "My brand",
        "created_by": None,
        "created_at": datetime(2020, 1, 1, 0, 0),
        "updated_at": datetime(2020, 1, 2, 0, 0),
    }

    branding = Branding(data)
    serialized = branding.serialize()

    # returns the same data
    assert serialized == data

    # but it's a copy: mutating the returned dict doesn't change the instance backing dict
    serialized["name"] = "mutated"
    assert branding.name == "My brand"
    assert branding._dict["name"] == "My brand"
