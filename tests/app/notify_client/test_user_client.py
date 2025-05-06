import uuid
from unittest.mock import Mock, call

import pytest
from flask import current_app
from notifications_python_client.errors import HTTPError

from app import invite_api_client, service_api_client, user_api_client
from app.constants import PERMISSION_CAN_MAKE_SERVICES_LIVE
from app.models.webauthn_credential import WebAuthnCredential
from tests import sample_uuid
from tests.conftest import SERVICE_ONE_ID
from tests.utils import RedisClientMock

user_id = sample_uuid()


def test_client_gets_all_users_for_service(
    notify_admin,
    mocker,
    fake_uuid,
):
    user_api_client.max_failed_login_count = 99  # doesn't matter for this test
    mock_get = mocker.patch(
        "app.notify_client.user_api_client.UserApiClient.get",
        return_value={
            "data": [
                {"id": fake_uuid},
            ]
        },
    )

    users = user_api_client.get_users_for_service(SERVICE_ONE_ID)

    mock_get.assert_called_once_with(f"/service/{SERVICE_ONE_ID}/users")
    assert len(users) == 1
    assert users[0]["id"] == fake_uuid


def test_client_uses_correct_find_by_email(notify_admin, mocker, api_user_active):
    expected_url = "/user/email"
    expected_data = {"email": api_user_active["email_address"]}

    user_api_client.max_failed_login_count = 1  # doesn't matter for this test
    mock_post = mocker.patch("app.notify_client.user_api_client.UserApiClient.post")

    user_api_client.get_user_by_email(api_user_active["email_address"])

    mock_post.assert_called_once_with(expected_url, data=expected_data)


def test_client_only_updates_allowed_attributes(notify_admin, mocker):
    mocker.patch("app.notify_client.current_user", id="1")
    with pytest.raises(TypeError) as error:
        user_api_client.update_user_attribute("user_id", id="1")
    assert str(error.value) == "Not allowed to update user attributes: id"


def test_client_updates_password_separately(notify_admin, mocker, api_user_active):
    expected_url = f"/user/{api_user_active['id']}/update-password"
    expected_params = {"_password": "newpassword"}
    user_api_client.max_failed_login_count = 1  # doesn't matter for this test
    mock_update_password = mocker.patch("app.notify_client.user_api_client.UserApiClient.post")

    user_api_client.update_password(api_user_active["id"], expected_params["_password"])
    mock_update_password.assert_called_once_with(expected_url, data=expected_params)


def test_client_activates_if_pending(notify_admin, mocker, api_user_pending):
    mock_post = mocker.patch("app.notify_client.user_api_client.UserApiClient.post")
    user_api_client.max_failed_login_count = 1  # doesn't matter for this test

    user_api_client.activate_user(api_user_pending["id"])

    mock_post.assert_called_once_with(f"/user/{api_user_pending['id']}/activate", data=None)


def test_client_passes_admin_url_when_sending_email_auth(
    notify_admin,
    mocker,
    fake_uuid,
):
    mock_post = mocker.patch("app.notify_client.user_api_client.UserApiClient.post")

    user_api_client.send_verify_code(fake_uuid, "email", "ignored@example.com")

    mock_post.assert_called_once_with(
        f"/user/{fake_uuid}/email-code",
        data={
            "to": "ignored@example.com",
            "email_auth_link_host": current_app.config["ADMIN_BASE_URL"],
        },
    )


def test_client_converts_admin_permissions_to_db_permissions_on_edit(notify_admin, mocker):
    mock_post = mocker.patch("app.notify_client.user_api_client.UserApiClient.post")

    user_api_client.set_user_permissions("user_id", "service_id", permissions={"send_messages", "view_activity"})

    assert sorted(mock_post.call_args[1]["data"]["permissions"], key=lambda x: x["permission"]) == sorted(
        [
            {"permission": "send_texts"},
            {"permission": "send_emails"},
            {"permission": "send_letters"},
            {"permission": "view_activity"},
        ],
        key=lambda x: x["permission"],
    )


def test_client_converts_admin_permissions_to_db_permissions_on_add_to_service(notify_admin, mocker):
    mock_post = mocker.patch("app.notify_client.user_api_client.UserApiClient.post", return_value={"data": {}})

    user_api_client.add_user_to_service(
        "service_id", "user_id", permissions={"send_messages", "view_activity"}, folder_permissions=[]
    )

    assert sorted(mock_post.call_args[1]["data"]["permissions"], key=lambda x: x["permission"]) == sorted(
        [
            {"permission": "send_texts"},
            {"permission": "send_emails"},
            {"permission": "send_letters"},
            {"permission": "view_activity"},
        ],
        key=lambda x: x["permission"],
    )


@pytest.mark.parametrize(
    "expected_cache_get_calls,cache_value,expected_api_calls,expected_cache_set_calls,expected_return_value",
    [
        (
            [call(f"user-{user_id}")],
            b'{"data": "from cache"}',
            [],
            [],
            "from cache",
        ),
        (
            [call(f"user-{user_id}")],
            None,
            [call(f"/user/{user_id}")],
            [call(f"user-{user_id}", '{"data": "from api"}', ex=2_419_200)],
            "from api",
        ),
    ],
)
def test_returns_value_from_cache(
    notify_admin,
    mocker,
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
        return_value={"data": "from api"},
    )
    mock_redis_set = mocker.patch(
        "app.extensions.RedisClient.set",
    )

    user_api_client.get_user(user_id)

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
        ("user", "add_user_to_service", [SERVICE_ONE_ID, sample_uuid(), [], []], {}),
        ("user", "update_user_attribute", [user_id], {}),
        ("user", "reset_failed_login_count", [user_id], {}),
        ("user", "update_user_attribute", [user_id], {}),
        ("user", "update_password", [user_id, "hunter2"], {}),
        ("user", "verify_password", [user_id, "hunter2"], {}),
        ("user", "check_verify_code", [user_id, "", ""], {}),
        (
            "user",
            "complete_webauthn_login_attempt",
            [user_id],
            {"is_successful": True, "webauthn_credential_id": "123"},
        ),
        ("user", "add_user_to_service", [SERVICE_ONE_ID, user_id, [], []], {}),
        (
            "user",
            "add_user_to_organisation",
            [sample_uuid(), user_id, [PERMISSION_CAN_MAKE_SERVICES_LIVE]],
            {},
        ),
        ("user", "set_user_permissions", [user_id, SERVICE_ONE_ID, []], {}),
        ("user", "activate_user", [user_id], {}),
        ("user", "archive_user", [user_id], {}),
        ("service", "remove_user_from_service", [SERVICE_ONE_ID, user_id], {}),
        ("service", "create_service", ["", "", 0, 0, 0, 0, False, user_id], {}),
        ("invite", "accept_invite", [SERVICE_ONE_ID, user_id], {}),
    ],
)
def test_deletes_user_cache(notify_admin, mock_get_user, mocker, client_name, method, extra_args, extra_kwargs):
    mocker.patch("app.notify_client.current_user", id="1")
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)
    mock_request = mocker.patch("notifications_python_client.base.BaseAPIClient.request")

    getattr(_clients_by_name[client_name], method)(*extra_args, **extra_kwargs)

    assert len(mock_request.call_args_list) == 1
    mock_redis_delete.assert_called_with_subset_of_args(f"user-{user_id}")


def test_add_user_to_service_calls_correct_endpoint_and_deletes_keys_from_cache(notify_admin, mocker):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete", new_callable=RedisClientMock)

    service_id = uuid.uuid4()
    user_id = uuid.uuid4()
    folder_id = uuid.uuid4()

    expected_url = f"/service/{service_id}/users/{user_id}"
    data = {"permissions": [], "folder_permissions": [folder_id]}

    mock_post = mocker.patch("app.notify_client.user_api_client.UserApiClient.post")

    user_api_client.add_user_to_service(service_id, user_id, [], [folder_id])

    mock_post.assert_called_once_with(expected_url, data=data)
    mock_redis_delete.assert_called_with_args(
        f"user-{user_id}",
        f"service-{service_id}-template-folders",
        f"service-{service_id}",
    )


def test_get_webauthn_credentials_for_user(notify_admin, mocker, webauthn_credential, fake_uuid):
    mock_get = mocker.patch(
        "app.notify_client.user_api_client.UserApiClient.get", return_value={"data": [webauthn_credential]}
    )

    credentials = user_api_client.get_webauthn_credentials_for_user(fake_uuid)

    mock_get.assert_called_once_with(f"/user/{fake_uuid}/webauthn")
    assert len(credentials) == 1
    assert credentials[0]["name"] == "Test credential"


def test_create_webauthn_credential_for_user(notify_admin, mocker, webauthn_credential, fake_uuid):
    credential = WebAuthnCredential(webauthn_credential)

    mock_post = mocker.patch("app.notify_client.user_api_client.UserApiClient.post")
    expected_url = f"/user/{fake_uuid}/webauthn"

    user_api_client.create_webauthn_credential_for_user(fake_uuid, credential)
    mock_post.assert_called_once_with(expected_url, data=credential.serialize())


def test_complete_webauthn_login_attempt_returns_true_and_no_message_normally(notify_admin, fake_uuid, mocker):
    mock_post = mocker.patch("app.notify_client.user_api_client.UserApiClient.post")
    webauthn_credential_id = str(uuid.uuid4())

    resp = user_api_client.complete_webauthn_login_attempt(
        fake_uuid, is_successful=True, webauthn_credential_id=webauthn_credential_id
    )

    expected_data = {"successful": True, "webauthn_credential_id": webauthn_credential_id}
    mock_post.assert_called_once_with(f"/user/{fake_uuid}/complete/webauthn-login", data=expected_data)
    assert resp == (True, "")


def test_complete_webauthn_login_attempt_returns_false_and_message_on_403(notify_admin, fake_uuid, mocker):
    mock_post = mocker.patch(
        "app.notify_client.user_api_client.UserApiClient.post",
        side_effect=HTTPError(response=Mock(status_code=403, json=Mock(return_value={"message": "forbidden"}))),
    )
    webauthn_credential_id = str(uuid.uuid4())

    resp = user_api_client.complete_webauthn_login_attempt(
        fake_uuid, is_successful=True, webauthn_credential_id=webauthn_credential_id
    )

    expected_data = {"successful": True, "webauthn_credential_id": webauthn_credential_id}
    mock_post.assert_called_once_with(f"/user/{fake_uuid}/complete/webauthn-login", data=expected_data)

    assert resp == (False, "forbidden")


def test_complete_webauthn_login_attempt_raises_on_api_error(notify_admin, fake_uuid, mocker):
    mocker.patch(
        "app.notify_client.user_api_client.UserApiClient.post",
        side_effect=HTTPError(response=Mock(status_code=503, message="error")),
    )

    with pytest.raises(HTTPError):
        user_api_client.complete_webauthn_login_attempt(fake_uuid, is_successful=True, webauthn_credential_id=fake_uuid)


def test_reset_password(
    notify_admin,
    mocker,
):
    mock_post = mocker.patch("app.notify_client.user_api_client.UserApiClient.post")

    user_api_client.send_reset_password_url("test@example.com")

    mock_post.assert_called_once_with(
        "/user/reset-password",
        data={
            "email": "test@example.com",
            "admin_base_url": current_app.config["ADMIN_BASE_URL"],
        },
    )


def test_send_registration_email(
    notify_admin,
    mocker,
    fake_uuid,
):
    mock_post = mocker.patch("app.notify_client.user_api_client.UserApiClient.post")

    user_api_client.send_verify_email(fake_uuid, "test@example.com")

    mock_post.assert_called_once_with(
        f"/user/{fake_uuid}/email-verification",
        data={
            "to": "test@example.com",
            "admin_base_url": current_app.config["ADMIN_BASE_URL"],
        },
    )
