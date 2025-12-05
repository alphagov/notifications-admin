import uuid

import pytest

from app.notify_client.template_email_file_client import TemplateEmailFileClient


@pytest.mark.parametrize(
    "data",
    [
        {
            "file_id": str(uuid.uuid4()),
            "filename": "test.pdf",
            "created_by": str(uuid.uuid4()),
            "retention_period": 90,
            "validate_users_email": True,
        },
        {
            "file_id": str(uuid.uuid4()),
            "filename": "test.pdf",
            "created_by": str(uuid.uuid4()),
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
    data["created_by_id"] = data.pop("created_by")
    if "validate_users_email" not in data.keys():
        data["validate_users_email"] = False
    mock_post.assert_called_once_with(expected_url, data=data)
