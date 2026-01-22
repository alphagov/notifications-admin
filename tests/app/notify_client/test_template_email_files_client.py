import uuid
from unittest.mock import call

import pytest

from app.notify_client.template_email_file_client import TemplateEmailFileClient


@pytest.mark.parametrize(
    "data",
    [
        {
            "file_id": str(uuid.uuid4()),
            "filename": "test.pdf",
            "created_by_id": str(uuid.uuid4()),
            "retention_period": 90,
            "validate_users_email": True,
        },
        {
            "file_id": str(uuid.uuid4()),
            "filename": "test.pdf",
            "created_by_id": str(uuid.uuid4()),
            "retention_period": 90,
        },
    ],
)
def test_create_file_calls_endpoint_with_correct_data(mocker, data):
    template_id = str(uuid.uuid4())
    service_id = str(uuid.uuid4())
    expected_url = f"/service/{service_id}/templates/{template_id}/template_email_files"
    mock_post = mocker.patch("app.notify_client.template_email_file_client.TemplateEmailFileClient.post")
    client = TemplateEmailFileClient(mocker.MagicMock())
    client.create_file(**data, service_id=service_id, template_id=template_id)
    data["id"] = data.pop("file_id")
    if "validate_users_email" not in data.keys():
        data["validate_users_email"] = False
    mock_post.assert_called_once_with(expected_url, data=data)


def test_update_file_calls_endpoint_with_correct_data(mocker):
    update_data = {
        "filename": "new_example.pdf",
        "link_text": "click this new link!",
        "retention_period": 30,
        "validate_users_email": False,
    }
    template_id = str(uuid.uuid4())
    service_id = str(uuid.uuid4())
    template_email_file_id = str(uuid.uuid4())
    mock_post = mocker.patch("app.notify_client.template_email_file_client.TemplateEmailFileClient.update_file")
    client = TemplateEmailFileClient(mocker.MagicMock())
    client.update_file(service_id=service_id, template_id=template_id, template_email_file_id=template_email_file_id,
                       data=update_data)
    assert mock_post.call_args_list == [
        call(service_id=service_id,
             template_id=template_id,
             template_email_file_id=template_email_file_id,
             data={
                 'filename': 'new_example.pdf',
                 'link_text': 'click this new link!',
                 'retention_period': 30,
                 'validate_users_email': False}
             )
    ]
