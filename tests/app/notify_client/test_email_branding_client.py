from unittest.mock import call

from app.notify_client.email_branding_client import EmailBrandingClient


def test_get_email_branding(mocker, fake_uuid):
    mock_get = mocker.patch(
        "app.notify_client.email_branding_client.EmailBrandingClient.get", return_value={"foo": "bar"}
    )
    mock_redis_get = mocker.patch(
        "app.extensions.RedisClient.get",
        return_value=None,
    )
    mock_redis_set = mocker.patch(
        "app.extensions.RedisClient.set",
    )
    EmailBrandingClient().get_email_branding(fake_uuid)
    mock_get.assert_called_once_with(url=f"/email-branding/{fake_uuid}")
    mock_redis_get.assert_called_once_with(f"email_branding-{fake_uuid}")
    mock_redis_set.assert_called_once_with(
        f"email_branding-{fake_uuid}",
        '{"foo": "bar"}',
        ex=2_419_200,
    )


def test_get_all_email_branding(mocker):
    mock_get = mocker.patch(
        "app.notify_client.email_branding_client.EmailBrandingClient.get", return_value={"email_branding": [1, 2, 3]}
    )
    mock_redis_get = mocker.patch(
        "app.extensions.RedisClient.get",
        return_value=None,
    )
    mock_redis_set = mocker.patch(
        "app.extensions.RedisClient.set",
    )
    EmailBrandingClient().get_all_email_branding()
    mock_get.assert_called_once_with(url="/email-branding")
    mock_redis_get.assert_called_once_with("email_branding")
    mock_redis_set.assert_called_once_with(
        "email_branding",
        "[1, 2, 3]",
        ex=2_419_200,
    )


def test_create_email_branding(mocker, fake_uuid):
    org_data = {
        "logo": "test.png",
        "name": "test name",
        "alt_text": "test alt text",
        "text": "test name",
        "colour": "red",
        "brand_type": "org",
        "created_by": fake_uuid,
    }

    mock_post = mocker.patch("app.notify_client.email_branding_client.EmailBrandingClient.post")
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    EmailBrandingClient().create_email_branding(
        logo=org_data["logo"],
        name=org_data["name"],
        alt_text=org_data["alt_text"],
        text=org_data["text"],
        colour=org_data["colour"],
        brand_type="org",
        created_by_id=org_data["created_by"],
    )

    mock_post.assert_called_once_with(url="/email-branding", data=org_data)

    mock_redis_delete.assert_called_once_with("email_branding")


def test_update_email_branding(mocker, fake_uuid):
    org_data = {
        "logo": "test.png",
        "name": "test name",
        "alt_text": "test alt text",
        "text": "test name",
        "colour": "red",
        "brand_type": "org",
        "updated_by": fake_uuid,
    }

    mock_post = mocker.patch("app.notify_client.email_branding_client.EmailBrandingClient.post")
    mock_redis_delete = mocker.patch("app.extensions.RedisClient.delete")
    mock_redis_delete_by_pattern = mocker.patch("app.extensions.RedisClient.delete_by_pattern")
    EmailBrandingClient().update_email_branding(
        branding_id=fake_uuid,
        logo=org_data["logo"],
        name=org_data["name"],
        alt_text=org_data["alt_text"],
        text=org_data["text"],
        colour=org_data["colour"],
        brand_type="org",
        updated_by_id=org_data["updated_by"],
    )

    mock_post.assert_called_once_with(url=f"/email-branding/{fake_uuid}", data=org_data)
    assert mock_redis_delete.call_args_list == [
        call(f"email_branding-{fake_uuid}"),
        call("email_branding"),
    ]
    assert mock_redis_delete_by_pattern.call_args_list == [call("organisation-*-email-branding-pool")]


def test_create_email_branding_sends_none_values(mocker, fake_uuid):
    # this would fail because neither of alt text and text are set, but the key is we're not sending empty strings
    form_data = {
        "logo": "",
        "name": "test name",
        "alt_text": "",
        "text": "",
        "colour": "",
        "brand_type": "org",
        "created_by_id": fake_uuid,
    }

    expected_data = {
        "logo": None,
        "name": "test name",
        "alt_text": None,
        "text": None,
        "colour": None,
        "brand_type": "org",
        "created_by": fake_uuid,
    }

    mock_post = mocker.patch("app.notify_client.email_branding_client.EmailBrandingClient.post")
    EmailBrandingClient().create_email_branding(**form_data)

    mock_post.assert_called_once_with(url="/email-branding", data=expected_data)


def test_update_email_branding_sends_none_values(mocker, fake_uuid):
    form_data = {
        "logo": "",
        "name": "test name",
        "alt_text": "test alt text",
        "text": "",
        "colour": "",
        "brand_type": "org",
        "branding_id": fake_uuid,
        "updated_by_id": fake_uuid,
    }

    expected_data = {
        "logo": None,
        "name": "test name",
        "alt_text": "test alt text",
        "text": None,
        "colour": None,
        "brand_type": "org",
        "updated_by": fake_uuid,
    }

    mock_post = mocker.patch("app.notify_client.email_branding_client.EmailBrandingClient.post")
    EmailBrandingClient().update_email_branding(**form_data)

    mock_post.assert_called_once_with(url=f"/email-branding/{fake_uuid}", data=expected_data)


def test_get_email_branding_name_for_alt_text(mocker):
    mock_post = mocker.patch(
        "app.notify_client.email_branding_client.EmailBrandingClient.post", return_value={"name": "bar"}
    )
    resp = EmailBrandingClient().get_email_branding_name_for_alt_text("foo")
    assert resp == "bar"
    mock_post.assert_called_once_with(url="/email-branding/get-name-for-alt-text", data={"alt_text": "foo"})
