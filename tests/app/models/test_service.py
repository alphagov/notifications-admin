import uuid

from app.models.service import Service
from app.models.user import User

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
            'users_with_permission': [active_user_with_permissions['id']],
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
            'users_with_permission': [active_user_with_permissions['id']],
        },
        {
            'name': "Parent 2 - visible",
            'id': VIS_PARENT_FOLDER_ID,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions['id']],
        },
        {
            'name': "2's Visible child",
            'id': str(uuid.uuid4()),
            'parent_id': VIS_PARENT_FOLDER_ID,
            'users_with_permission': [active_user_with_permissions['id']],
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
            'users_with_permission': [active_user_with_permissions['id']],
        },
    ]


def test_get_user_template_folders_only_returns_folders_visible_to_user(
    app_,
    mock_get_template_folders,
    service_one,
    active_user_with_permissions,
    mocker
):
    mock_get_template_folders.return_value = _get_all_folders(active_user_with_permissions)
    service = Service(service_one)
    result = service.get_user_template_folders(User(active_user_with_permissions))
    assert result == [
        {
            'name': "Parent 1 - invisible / 1's Visible child",
            'id': mocker.ANY,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions['id']],
        },
        {
            'name': "Parent 1 - invisible / 1's Invisible child / 1's Visible grandchild",
            'id': mocker.ANY,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions['id']],
        },
        {
            'name': "2's Visible child",
            'id': mocker.ANY,
            'parent_id': VIS_PARENT_FOLDER_ID,
            'users_with_permission': [active_user_with_permissions['id']],
        },
        {
            'name': "2's Invisible child / 2's Visible grandchild",
            'id': mocker.ANY,
            'parent_id': VIS_PARENT_FOLDER_ID,
            'users_with_permission': [active_user_with_permissions['id']],
        },
        {
            'name': "Parent 2 - visible",
            'id': VIS_PARENT_FOLDER_ID,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions['id']],
        },
    ]


def test_get_template_folders_shows_user_folders_when_user_id_passed_in(
    app_,
    mock_get_template_folders,
    service_one,
    active_user_with_permissions,
    mocker
):
    mock_get_template_folders.return_value = _get_all_folders(active_user_with_permissions)
    service = Service(service_one)
    result = service.get_template_folders(user=User(active_user_with_permissions))
    assert result == [
        {
            'name': "Parent 1 - invisible / 1's Visible child",
            'id': mocker.ANY,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions['id']]
        },
        {
            'name': "Parent 1 - invisible / 1's Invisible child / 1's Visible grandchild",
            'id': mocker.ANY,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions['id']]
        },
        {
            'name': "Parent 2 - visible",
            'id': VIS_PARENT_FOLDER_ID,
            'parent_id': None,
            'users_with_permission': [active_user_with_permissions['id']]
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
            'users_with_permission': [active_user_with_permissions['id']],
        }
    ]
