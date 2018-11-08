import uuid

import pytest
from flask import url_for

from tests.conftest import SERVICE_ONE_ID, normalize_spaces

PARENT_FOLDER_ID = '7e979e79-d970-43a5-ac69-b625a8d147b0'
CHILD_FOLDER_ID = '92ee1ee0-e4ee-4dcc-b1a7-a5da9ebcfa2b'


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
    'expected_page_title, extra_args, expected_nav_links, expected_links',
    [
        (
            'Templates',
            {},
            ['Text message', 'Email', 'Letter'],
            [
                'folder_one',
                'folder_two',
                'sms_template_one',
                'sms_template_two',
                'email_template_one',
                'email_template_two',
                'letter_template_one',
                'letter_template_two',
            ]
        ),
        (
            'Templates',
            {'template_type': 'sms'},
            ['All', 'Email', 'Letter'],
            ['folder_one', 'folder_two', 'sms_template_one', 'sms_template_two'],
        ),
        (
            'Templates / folder_one',
            {'template_type': 'sms', 'template_folder_id': PARENT_FOLDER_ID},
            ['All', 'Email', 'Letter'],
            ['folder_one_one', 'folder_one_two'],
        ),
        (
            'Templates / folder_one / folder_one_one',
            {'template_folder_id': CHILD_FOLDER_ID},
            ['Text message', 'Email', 'Letter'],
            [],
        ),
    ]
)
def test_should_show_templates_folder_page(
    client_request,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_has_no_jobs,
    service_one,
    mocker,
    fake_uuid,
    expected_page_title,
    extra_args,
    expected_nav_links,
    expected_links,
):

    mock_get_template_folders.return_value = [
        {'id': PARENT_FOLDER_ID, 'name': 'folder_one', 'parent_id': None},
        {'id': str(uuid.uuid4()), 'name': 'folder_two', 'parent_id': None},
        {'id': CHILD_FOLDER_ID, 'name': 'folder_one_one', 'parent_id': PARENT_FOLDER_ID},
        {'id': str(uuid.uuid4()), 'name': 'folder_one_two', 'parent_id': PARENT_FOLDER_ID},
    ]

    service_one['permissions'] += ['letter', 'edit_folders']

    page = client_request.get(
        'main.choose_template',
        service_id=SERVICE_ONE_ID,
        **extra_args
    )

    assert normalize_spaces(page.select_one('h1').text) == expected_page_title

    links_in_page = page.select('.pill a')

    assert len(links_in_page) == len(expected_nav_links)

    for index, expected_link in enumerate(expected_nav_links):
        assert links_in_page[index].text.strip() == expected_link

    page_links = page.select('.message-name a')

    assert len(page_links) == len(expected_links)

    for index, expected_link in enumerate(expected_links):
        assert page_links[index].text.strip() == expected_link

    mock_get_service_templates.assert_called_once_with(SERVICE_ONE_ID)
