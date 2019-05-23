from flask import url_for


def test_view_template_version(
    logged_in_client,
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
    resp = logged_in_client.get(url_for(
        '.view_template_version',
        service_id=service_id,
        template_id=template_id,
        version=version))

    assert resp.status_code == 200
    resp_data = resp.get_data(as_text=True)
    template = mock_get_template_version(service_id, template_id, version)
    assert api_user_active['name'] in resp_data
    assert template['data']['content'] in resp_data
    assert all_versions_link in resp_data
    mock_get_template_version.assert_called_with(
        service_id,
        template_id,
        version
    )


def test_view_template_versions(
    logged_in_client,
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
    resp = logged_in_client.get(url_for(
        '.view_template_versions',
        service_id=service_id,
        template_id=template_id
    ))

    assert resp.status_code == 200
    resp_data = resp.get_data(as_text=True)
    versions = mock_get_template_versions(service_id, template_id)
    assert api_user_active['name'] in resp_data
    assert versions['data'][0]['content'] in resp_data
    mock_get_template_versions.assert_called_with(
        service_id,
        template_id
    )
