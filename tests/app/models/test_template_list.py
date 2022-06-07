import uuid

import pytest

from app.models.service import Service
from app.models.template_list import TemplateList
from app.models.user import User

INV_PARENT_FOLDER_ID = '7e979e79-d970-43a5-ac69-b625a8d147b0'
INV_CHILD_1_FOLDER_ID = '92ee1ee0-e4ee-4dcc-b1a7-a5da9ebcfa2b'
VIS_PARENT_FOLDER_ID = 'bbbb222b-2b22-2b22-222b-b222b22b2222'
INV_CHILD_2_FOLDER_ID = 'fafe723f-1d39-4a10-865f-e551e03d8886'


@pytest.fixture
def mock_get_hierarchy_of_folders(
    mock_get_template_folders,
    active_user_with_permissions
):
    mock_get_template_folders.return_value = [
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


def test_template_list_yields_folders_visible_to_user(
    mock_get_hierarchy_of_folders,
    mock_get_service_templates,
    service_one,
    active_user_with_permissions,
):
    service = Service(service_one)
    user = User(active_user_with_permissions)

    result_folder_names = tuple(
        result.name for result in
        TemplateList(service=service, user=user)
        if result.is_folder
    )

    assert result_folder_names == (
        ["Parent 1 - invisible", "1's Visible child"],
        ["Parent 1 - invisible", ["1's Invisible child", "1's Visible grandchild"]],
        "Parent 2 - visible",
        "2's Visible child",
        ["2's Invisible child", "2's Visible grandchild"],
    )


def test_template_list_yields_all_folders_without_user(
    mock_get_hierarchy_of_folders,
    mock_get_service_templates,
    service_one,
):
    service = Service(service_one)

    result_folder_names = tuple(
        result.name for result in
        TemplateList(service=service)
        if result.is_folder
    )

    assert result_folder_names == (
        "Invisible folder",
        "Parent 1 - invisible",
        "1's Invisible child",
        "1's Visible grandchild",
        "1's Visible child",
        "Parent 2 - visible",
        "2's Invisible child",
        "2's Visible grandchild",
        "2's Visible child",
    )
