from unittest.mock import Mock, call
from uuid import uuid4

import pytest

from app import invite_api_client, service_api_client, user_api_client
from app.notify_client.service_api_client import ServiceAPIClient
from tests.conftest import SERVICE_ONE_ID
from tests.utils import RedisClientMock

FAKE_TEMPLATE_ID = uuid4()


def test_client_posts_archived_true_when_deleting_template(mocker):
    mocker.patch("app.notify_client.current_user", id="1")
    mock_redis_delete_by_pattern = mocker.patch(
        "app.extensions.RedisClient.delete_by_pattern", new_callable=RedisClientMock
    )
    expected_data = {"archived": True, "created_by": "1"}
    expected_url = f"/service/{SERVICE_ONE_ID}/template/{FAKE_TEMPLATE_ID}"

    client = ServiceAPIClient(mocker.MagicMock())
    mock_post = mocker.patch("app.notify_client.service_api_client.ServiceAPIClient.post")
    mocker.patch(
        "app.notify_client.service_api_client.ServiceAPIClient.get",
        return_value={"data": {"id": str(FAKE_TEMPLATE_ID)}},
    )

    client.delete_service_template(SERVICE_ONE_ID, FAKE_TEMPLATE_ID)
    mock_post.assert_called_once_with(expected_url, data=expected_data)
    mock_redis_delete_by_pattern.assert_called_with_args(f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}*")


def test_client_gets_service(mocker):
    client = ServiceAPIClient(mocker.MagicMock())
    mock_get = mocker.patch.object(client, "get", return_value={})

    client.get_service("foo")
    mock_get.assert_called_once_with("/service/foo")


@pytest.mark.parametrize("limit_days", [None, 30])
def test_client_gets_service_statistics(mocker, limit_days):
    client = ServiceAPIClient(mocker.MagicMock())
    mock_get = mocker.patch.object(client, "get", return_value={"data": {"a": "b"}})

    ret = client.get_service_statistics("foo", limit_days)

    assert ret == {"a": "b"}
    mock_get.assert_called_once_with("/service/foo/statistics", params={"limit_days": limit_days})


def test_client_only_updates_allowed_attributes(mocker):
    mocker.patch("app.notify_client.current_user", id="1")
    with pytest.raises(TypeError) as error:
        ServiceAPIClient(mocker.MagicMock()).update_service("service_id", foo="bar")
    assert str(error.value) == "Not allowed to update service attributes: foo"


def test_client_creates_service_with_correct_data(
    mocker,
    fake_uuid,
):
    client = ServiceAPIClient(mocker.MagicMock())
    mock_post = mocker.patch.object(client, "post", return_value={"data": {"id": None}})
    mocker.patch("app.notify_client.current_user", id="123")

    client.create_service(
        "My first service",
        "central_government",
        1,
        1,
        1,
        True,
        fake_uuid,
    )
    mock_post.assert_called_once_with(
        "/service",
        {
            # Autogenerated arguments
            "created_by": "123",
            "active": True,
            # ‘service_name’ argument is coerced to ‘name’
            "name": "My first service",
            # The rest pass through with the same names
            "organisation_type": "central_government",
            "email_message_limit": 1,
            "sms_message_limit": 1,
            "letter_message_limit": 1,
            "restricted": True,
            "user_id": fake_uuid,
        },
    )


def test_get_precompiled_template(mocker):
    mock_redis_set = mocker.patch("app.extensions.RedisClient.set")

    client = ServiceAPIClient(mocker.MagicMock())
    mock_get = mocker.patch.object(client, "get", return_value={"data": "foo"})

    client.get_precompiled_template(SERVICE_ONE_ID)
    mock_get.assert_called_once_with(f"/service/{SERVICE_ONE_ID}/template/precompiled")
    mock_redis_set.assert_called_once_with(
        f"service-{SERVICE_ONE_ID}-template-precompiled",
        '{"data": "foo"}',
        ex=2_419_200,
    )


@pytest.mark.parametrize(
    "template_data, extra_args, expected_count",
    (
        (
            [],
            {},
            0,
        ),
        (
            [],
            {"template_type": "email"},
            0,
        ),
        (
            [
                {"template_type": "email"},
                {"template_type": "sms"},
            ],
            {},
            2,
        ),
        (
            [
                {"template_type": "email"},
                {"template_type": "sms"},
            ],
            {"template_type": "email"},
            1,
        ),
        (
            [
                {"template_type": "email"},
                {"template_type": "sms"},
            ],
            {"template_type": "letter"},
            0,
        ),
    ),
)
def test_client_returns_count_of_service_templates(
    notify_admin,
    mocker,
    template_data,
    extra_args,
    expected_count,
):
    mocker.patch("app.service_api_client.get_service_templates", return_value={"data": template_data})

    assert service_api_client.count_service_templates(SERVICE_ONE_ID, **extra_args) == expected_count


@pytest.mark.parametrize(
    (
        "method,"
        "extra_args,"
        "expected_cache_get_calls,"
        "cache_value,"
        "expected_api_calls,"
        "expected_cache_set_calls,"
        "expected_return_value,"
    ),
    [
        (
            "get_service",
            [SERVICE_ONE_ID],
            [call(f"service-{SERVICE_ONE_ID}")],
            b'{"data_from": "cache"}',
            [],
            [],
            {"data_from": "cache"},
        ),
        (
            "get_service",
            [SERVICE_ONE_ID],
            [call(f"service-{SERVICE_ONE_ID}")],
            None,
            [call(f"/service/{SERVICE_ONE_ID}")],
            [
                call(
                    f"service-{SERVICE_ONE_ID}",
                    '{"data_from": "api"}',
                    ex=2_419_200,
                )
            ],
            {"data_from": "api"},
        ),
        (
            "get_service_template",
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID],
            [call(f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}-version-None")],
            b'{"data_from": "cache"}',
            [],
            [],
            {"data_from": "cache"},
        ),
        (
            "get_service_template",
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID],
            [
                call(f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}-version-None"),
            ],
            None,
            [call(f"/service/{SERVICE_ONE_ID}/template/{FAKE_TEMPLATE_ID}")],
            [
                call(
                    f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}-version-None",
                    '{"data_from": "api"}',
                    ex=2_419_200,
                ),
            ],
            {"data_from": "api"},
        ),
        (
            "get_service_template",
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID, 1],
            [call(f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}-version-1")],
            b'{"data_from": "cache"}',
            [],
            [],
            {"data_from": "cache"},
        ),
        (
            "get_service_template",
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID, 1],
            [
                call(f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}-version-1"),
            ],
            None,
            [call(f"/service/{SERVICE_ONE_ID}/template/{FAKE_TEMPLATE_ID}/version/1")],
            [
                call(
                    f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}-version-1",
                    '{"data_from": "api"}',
                    ex=2_419_200,
                ),
            ],
            {"data_from": "api"},
        ),
        (
            "get_service_templates",
            [SERVICE_ONE_ID],
            [call(f"service-{SERVICE_ONE_ID}-templates")],
            b'{"data_from": "cache"}',
            [],
            [],
            {"data_from": "cache"},
        ),
        (
            "get_service_templates",
            [SERVICE_ONE_ID],
            [call(f"service-{SERVICE_ONE_ID}-templates")],
            None,
            [call(f"/service/{SERVICE_ONE_ID}/template?detailed=False")],
            [
                call(
                    f"service-{SERVICE_ONE_ID}-templates",
                    '{"data_from": "api"}',
                    ex=2_419_200,
                )
            ],
            {"data_from": "api"},
        ),
        (
            "get_service_template_versions",
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID],
            [call(f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}-versions")],
            b'{"data_from": "cache"}',
            [],
            [],
            {"data_from": "cache"},
        ),
        (
            "get_service_template_versions",
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID],
            [
                call(f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}-versions"),
            ],
            None,
            [call(f"/service/{SERVICE_ONE_ID}/template/{FAKE_TEMPLATE_ID}/versions")],
            [
                call(
                    f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}-versions",
                    '{"data_from": "api"}',
                    ex=2_419_200,
                ),
            ],
            {"data_from": "api"},
        ),
        (
            "get_returned_letter_summary",
            [SERVICE_ONE_ID],
            [call(f"service-{SERVICE_ONE_ID}-returned-letters-summary")],
            None,
            [call(f"service/{SERVICE_ONE_ID}/returned-letter-summary")],
            [
                call(
                    f"service-{SERVICE_ONE_ID}-returned-letters-summary",
                    '{"data_from": "api"}',
                    ex=2_419_200,
                )
            ],
            {"data_from": "api"},
        ),
        (
            "get_returned_letter_statistics",
            [SERVICE_ONE_ID],
            [call(f"service-{SERVICE_ONE_ID}-returned-letters-statistics")],
            None,
            [call(f"service/{SERVICE_ONE_ID}/returned-letter-statistics")],
            [
                call(
                    f"service-{SERVICE_ONE_ID}-returned-letters-statistics",
                    '{"data_from": "api"}',
                    ex=2_419_200,
                )
            ],
            {"data_from": "api"},
        ),
    ],
)
def test_returns_value_from_cache(
    mocker,
    notify_admin,
    method,
    extra_args,
    expected_cache_get_calls,
    cache_value,
    expected_return_value,
    expected_api_calls,
    expected_cache_set_calls,
):
    mock_redis_get = mocker.patch(
        "app.extensions.RedisClient.get",
        return_value=cache_value,
    )
    mock_api_get = mocker.patch(
        "app.notify_client.NotifyAdminAPIClient.get",
        return_value={"data_from": "api"},
    )
    mock_redis_set = mocker.patch(
        "app.extensions.RedisClient.set",
    )

    assert getattr(service_api_client, method)(*extra_args) == expected_return_value

    assert mock_redis_get.call_args_list == expected_cache_get_calls
    assert mock_api_get.call_args_list == expected_api_calls
    assert mock_redis_set.call_args_list == expected_cache_set_calls


# feeding LocalProxys that need an app context into pytest's parametrization system
# leads to bad things
_clients_by_name = {
    "user": user_api_client,
    "service": service_api_client,
    "invite": invite_api_client,
}


@pytest.mark.parametrize(
    "client_name, method, extra_args, extra_kwargs",
    [
        ("service", "update_service", [SERVICE_ONE_ID], {"name": "foo"}),
        ("service", "archive_service", [SERVICE_ONE_ID, []], {}),
        ("service", "remove_user_from_service", [SERVICE_ONE_ID, ""], {}),
        ("service", "update_guest_list", [SERVICE_ONE_ID, {}], {}),
        ("service", "create_service_callback_api", [SERVICE_ONE_ID] + [""] * 4, {}),
        ("service", "update_service_inbound_api", [SERVICE_ONE_ID] + [""] * 5, {}),
        ("service", "add_reply_to_email_address", [SERVICE_ONE_ID, ""], {}),
        ("service", "update_reply_to_email_address", [SERVICE_ONE_ID] + [""] * 2, {}),
        ("service", "delete_reply_to_email_address", [SERVICE_ONE_ID, ""], {}),
        ("service", "add_letter_contact", [SERVICE_ONE_ID, ""], {}),
        ("service", "update_letter_contact", [SERVICE_ONE_ID] + [""] * 2, {}),
        ("service", "delete_letter_contact", [SERVICE_ONE_ID, ""], {}),
        ("service", "add_sms_sender", [SERVICE_ONE_ID, ""], {}),
        ("service", "update_sms_sender", [SERVICE_ONE_ID] + [""] * 2, {}),
        ("service", "delete_sms_sender", [SERVICE_ONE_ID, ""], {}),
        ("service", "update_delivery_status_callback_api", [SERVICE_ONE_ID] + [""] * 5, {}),
        ("service", "update_returned_letters_callback_api", [SERVICE_ONE_ID] + [""] * 5, {}),
        ("user", "add_user_to_service", [SERVICE_ONE_ID, uuid4(), [], []], {}),
        ("invite", "accept_invite", [SERVICE_ONE_ID, uuid4()], {}),
    ],
)
def test_deletes_service_cache(
    notify_admin,
    mocker,
    client_name,
    method,
    extra_args,
    extra_kwargs,
):
    mocker.patch("app.notify_client.current_user", id="1")
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)
    mock_request = mocker.patch("notifications_python_client.base.BaseAPIClient.request")

    getattr(_clients_by_name[client_name], method)(*extra_args, **extra_kwargs)

    mock_redis_delete.assert_called_with_subset_of_args(f"service-{SERVICE_ONE_ID}")
    assert len(mock_request.call_args_list) == 1


@pytest.mark.parametrize(
    "method, extra_args, extra_kwargs, expected_cache_deletes, expected_cache_deletes_by_pattern",
    [
        (
            "create_service_template",
            [],
            {
                "name": "name",
                "type_": "type_",
                "content": "content",
                "service_id": SERVICE_ONE_ID,
            },
            [f"service-{SERVICE_ONE_ID}-templates"],
            [],
        ),
        (
            "update_service_template",
            [],
            {
                "name": "foo",
                "content": "bar",
                "service_id": SERVICE_ONE_ID,
                "template_id": FAKE_TEMPLATE_ID,
            },
            [f"service-{SERVICE_ONE_ID}-templates"],
            [f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}*"],
        ),
        (
            "redact_service_template",
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID],
            {},
            [f"service-{SERVICE_ONE_ID}-templates"],
            [f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}*"],
        ),
        (
            "update_service_template_sender",
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID, "foo"],
            {},
            [f"service-{SERVICE_ONE_ID}-templates"],
            [f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}*"],
        ),
        (
            "delete_service_template",
            [SERVICE_ONE_ID, FAKE_TEMPLATE_ID],
            {},
            [f"service-{SERVICE_ONE_ID}-templates"],
            [f"service-{SERVICE_ONE_ID}-template-{FAKE_TEMPLATE_ID}*"],
        ),
        (
            "archive_service",
            [SERVICE_ONE_ID, []],
            {},
            [f"service-{SERVICE_ONE_ID}"],
            [f"service-{SERVICE_ONE_ID}-template*"],
        ),
    ],
)
def test_deletes_caches_when_modifying_templates(
    notify_admin,
    mocker,
    method,
    extra_args,
    extra_kwargs,
    expected_cache_deletes,
    expected_cache_deletes_by_pattern,
):
    mocker.patch("app.notify_client.current_user", id="1")
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)
    mock_redis_delete_by_pattern = mocker.patch(
        "app.extensions.RedisClient.delete_by_pattern", new_callable=RedisClientMock
    )
    mock_request = mocker.patch("notifications_python_client.base.BaseAPIClient.request")

    getattr(service_api_client, method)(*extra_args, **extra_kwargs)

    assert len(mock_request.call_args_list) == 1

    mock_redis_delete.assert_called_with_args(*expected_cache_deletes)
    mock_redis_delete_by_pattern.assert_called_with_args(*expected_cache_deletes_by_pattern)


def test_deletes_cached_users_when_archiving_service(
    notify_admin,
    mock_get_service_templates,
    mocker,
):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)
    mock_redis_delete_by_pattern = mocker.patch(
        "app.extensions.RedisClient.delete_by_pattern", new_callable=RedisClientMock
    )

    mocker.patch("notifications_python_client.base.BaseAPIClient.request", return_value={"data": ""})

    service_api_client.archive_service(SERVICE_ONE_ID, ["my-user-id1", "my-user-id2"])

    mock_redis_delete.assert_called_with_subset_of_args("user-my-user-id1", "user-my-user-id2")
    mock_redis_delete_by_pattern.assert_called_with_args(f"service-{SERVICE_ONE_ID}-template*")


def test_client_gets_guest_list(mocker):
    client = ServiceAPIClient(mocker.MagicMock())
    mock_get = mocker.patch.object(client, "get", return_value=["a", "b", "c"])

    response = client.get_guest_list("foo")

    assert response == ["a", "b", "c"]
    mock_get.assert_called_once_with(
        "/service/foo/guest-list",
    )


def test_client_updates_guest_list(mocker):
    client = ServiceAPIClient(mocker.MagicMock())
    mock_put = mocker.patch.object(client, "put")

    client.update_guest_list("foo", data=["a", "b", "c"])

    mock_put.assert_called_once_with(
        "/service/foo/guest-list",
        data=["a", "b", "c"],
    )


def test_client_deletes_service_template_cache_when_service_is_updated(notify_admin, mock_get_user, mocker):
    mocker.patch("app.notify_client.current_user", id="1")
    mocker.patch("notifications_python_client.base.BaseAPIClient.request")
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)
    mock_redis_delete_by_pattern = mocker.patch(
        "app.extensions.RedisClient.delete_by_pattern", new_callable=RedisClientMock
    )

    service_api_client.update_reply_to_email_address(SERVICE_ONE_ID, uuid4(), "foo@bar.com")

    mock_redis_delete.assert_called_with_args(f"service-{SERVICE_ONE_ID}")
    mock_redis_delete_by_pattern.assert_called_with_args(f"service-{SERVICE_ONE_ID}-template-*")


def test_client_updates_service_with_allowed_attributes(
    mocker,
):
    client = ServiceAPIClient(mocker.MagicMock())
    mock_post = mocker.patch.object(client, "post", return_value={"data": {"id": None}})
    mocker.patch("app.notify_client.current_user", id="123")

    allowed_attributes = [
        "active",
        "contact_link",
        "count_as_live",
        "email_branding",
        "free_sms_fragment_limit",
        "go_live_at",
        "go_live_user",
        "letter_branding",
        "letter_contact_block",
        "name",
        "notes",
        "organisation_type",
        "permissions",
        "prefix_sms",
        "rate_limit",
        "reply_to_email_address",
        "restricted",
        "sms_sender",
        "volume_email",
        "volume_letter",
        "volume_sms",
    ]

    attrs_dict = {}
    for attr in allowed_attributes:
        attrs_dict[attr] = "value"

    client.update_service(SERVICE_ONE_ID, **attrs_dict)
    mock_post.assert_called_once_with(f"/service/{SERVICE_ONE_ID}", {"created_by": "123", **attrs_dict})


@pytest.mark.parametrize(
    "err_data, expected_message",
    (
        ({"name": "Service name error"}, "This service name is already in use - enter a unique name"),
        (
            {"normalised_service_name": "normalised service name has disallowed characters"},
            "Service name cannot include characters from a non-Latin alphabet",
        ),
        ({"other": "blah"}, None),
    ),
)
def test_client_parsing_service_name_errors(err_data, expected_message, mocker):
    client = ServiceAPIClient(mocker.MagicMock())
    error = Mock()
    error.message = err_data

    error_message = client.parse_edit_service_http_error(error)

    assert error_message == expected_message


def test_deletes_unsubscribe_request_summary_when_batching(
    notify_admin,
    mock_get_user,
    mocker,
    fake_uuid,
):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)
    mock_request = mocker.patch("notifications_python_client.base.BaseAPIClient.request")

    service_api_client.create_unsubscribe_request_report(fake_uuid, data={})

    mock_redis_delete.assert_called_with_subset_of_args(f"service-{fake_uuid}-unsubscribe-request-reports-summary")
    assert len(mock_request.call_args_list) == 1


def test_update_service_join_requests(notify_admin, mocker):
    requester_id = uuid4()
    request_id = uuid4()
    service_id = SERVICE_ONE_ID

    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)
    mock_request = mocker.patch("notifications_python_client.base.BaseAPIClient.request", return_value={})

    service_api_client.update_service_join_requests(
        request_id=str(request_id), requester_id=str(requester_id), service_id=str(service_id), status="approved"
    )

    expected_cache_deletes = [
        f"service-join-request-{request_id}",
        f"user-{requester_id}",
        f"service-{service_id}-template-folders",
    ]

    mock_redis_delete.assert_called_with_args(*expected_cache_deletes)

    mock_request.assert_called_once_with(
        "POST", f"/service/update-service-join-request-status/{request_id}", data={"status": "approved"}
    )


def test_remove_service_inbound_sms_clears_cache(notify_admin, mocker):
    service_id = SERVICE_ONE_ID
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)
    mock_redis_delete_by_pattern = mocker.patch(
        "app.extensions.RedisClient.delete_by_pattern", new_callable=RedisClientMock
    )
    mock_post = mocker.patch("app.notify_client.service_api_client.ServiceAPIClient.post")

    service_api_client.remove_service_inbound_sms(service_id=service_id, archive=True)

    mock_redis_delete.assert_called_with_args(f"service-{service_id}")
    mock_redis_delete_by_pattern.assert_called_with_args(f"service-{service_id}-template-*")
    mock_post.assert_called_once_with(f"/service/{service_id}/inbound-sms/remove", data={"archive": True})
