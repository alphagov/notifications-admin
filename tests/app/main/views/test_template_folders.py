

def test_add_folder(
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
