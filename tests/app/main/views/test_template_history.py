from datetime import datetime

import pytest
from flask import url_for

from tests import template_version_json
from tests.conftest import normalize_spaces


@pytest.mark.parametrize(
    "archived, version, expected_hint",
    [
        (False, 1, "Created 31 May 2020 at 1:00pm by Test User"),
        (False, 2, "Edit made 6 June 2020 at 1:00pm by Test User"),
        (True, 2, "Deleted 6 June 2020 at 1:00pm by Test User"),
        # This shouldn't happen in real life but just for completeness
        (True, 1, "Created 31 May 2020 at 1:00pm by Test User"),
    ],
)
def test_view_template_version(
    client_request,
    api_user_active,
    mock_has_permissions,
    mocker,
    fake_uuid,
    archived,
    version,
    expected_hint,
):
    # 12pm utc = 1pm bst
    created_at_timestamp = datetime(2020, 5, 31, 12, 0).strftime("%Y-%m-%d %H:%M:%S.%f")
    updated_at_timestamp = datetime(2020, 6, 6, 12, 0).strftime("%Y-%m-%d %H:%M:%S.%f")

    service_id = fake_uuid
    template_id = fake_uuid
    all_versions_link = url_for("main.view_template_versions", service_id=service_id, template_id=template_id)
    template_version = template_version_json(
        service_id,
        template_id,
        api_user_active,
        version=version,
        archived=archived,
        created_at=created_at_timestamp,
        updated_at=updated_at_timestamp,
    )
    mock_get_template_version = mocker.patch(
        "app.service_api_client.get_service_template", return_value={"data": template_version}
    )

    page = client_request.get(
        ".view_template_version",
        service_id=service_id,
        template_id=template_id,
        version=version,
    )

    assert normalize_spaces(page.select_one("p.hint").text) == expected_hint
    assert template_version["content"] in page.text
    assert all_versions_link in str(page)
    mock_get_template_version.assert_called_with(service_id, template_id, version)


def test_view_template_versions(
    client_request,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_template_versions,
    mock_get_service_template,
    mock_get_user,
    mock_get_user_by_email,
    mock_has_permissions,
    fake_uuid,
):
    service_id = fake_uuid
    template_id = fake_uuid
    page = client_request.get(
        ".view_template_versions",
        service_id=service_id,
        template_id=template_id,
    )

    versions = mock_get_template_versions(service_id, template_id)
    assert api_user_active["name"] in page.text
    assert versions["data"][0]["content"] in page.text
    mock_get_template_versions.assert_called_with(service_id, template_id)


def test_view_template_versions_pages(
    client_request,
    api_user_active,
    mocker,
    mock_login,
    mock_get_service,
    mock_get_service_template,
    mock_get_user,
    mock_get_user_by_email,
    mock_has_permissions,
    fake_uuid,
):
    service_id = fake_uuid
    template_id = fake_uuid

    versions = [template_version_json(service_id, template_id, api_user_active, version=v + 1) for v in range(51)][::-1]
    mocker.patch(
        "app.service_api_client.get_service_template_versions", side_effect=lambda sid, tid: {"data": versions}
    )

    page = client_request.get(".view_template_versions", service_id=service_id, template_id=template_id)
    assert api_user_active["name"] in page.text
    next_page = page.select_one("a[rel=next]")
    previous_page = page.select_one("a[rel=previous]")
    assert next_page
    assert not previous_page
    assert "Version 51: " in page.text
    assert "Version 26: " not in page.text
    assert "Version 1: " not in page.text
    assert "Next page" in page.text
    assert "Previous page" not in page.text

    page = client_request.get_url(next_page.get("href"))
    assert api_user_active["name"] in page.text
    assert versions[0]["content"] in page.text
    next_page = page.select_one("a[rel=next]")
    previous_page = page.select_one("a[rel=previous]")
    assert next_page
    assert previous_page
    assert "Version 51: " not in page.text
    assert "Version 26: " in page.text
    assert "Version 1: " not in page.text
    assert "Next page" in page.text
    assert "Previous page" in page.text

    page = client_request.get_url(next_page.get("href"))
    assert api_user_active["name"] in page.text
    assert versions[0]["content"] in page.text
    next_page = page.select_one("a[rel=next]")
    previous_page = page.select_one("a[rel=previous]")
    assert not next_page
    assert previous_page
    assert "Version 51: " not in page.text
    assert "Version 26: " not in page.text
    assert "Version 1: " in page.text
    assert "Next page" not in page.text
    assert "Previous page" in page.text
