from unittest.mock import ANY, call

import pytest

from app import organisations_client
from tests.utils import assert_mock_has_any_call_with_first_n_args


@pytest.mark.parametrize(
    (
        "client_method,"
        "expected_cache_get_calls,"
        "cache_value,"
        "expected_api_calls,"
        "expected_cache_set_calls,"
        "expected_return_value,"
    ),
    [
        (
            "get_domains",
            [
                call("domains"),
            ],
            b"""
                [
                    {"name": "org 1", "domains": ["a", "b", "c"]},
                    {"name": "org 2", "domains": ["c", "d", "e"]}
                ]
            """,
            [],
            [],
            ["a", "b", "c", "d", "e"],
        ),
        (
            "get_domains",
            [
                call("domains"),
                call("organisations"),
            ],
            None,
            [call(url="/organisations")],
            [
                call(
                    "organisations",
                    '[{"domains": ["x", "y", "z"]}]',
                    ex=2_419_200,
                ),
                call("domains", '["x", "y", "z"]', ex=2_419_200),
            ],
            "from api",
        ),
        (
            "get_organisations",
            [
                call("organisations"),
            ],
            b"""
                [
                    {"name": "org 1", "domains": ["a", "b", "c"]},
                    {"name": "org 2", "domains": ["c", "d", "e"]}
                ]
            """,
            [],
            [],
            [{"name": "org 1", "domains": ["a", "b", "c"]}, {"name": "org 2", "domains": ["c", "d", "e"]}],
        ),
        (
            "get_organisations",
            [
                call("organisations"),
            ],
            None,
            [call(url="/organisations")],
            [
                call(
                    "organisations",
                    '[{"domains": ["x", "y", "z"]}]',
                    ex=2_419_200,
                ),
            ],
            "from api",
        ),
    ],
)
def test_returns_value_from_cache(
    notify_admin,
    mocker,
    client_method,
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
        return_value=[{"domains": ["x", "y", "z"]}],
    )
    mock_redis_set = mocker.patch(
        "app.extensions.RedisClient.set",
    )

    getattr(organisations_client, client_method)()

    assert mock_redis_get.call_args_list == expected_cache_get_calls
    assert mock_api_get.call_args_list == expected_api_calls
    assert mock_redis_set.call_args_list == expected_cache_set_calls


def test_deletes_domain_cache(
    notify_admin,
    mock_get_user,
    mocker,
    fake_uuid,
):
    mocker.patch("app.notify_client.current_user", id="1")
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    mock_request = mocker.patch("notifications_python_client.base.BaseAPIClient.request")

    organisations_client.update_organisation(fake_uuid, foo="bar")

    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, "domains")
    assert len(mock_request.call_args_list) == 1


def test_update_organisation_when_org_has_no_services(mocker, fake_uuid):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    mock_post = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.post")

    organisations_client.update_organisation(fake_uuid, **{"foo": "bar"})

    mock_post.assert_called_with(url=f"/organisations/{fake_uuid}", data={"foo": "bar"})

    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, "domains")
    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, "organisations")
    assert_mock_has_any_call_with_first_n_args(
        mock_redis_delete,
        "organisation-6ce466d0-fd6a-11e5-82f5-e0accb9d11a6-name",
    )
    assert_mock_has_any_call_with_first_n_args(
        mock_redis_delete, "organisation-6ce466d0-fd6a-11e5-82f5-e0accb9d11a6-email-branding-pool"
    )
    assert_mock_has_any_call_with_first_n_args(
        mock_redis_delete, "organisation-6ce466d0-fd6a-11e5-82f5-e0accb9d11a6-letter-branding-pool"
    )


def test_update_organisation_when_org_has_services(mocker, fake_uuid):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    mock_post = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.post")

    organisations_client.update_organisation(
        fake_uuid,
        cached_service_ids=["a", "b", "c"],
        foo="bar",
    )

    mock_post.assert_called_with(url=f"/organisations/{fake_uuid}", data={"foo": "bar"})

    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, "domains")
    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, "organisations")
    assert_mock_has_any_call_with_first_n_args(
        mock_redis_delete,
        "organisation-6ce466d0-fd6a-11e5-82f5-e0accb9d11a6-name",
    )
    assert_mock_has_any_call_with_first_n_args(
        mock_redis_delete, "organisation-6ce466d0-fd6a-11e5-82f5-e0accb9d11a6-email-branding-pool"
    )
    assert_mock_has_any_call_with_first_n_args(
        mock_redis_delete, "organisation-6ce466d0-fd6a-11e5-82f5-e0accb9d11a6-letter-branding-pool"
    )
    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, "service-a", "service-b", "service-c")


def test_add_brandings_to_email_branding_pool(mocker, fake_uuid):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    mock_post = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.post")

    organisations_client.add_brandings_to_email_branding_pool(
        fake_uuid,
        branding_ids=["abcd", "efgh"],
    )
    mock_post.assert_called_with(
        url=f"/organisations/{fake_uuid}/email-branding-pool", data={"branding_ids": ["abcd", "efgh"]}
    )
    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, f"organisation-{fake_uuid}-email-branding-pool")


def test_update_service_organisation_deletes_cache(mocker, fake_uuid):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    mock_post = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.post")

    organisations_client.update_service_organisation(service_id=fake_uuid, org_id=fake_uuid)

    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, "live-service-and-organisation-counts")
    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, "organisations")
    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, f"service-{fake_uuid}")
    mock_post.assert_called_with(url=f"/organisations/{fake_uuid}/service", data=ANY)


def test_remove_user_from_organisation_deletes_user_cache(mocker):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    mock_delete = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.delete")

    org_id = "abcd-1234"
    user_id = "efgh-5678"

    organisations_client.remove_user_from_organisation(
        org_id=org_id,
        user_id=user_id,
    )
    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, f"user-{user_id}")
    mock_delete.assert_called_with(f"/organisations/{org_id}/users/{user_id}")


def test_archive_organisation(mocker):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    mock_post = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.post")

    org_id = "abcd-1234"

    organisations_client.archive_organisation(org_id=org_id)

    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, f"organisation-{org_id}-name")
    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, "domains")
    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, "organisations")
    mock_post.assert_called_with(url=f"/organisations/{org_id}/archive", data=None)


def test_remove_email_branding_from_organisation_pool(mocker):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    mock_delete = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.delete")

    org_id = "abcd-1234"
    branding_id = "efgh-5678"

    organisations_client.remove_email_branding_from_pool(
        org_id=org_id,
        branding_id=branding_id,
    )

    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, f"organisation-{org_id}-email-branding-pool")
    mock_delete.assert_called_with(f"/organisations/{org_id}/email-branding-pool/{branding_id}")


def test_get_letter_branding_pool(mocker):
    mock_redis_set = mocker.patch("app.extensions.RedisClient.set")
    mock_get = mocker.patch(
        "app.notify_client.organisations_api_client.OrganisationsClient.get",
        return_value={"data": {"filename": "gov.svg"}},
    )

    org_id = "abcd-1234"
    organisations_client.get_letter_branding_pool(org_id)

    mock_redis_set.assert_called_once_with(
        f"organisation-{org_id}-letter-branding-pool", '{"filename": "gov.svg"}', ex=2_419_200
    )
    mock_get.assert_called_with(url=f"/organisations/{org_id}/letter-branding-pool")


def test_add_brandings_to_letter_branding_pool(mocker, fake_uuid):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    mock_post = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.post")

    organisations_client.add_brandings_to_letter_branding_pool(
        fake_uuid,
        branding_ids=["abcd", "efgh"],
    )
    mock_post.assert_called_with(
        url=f"/organisations/{fake_uuid}/letter-branding-pool", data={"branding_ids": ["abcd", "efgh"]}
    )
    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, f"organisation-{fake_uuid}-letter-branding-pool")


def test_remove_letter_branding_from_organisation_pool(mocker):
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    mock_delete = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.delete")

    org_id = "abcd-1234"
    branding_id = "efgh-5678"

    organisations_client.remove_letter_branding_from_pool(
        org_id=org_id,
        branding_id=branding_id,
    )

    assert_mock_has_any_call_with_first_n_args(mock_redis_delete, f"organisation-{org_id}-letter-branding-pool")
    mock_delete.assert_called_with(f"/organisations/{org_id}/letter-branding-pool/{branding_id}")


def test_notify_users_of_request_to_go_live_for_service(mocker, fake_uuid):
    mock_post = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.post")

    organisations_client.notify_users_of_request_to_go_live_for_service(fake_uuid)

    mock_post.assert_called_with(
        url=f"/organisations/notify-users-of-request-to-go-live/{fake_uuid}",
        data=None,
    )
