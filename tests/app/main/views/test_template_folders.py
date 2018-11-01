from flask import url_for


def test_add_page_shows_option_for_folder(
    client_request,
    service_one,
    mocker,
    mock_get_service_templates,
    mock_get_organisations_and_services_for_user,
):
    service_one['permissions'] += ['edit_folders']
    mocker.patch('app.service_api_client.get_service', return_value={"data": service_one})

    page = client_request.get(
        'main.add_template_by_type',
        service_id=service_one['id'],
        _test_page_title=False
    )

    radios = page.select('input[type=radio]')
    labels = page.select('label')

    assert [x['value'] for x in radios] == ['email', 'sms', 'copy-existing', 'folder']
    assert [x.text.strip() for x in labels] == [
        'Email template',
        'Text message template',
        'Copy of an existing template',
        'Folder'
    ]


def test_get_add_template_folder_page(client_request, service_one):
    service_one['permissions'] += ['edit_folders']

    page = client_request.get('main.add_template_folder', service_id=service_one['id'])

    assert page.find('input', attrs={'name': 'name'}) is not None


def test_add_template_folder_page_rejects_if_service_doesnt_have_permission(client_request, service_one):
    client_request.get('main.add_template_folder', service_id=service_one['id'], _expected_status=403)
    client_request.post('main.add_template_folder', service_id=service_one['id'], _expected_status=403)


def test_post_add_template_folder_page(client_request, service_one, mocker):
    mock_create = mocker.patch('app.template_folder_api_client.create_template_folder')

    service_one['permissions'] += ['edit_folders']

    client_request.post(
        'main.add_template_folder',
        service_id=service_one['id'],
        _data={'name': 'foo'},
        _expected_redirect=url_for(
            'main.choose_template',
            service_id=service_one['id'],
            _external=True,
        )
    )

    mock_create.assert_called_once_with(service_one['id'], name='foo', parent_id=None)
