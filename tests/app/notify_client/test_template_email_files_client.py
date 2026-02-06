import uuid

import pytest

from app.notify_client.template_email_file_client import TemplateEmailFileClient
from tests.utils import RedisClientMock


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
        data["validate_users_email"] = True
    mock_post.assert_called_once_with(expected_url, data=data)


def test_update_file_calls_endpoint_with_correct_data(mocker):
    template_id = str(uuid.uuid4())
    service_id = str(uuid.uuid4())
    file_id = str(uuid.uuid4())
    data = {"retention_period": 90, "validate_users_email": True, "link_text": "Click me"}
    expected_url = f"/service/{service_id}/templates/{template_id}/template_email_files/{file_id}"
    mock_post = mocker.patch("app.notify_client.template_email_file_client.TemplateEmailFileClient.post")
    mock_redis_delete_by_pattern = mocker.patch(
        "app.extensions.RedisClient.delete_by_pattern", new_callable=RedisClientMock
    )
    client = TemplateEmailFileClient(mocker.MagicMock())
    client.update_file(service_id=service_id, template_id=template_id, file_id=file_id, **data)
    mock_post.assert_called_once_with(expected_url, data=data)
    mock_redis_delete_by_pattern.assert_called_with_args(f"service-{service_id}-template-{template_id}*")
