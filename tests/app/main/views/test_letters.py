from functools import partial

import pytest
from flask import url_for

letters_urls = [
    partial(url_for, 'main.add_service_template', template_type='letter'),
]


@pytest.mark.parametrize('url', letters_urls)
@pytest.mark.parametrize('permissions, response_code', [
    (['letter'], 200),
    ([], 403)
])
def test_letters_access_restricted(
    logged_in_platform_admin_client,
    mocker,
    permissions,
    response_code,
    mock_get_service_templates,
    url,
    service_one,
):
    service_one['permissions'] = permissions

    mocker.patch('app.service_api_client.get_service', return_value={"data": service_one})

    response = logged_in_platform_admin_client.get(url(service_id=service_one['id']))

    assert response.status_code == response_code


@pytest.mark.parametrize('url', letters_urls)
def test_letters_lets_in_without_permission(
    client,
    mocker,
    mock_login,
    mock_has_permissions,
    api_user_active,
    mock_get_service_templates,
    url,
    service_one
):
    service_one['permissions'] = ['letter']
    mocker.patch('app.service_api_client.get_service', return_value={"data": service_one})

    client.login(api_user_active)
    response = client.get(url(service_id=service_one['id']))

    assert api_user_active['permissions'] == {}
    assert response.status_code == 200


@pytest.mark.parametrize('permissions, choices', [
    (
        ['email', 'sms', 'letter'],
        ['Email', 'Text message', 'Letter', 'Copy an existing template']
    ),
    (
        ['email', 'sms'],
        ['Email', 'Text message', 'Copy an existing template']
    ),
])
def test_given_option_to_add_letters_if_allowed(
    client_request,
    service_one,
    mocker,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_organisations_and_services_for_user,
    permissions,
    choices,
):
    service_one['permissions'] = permissions

    page = client_request.get('main.choose_template', service_id=service_one['id'])

    radios = page.select('#add_new_template_form input[type=radio]')
    labels = page.select('#add_new_template_form label')

    assert len(radios) == len(choices)
    assert len(labels) == len(choices)

    for index, choice in enumerate(permissions):
        assert radios[index]['value'] == choice

    for index, label in enumerate(choices):
        assert labels[index].text.strip() == label
