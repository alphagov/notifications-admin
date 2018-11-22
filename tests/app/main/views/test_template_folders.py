import uuid

import pytest
from flask import url_for

from tests.conftest import SERVICE_ONE_ID, normalize_spaces

PARENT_FOLDER_ID = '7e979e79-d970-43a5-ac69-b625a8d147b0'
CHILD_FOLDER_ID = '92ee1ee0-e4ee-4dcc-b1a7-a5da9ebcfa2b'
GRANDCHILD_FOLDER_ID = 'fafe723f-1d39-4a10-865f-e551e03d8886'
FOLDER_TWO_ID = 'bbbb222b-2b22-2b22-222b-b222b22b2222'


def _folder(name, folder_id=None, parent=None):
    return {
        'name': name,
        'id': folder_id or str(uuid.uuid4()),
        'parent_id': parent,
    }


def _template(template_type, name, parent=None):
    return {
        'id': str(uuid.uuid4()),
        'name': name,
        'template_type': template_type,
        'folder': parent,
    }


@pytest.mark.parametrize('parent_folder_id', [None, PARENT_FOLDER_ID])
def test_add_page_shows_option_for_folder(
    client_request,
    service_one,
    parent_folder_id,
    mocker,
    mock_get_service_templates,
    mock_get_organisations_and_services_for_user,
):
    service_one['permissions'] += ['edit_folders']
    mocker.patch('app.service_api_client.get_service', return_value={"data": service_one})

    page = client_request.get(
        'main.add_template_by_type',
        service_id=service_one['id'],
        template_folder_id=parent_folder_id,
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


@pytest.mark.parametrize('parent_folder_id', [None, PARENT_FOLDER_ID])
def test_get_add_template_folder_page(client_request, service_one, parent_folder_id):
    service_one['permissions'] += ['edit_folders']

    page = client_request.get(
        'main.add_template_folder',
        service_id=service_one['id'],
        template_folder_id=parent_folder_id
    )

    assert page.select_one('input[name=name]') is not None


def test_add_template_folder_page_rejects_if_service_doesnt_have_permission(client_request, service_one):
    client_request.get('main.add_template_folder', service_id=service_one['id'], _expected_status=403)
    client_request.post('main.add_template_folder', service_id=service_one['id'], _expected_status=403)


@pytest.mark.parametrize('parent_folder_id', [None, PARENT_FOLDER_ID])
def test_post_add_template_folder_page(client_request, service_one, mocker, parent_folder_id):
    mock_create = mocker.patch('app.template_folder_api_client.create_template_folder')

    service_one['permissions'] += ['edit_folders']

    client_request.post(
        'main.add_template_folder',
        service_id=service_one['id'],
        template_folder_id=parent_folder_id,
        _data={'name': 'foo'},
        _expected_redirect=url_for(
            'main.choose_template',
            service_id=service_one['id'],
            template_folder_id=parent_folder_id,
            _external=True,
        )
    )

    mock_create.assert_called_once_with(service_one['id'], name='foo', parent_id=parent_folder_id)


@pytest.mark.parametrize(
    (
        'expected_title_tag,'
        'expected_page_title,'
        'expected_parent_link_args,'
        'extra_args,'
        'expected_nav_links,'
        'expected_items, '
        'expected_empty_message '
    ),
    [
        (
            'Templates – service one – GOV.UK Notify',
            'Templates',
            None,
            {},
            ['Text message', 'Email', 'Letter'],
            [
                'folder_one 2 folders',
                'folder_one / folder_one_one 1 template, 1 folder',
                'folder_one / folder_one_one / folder_one_one_one 1 template',
                'folder_one / folder_one_one / folder_one_one_one / sms_template_nested Text message template',
                'folder_one / folder_one_one / letter_template_nested Letter template',
                'folder_one / folder_one_two Empty',
                'folder_two Empty',
                'sms_template_one Text message template',
                'sms_template_two Text message template',
                'email_template_one Email template',
                'email_template_two Email template',
                'letter_template_one Letter template',
                'letter_template_two Letter template',
            ],
            None,
        ),
        (
            'Templates – service one – GOV.UK Notify',
            'Templates',
            None,
            {'template_type': 'sms'},
            ['All', 'Email', 'Letter'],
            [
                'folder_one 1 folder',
                'folder_one / folder_one_one 1 folder',
                'folder_one / folder_one_one / folder_one_one_one 1 template',
                'folder_one / folder_one_one / folder_one_one_one / sms_template_nested Text message template',
                'sms_template_one Text message template',
                'sms_template_two Text message template',
            ],
            None,
        ),
        (
            'folder_one – Templates – service one – GOV.UK Notify',
            'Templates / folder_one',
            {'template_type': 'all'},
            {'template_folder_id': PARENT_FOLDER_ID},
            ['Text message', 'Email', 'Letter'],
            [
                'folder_one_one 1 template, 1 folder',
                'folder_one_one / folder_one_one_one 1 template',
                'folder_one_one / folder_one_one_one / sms_template_nested Text message template',
                'folder_one_one / letter_template_nested Letter template',
                'folder_one_two Empty',
            ],
            None,
        ),
        (
            'folder_one – Templates – service one – GOV.UK Notify',
            'Templates / folder_one',
            {'template_type': 'sms'},
            {'template_type': 'sms', 'template_folder_id': PARENT_FOLDER_ID},
            ['All', 'Email', 'Letter'],
            [
                'folder_one_one 1 folder',
                'folder_one_one / folder_one_one_one 1 template',
                'folder_one_one / folder_one_one_one / sms_template_nested Text message template',
            ],
            None,
        ),
        (
            'folder_one – Templates – service one – GOV.UK Notify',
            'Templates / folder_one',
            {'template_type': 'email'},
            {'template_type': 'email', 'template_folder_id': PARENT_FOLDER_ID},
            ['All', 'Text message', 'Letter'],
            [],
            'There are no email templates in this folder',
        ),
        (
            'folder_one_one – folder_one – service one – GOV.UK Notify',
            'folder_one / folder_one_one',
            {'template_type': 'all', 'template_folder_id': PARENT_FOLDER_ID},
            {'template_folder_id': CHILD_FOLDER_ID},
            ['Text message', 'Email', 'Letter'],
            [
                'folder_one_one_one 1 template',
                'folder_one_one_one / sms_template_nested Text message template',
                'letter_template_nested Letter template',
            ],
            None,
        ),
        (
            'folder_one_one_one – folder_one_one – service one – GOV.UK Notify',
            'folder_one_one / folder_one_one_one',
            {'template_type': 'all', 'template_folder_id': CHILD_FOLDER_ID},
            {'template_folder_id': GRANDCHILD_FOLDER_ID},
            ['Text message', 'Email', 'Letter'],
            [
                'sms_template_nested Text message template',
            ],
            None,
        ),
        (
            'folder_two – Templates – service one – GOV.UK Notify',
            'Templates / folder_two',
            {'template_type': 'all'},
            {'template_folder_id': FOLDER_TWO_ID},
            ['Text message', 'Email', 'Letter'],
            [],
            'This folder is empty',
        ),
        (
            'folder_two – Templates – service one – GOV.UK Notify',
            'Templates / folder_two',
            {'template_type': 'sms'},
            {'template_folder_id': FOLDER_TWO_ID, 'template_type': 'sms'},
            ['All', 'Email', 'Letter'],
            [],
            'This folder is empty',
        ),
    ]
)
def test_should_show_templates_folder_page(
    client_request,
    mock_get_template_folders,
    mock_has_no_jobs,
    service_one,
    mocker,
    fake_uuid,
    expected_title_tag,
    expected_page_title,
    expected_parent_link_args,
    extra_args,
    expected_nav_links,
    expected_items,
    expected_empty_message,
):
    mock_get_template_folders.return_value = [
        _folder('folder_two', FOLDER_TWO_ID),
        _folder('folder_one', PARENT_FOLDER_ID),
        _folder('folder_one_two', parent=PARENT_FOLDER_ID),
        _folder('folder_one_one', CHILD_FOLDER_ID, parent=PARENT_FOLDER_ID),
        _folder('folder_one_one_one', GRANDCHILD_FOLDER_ID, parent=CHILD_FOLDER_ID),
    ]
    mock_get_service_templates = mocker.patch(
        'app.service_api_client.get_service_templates',
        return_value={'data': [
            _template('sms', 'sms_template_one'),
            _template('sms', 'sms_template_two'),
            _template('email', 'email_template_one'),
            _template('email', 'email_template_two'),
            _template('letter', 'letter_template_one'),
            _template('letter', 'letter_template_two'),
            _template('letter', 'letter_template_nested', parent=CHILD_FOLDER_ID),
            _template('sms', 'sms_template_nested', parent=GRANDCHILD_FOLDER_ID),
        ]}
    )

    service_one['permissions'] += ['letter', 'edit_folders']

    page = client_request.get(
        'main.choose_template',
        service_id=SERVICE_ONE_ID,
        _test_page_title=False,
        **extra_args
    )

    assert normalize_spaces(page.select_one('title').text) == expected_title_tag
    assert normalize_spaces(page.select_one('h1').text) == expected_page_title

    if expected_parent_link_args:
        assert len(page.select('h1 a')) == 1
        assert page.select_one('h1 a')['href'] == url_for(
            'main.choose_template',
            service_id=SERVICE_ONE_ID,
            **expected_parent_link_args
        )
    else:
        assert page.select_one('h1 a') is None

    links_in_page = page.select('.pill a')

    assert len(links_in_page) == len(expected_nav_links)

    for index, expected_link in enumerate(expected_nav_links):
        assert links_in_page[index].text.strip() == expected_link

    page_items = page.select('.template-list-item')
    assert len(page_items) == len(expected_items)

    for index, expected_item in enumerate(expected_items):
        assert normalize_spaces(page_items[index].text) == expected_item

    if expected_empty_message:
        assert normalize_spaces(page.select_one('.template-list-empty').text) == (
            expected_empty_message
        )
    else:
        assert not page.select('.template-list-empty')

    mock_get_service_templates.assert_called_once_with(SERVICE_ONE_ID)


@pytest.mark.parametrize("template_type", ["email", "sms"])
def test_add_template_by_type_should_redirect_to_add_service_template(
    client_request,
    service_one,
    template_type,
    mock_get_service_templates,
    mock_get_organisations_and_services_for_user,
):
    service_one['permissions'] += ['edit_folders']
    client_request.post(
        'main.add_template_by_type',
        service_id=SERVICE_ONE_ID,
        template_folder_id=PARENT_FOLDER_ID,
        _data={'template_type': template_type},
        _expected_redirect=url_for('main.add_service_template',
                                   service_id=SERVICE_ONE_ID,
                                   template_type=template_type,
                                   template_folder_id=PARENT_FOLDER_ID,
                                   _external=True),
    )


def test_add_template_by_type_should_redirect_to_view_template_for_letter(
        client_request,
        service_one,
        mock_get_service_templates,
        mock_get_organisations_and_services_for_user,
        fake_uuid,
        mock_create_service_template
):
    service_one['permissions'] += ['edit_folders']
    service_one['permissions'] += ['letter']
    client_request.post(
        'main.add_template_by_type',
        service_id=SERVICE_ONE_ID,
        template_folder_id=PARENT_FOLDER_ID,
        _data={'template_type': 'letter'},
        _expected_redirect=url_for('main.view_template',
                                   service_id=SERVICE_ONE_ID,
                                   template_id='Untitled',
                                   _external=True),
    )
    mock_create_service_template.assert_called_once_with('Untitled',
                                                         'letter',
                                                         'Body',
                                                         SERVICE_ONE_ID,
                                                         'Main heading',
                                                         'normal',
                                                         PARENT_FOLDER_ID)


def test_can_create_email_template_with_parent_folder(
        client_request,
        mock_create_service_template
):
    data = {
        'name': "new name",
        'subject': "Food incoming!",
        'template_content': "here's a burrito 🌯",
        'template_type': 'email',
        'service': SERVICE_ONE_ID,
        'process_type': 'normal',
        'parent_folder_id': PARENT_FOLDER_ID
    }
    client_request.post('.add_service_template',
                        service_id=SERVICE_ONE_ID,
                        template_type='email',
                        template_folder_id=PARENT_FOLDER_ID,
                        _data=data,
                        _expected_redirect=url_for("main.view_template",
                                                   service_id=SERVICE_ONE_ID,
                                                   template_id="new%20name",
                                                   _external=True)
                        )
    mock_create_service_template.assert_called_once_with(
        data['name'],
        data['template_type'],
        data['template_content'],
        SERVICE_ONE_ID,
        data['subject'],
        data['process_type'],
        data['parent_folder_id'])


def test_get_manage_folder_page(
    client_request,
    service_one,
    mock_get_template_folders,
):
    folder_id = str(uuid.uuid4())
    mock_get_template_folders.return_value = [
        {'id': folder_id, 'name': 'folder_two', 'parent_id': None},
    ]
    service_one['permissions'] += ['edit_folders']

    page = client_request.get(
        'main.manage_template_folder',
        service_id=service_one['id'],
        template_folder_id=folder_id,
        _test_page_title=False,
    )
    assert normalize_spaces(page.select_one('title').text) == (
        'folder_two – Templates – service one – GOV.UK Notify'
    )
    assert page.select_one('input[name=name]')['value'] == 'folder_two'
    delete_link = page.find('a', string="Delete this folder")
    expected_delete_url = "/services/{}/templates/folders/{}/delete".format(service_one['id'], folder_id)

    assert expected_delete_url in delete_link["href"]


def test_manage_folder_page_404s(client_request, service_one, mock_get_template_folders):
    service_one['permissions'] += ['edit_folders']
    client_request.get(
        'main.manage_template_folder',
        service_id=service_one['id'],
        template_folder_id=str(uuid.uuid4()),
        _expected_status=404,
    )


def test_get_manage_folder_page_no_permissions(client_request, service_one, mock_get_template_folders):
    folder_id = str(uuid.uuid4())

    client_request.get(
        'main.manage_template_folder',
        service_id=service_one['id'],
        template_folder_id=folder_id,
        _expected_status=403
    )


def test_rename_folder(client_request, service_one, mock_get_template_folders, mocker):
    mock_update = mocker.patch('app.template_folder_api_client.update_template_folder')
    folder_id = str(uuid.uuid4())
    mock_get_template_folders.return_value = [
        {'id': folder_id, 'name': 'folder_two', 'parent_id': None},
    ]
    service_one['permissions'] += ['edit_folders']

    client_request.post(
        'main.manage_template_folder',
        service_id=service_one['id'],
        template_folder_id=folder_id,
        _data={"name": "new beautiful name"},
        _expected_redirect=url_for("main.choose_template",
                                   service_id=service_one['id'],
                                   template_folder_id=folder_id,
                                   _external=True)
    )

    mock_update.assert_called_once_with(
        service_one['id'],
        folder_id,
        name="new beautiful name"
    )


def test_delete_template_folder_should_request_confirmation(
    client_request, service_one, mock_get_template_folders, mocker
):
    service_one['permissions'] += ['edit_folders']
    folder_id = str(uuid.uuid4())
    mock_get_template_folders.side_effect = [[
        {'id': folder_id, 'name': 'sacrifice', 'parent_id': None},
    ], []]
    mocker.patch(
        'app.models.service.Service.get_templates',
        return_value=[],
    )
    page = client_request.get(
        'main.delete_template_folder', service_id=service_one['id'],
        template_folder_id=folder_id,
        _test_page_title=False,
    )
    assert normalize_spaces(page.select('.banner-dangerous')[0].text) == (
        'Are you sure you want to delete the ‘sacrifice’ folder? '
        'Yes, delete'
    )

    assert page.select_one('input[name=name]')['value'] == 'sacrifice'

    assert len(page.select('form')) == 2
    assert len(page.select('button')) == 2

    assert 'action' not in page.select('form')[0]
    assert page.select('form button')[0].text == 'Yes, delete'

    assert page.select('form')[1]['action'] == url_for(
        'main.manage_template_folder',
        service_id=service_one['id'],
        template_folder_id=folder_id,
    )
    assert page.select('form button')[1].text == 'Save'


def test_delete_template_folder_should_detect_non_empty_folder_on_get(
    client_request, service_one, mock_get_template_folders, mocker
):
    service_one['permissions'] += ['edit_folders']
    folder_id = str(uuid.uuid4())
    template_id = str(uuid.uuid4())
    mock_get_template_folders.side_effect = [
        [{'id': folder_id, 'name': "can't touch me", 'parent_id': None}],
        []
    ]
    mocker.patch(
        'app.models.service.Service.get_templates',
        return_value=[{'id': template_id, 'name': 'template'}],
    )
    client_request.get(
        'main.delete_template_folder', service_id=service_one['id'],
        template_folder_id=folder_id,
        _expected_redirect=url_for(
            "main.choose_template",
            template_type="all",
            service_id=service_one['id'],
            template_folder_id=folder_id,
            _external=True
        ),
        _expected_status=302
    )


@pytest.mark.parametrize('parent_folder_id', (
    None,
    PARENT_FOLDER_ID,
))
def test_delete_folder(client_request, service_one, mock_get_template_folders, mocker, parent_folder_id):
    mock_delete = mocker.patch('app.template_folder_api_client.delete_template_folder')
    folder_id = str(uuid.uuid4())
    mock_get_template_folders.side_effect = [[
        {'id': folder_id, 'name': 'sacrifice', 'parent_id': parent_folder_id},
    ], []]
    mocker.patch(
        'app.models.service.Service.get_templates',
        return_value=[],
    )
    service_one['permissions'] += ['edit_folders']

    client_request.post(
        'main.delete_template_folder',
        service_id=service_one['id'],
        template_folder_id=folder_id,
        _expected_redirect=url_for(
            "main.choose_template",
            service_id=service_one['id'],
            template_folder_id=parent_folder_id,
            _external=True,
        )
    )

    mock_delete.assert_called_once_with(service_one['id'], folder_id)
