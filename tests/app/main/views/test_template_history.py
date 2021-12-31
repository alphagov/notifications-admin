from flask import url_for


def test_view_template_version(
    client_request,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_template_version,
    mock_get_user,
    mock_get_user_by_email,
    mock_has_permissions,
    fake_uuid,
):
    service_id = fake_uuid
    template_id = fake_uuid
    version = 1
    all_versions_link = url_for(
        'main.view_template_versions',
        service_id=service_id,
        template_id=template_id
    )
    page = client_request.get(
        '.view_template_version',
        service_id=service_id,
        template_id=template_id,
        version=version,
    )

    template = mock_get_template_version(service_id, template_id, version)
    assert api_user_active['name'] in page.text
    assert template['data']['content'] in page.text
    assert all_versions_link in str(page)
    mock_get_template_version.assert_called_with(
        service_id,
        template_id,
        version
    )


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
        '.view_template_versions',
        service_id=service_id,
        template_id=template_id,
    )

    versions = mock_get_template_versions(service_id, template_id)
    assert api_user_active['name'] in page.text
    assert versions['data'][0]['content'] in page.text
    mock_get_template_versions.assert_called_with(
        service_id,
        template_id
    )
