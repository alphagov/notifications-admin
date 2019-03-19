import uuid

from app.models.service import Service
from tests.conftest import _template

INV_PARENT_FOLDER_ID = '7e979e79-d970-43a5-ac69-b625a8d147b0'
INV_CHILD_1_FOLDER_ID = '92ee1ee0-e4ee-4dcc-b1a7-a5da9ebcfa2b'
VIS_PARENT_FOLDER_ID = 'bbbb222b-2b22-2b22-222b-b222b22b2222'
INV_CHILD_2_FOLDER_ID = 'fafe723f-1d39-4a10-865f-e551e03d8886'


def _get_all_folders(active_user_with_permissions):
    return [
        {
            'name': "Invisible folder",
            'id': str(uuid.uuid4()),
            'parent_id': None,
            'users_with_permission': []
        },
        {
            'name': "Parent 1 - invisible",
            'id': INV_PARENT_FOLDER_ID,
            'parent_id': None,
            'users_with_permission': []
        },
        {
            'name': "1's Visible child",
            'id': str(uuid.uuid4()),
            'parent_id': INV_PARENT_FOLDER_ID,
            'users_with_permission': [active_user_with_permissions.id]
        },
        {
            'name': "1's Invisible child",
            'id': INV_CHILD_1_FOLDER_ID,
            'parent_id': INV_PARENT_FOLDER_ID,
            'users_with_permission': []
        },
        {
            'name': "1's Visible grandchild",
            'id': str(uuid.uuid4()),
            'parent_id': INV_CHILD_1_FOLDER_ID,
            'users_with_permission': [active_user_with_permissions.id]
        },
        {
            'name': "Parent 2 - visible",
            'id': VIS_PARENT_FOLDER_ID,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions.id]
        },
        {
            'name': "2's Visible child",
            'id': str(uuid.uuid4()),
            'parent_id': VIS_PARENT_FOLDER_ID,
            'users_with_permission': [active_user_with_permissions.id]
        },
        {
            'name': "2's Invisible child",
            'id': INV_CHILD_2_FOLDER_ID,
            'parent_id': VIS_PARENT_FOLDER_ID,
            'users_with_permission': []
        },
        {
            'name': "2's Visible grandchild",
            'id': str(uuid.uuid4()),
            'parent_id': INV_CHILD_2_FOLDER_ID,
            'users_with_permission': [active_user_with_permissions.id]
        },
    ]


def test_get_user_template_folders_only_returns_folders_visible_to_user(
    mock_get_template_folders,
    service_one,
    active_user_with_permissions,
    mocker
):
    mock_get_template_folders.return_value = _get_all_folders(active_user_with_permissions)
    service_one['permissions'] = ['edit_folder_permissions']
    service = Service(service_one)
    result = service.get_user_template_folders(active_user_with_permissions.id)
    assert result == [
        {
            'name': "Parent 1 - invisible / 1's Visible child",
            'id': mocker.ANY,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions.id]
        },
        {
            'name': "Parent 1 - invisible / 1's Invisible child / 1's Visible grandchild",
            'id': mocker.ANY,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions.id]
        },
        {
            'name': "2's Visible child",
            'id': mocker.ANY,
            'parent_id': VIS_PARENT_FOLDER_ID,
            'users_with_permission': [active_user_with_permissions.id]
        },
        {
            'name': "2's Invisible child / 2's Visible grandchild",
            'id': mocker.ANY,
            'parent_id': VIS_PARENT_FOLDER_ID,
            'users_with_permission': [active_user_with_permissions.id]
        },
        {
            'name': "Parent 2 - visible",
            'id': VIS_PARENT_FOLDER_ID,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions.id]
        },
    ]


def test_get_template_folders_shows_user_folders_when_user_id_passed_in(
    mock_get_template_folders,
    service_one,
    active_user_with_permissions,
    mocker
):
    mock_get_template_folders.return_value = _get_all_folders(active_user_with_permissions)
    service_one['permissions'] = ['edit_folder_permissions']
    service = Service(service_one)
    result = service.get_template_folders(user_id=active_user_with_permissions.id)
    assert result == [
        {
            'name': "Parent 1 - invisible / 1's Visible child",
            'id': mocker.ANY,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions.id]
        },
        {
            'name': "Parent 1 - invisible / 1's Invisible child / 1's Visible grandchild",
            'id': mocker.ANY,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions.id]
        },
        {
            'name': "Parent 2 - visible",
            'id': VIS_PARENT_FOLDER_ID,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions.id]
        },
    ]


def test_get_template_folders_shows_all_folders_when_user_id_not_passed_in(
    mock_get_template_folders,
    service_one,
    active_user_with_permissions,
    mocker
):
    mock_get_template_folders.return_value = _get_all_folders(active_user_with_permissions)
    service = Service(service_one)
    result = service.get_template_folders()
    assert result == [
        {
            'name': "Invisible folder",
            'id': mocker.ANY,
            'parent_id': None,
            'users_with_permission': []
        },
        {
            'name': "Parent 1 - invisible",
            'id': INV_PARENT_FOLDER_ID,
            'parent_id': None,
            'users_with_permission': []
        },
        {
            'name': "Parent 2 - visible",
            'id': VIS_PARENT_FOLDER_ID,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions.id]
        }
    ]


def test_get_user_templates_across_folders(
    mock_get_template_folders,
    service_one,
    active_user_with_permissions,
    mocker
):
    all_templates = {'data': [
        _template('sms', 'sms_template_one', parent=INV_CHILD_1_FOLDER_ID),
        _template('sms', 'sms_template_two'),
        _template('email', 'email_template_one', parent=VIS_PARENT_FOLDER_ID),
        _template('letter', 'letter_template_one')
    ]}
    mock_get_template_folders.return_value = _get_all_folders(active_user_with_permissions)
    mocker.patch('app.service_api_client.get_service_templates', return_value=all_templates)
    service_one['permissions'] = ['edit_folder_permissions', 'letter', 'email', 'sms']
    service = Service(service_one)
    result = service.get_user_templates_across_folders(active_user_with_permissions.id)
    assert result == [
        {'folder': None, 'id': mocker.ANY,
            'name': 'sms_template_two', 'template_type': 'sms'},
        {'folder': None, 'id': mocker.ANY,
            'name': 'letter_template_one', 'template_type': 'letter'},
        {'folder': 'bbbb222b-2b22-2b22-222b-b222b22b2222', 'id': mocker.ANY,
            'name': 'email_template_one', 'template_type': 'email'}
    ]


def test_get_user_templates_across_folders_sms_only(
    mock_get_template_folders,
    service_one,
    active_user_with_permissions,
    mocker
):
    all_templates = {'data': [
        _template('sms', 'sms_template_one', parent=INV_CHILD_1_FOLDER_ID),
        _template('sms', 'sms_template_two'),
        _template('email', 'email_template_one', parent=VIS_PARENT_FOLDER_ID),
        _template('letter', 'letter_template_one')
    ]}
    mock_get_template_folders.return_value = _get_all_folders(active_user_with_permissions)
    mocker.patch('app.service_api_client.get_service_templates', return_value=all_templates)
    service_one['permissions'] = ['edit_folder_permissions', 'letter', 'email', 'sms']
    service = Service(service_one)
    result = service.get_user_templates_across_folders(active_user_with_permissions.id, template_type='sms')
    assert result == [{'folder': None, 'id': mocker.ANY, 'name': 'sms_template_two', 'template_type': 'sms'}]
