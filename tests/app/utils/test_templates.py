import pytest
from notifications_utils.template import Template

from app.utils.templates import TemplatedLetterImageTemplate, get_sample_template
from tests import template_json
from tests.conftest import SERVICE_ONE_ID


@pytest.mark.parametrize("template_type", ["sms", "letter", "email"])
def test_get_sample_template_returns_template(template_type):
    template = get_sample_template(template_type)
    assert isinstance(template, Template)


def test_get_page_count_for_letter_caches(
    client_request,
    service_one,
    api_user_active,
    mocker,
    fake_uuid,
):
    client_request.login(api_user_active, service_one)

    mock_redis_get = mocker.patch(
        "app.extensions.RedisClient.get",
        return_value=None,
    )
    mock_redis_set = mocker.patch(
        "app.extensions.RedisClient.set",
    )
    mock_get_page_count = mocker.patch("app.template_previews.get_page_count_for_letter", return_value=5)

    template = TemplatedLetterImageTemplate(
        template_json(
            service_id=SERVICE_ONE_ID,
            id_=fake_uuid,
            type_="letter",
        )
    )

    for _ in range(3):
        assert template.page_count == 5

    # Redis and template preview only get called once each because the instance also caches the value
    mock_redis_get.assert_called_once_with(f"service-{SERVICE_ONE_ID}-template-{fake_uuid}-page-count")
    mock_redis_set.assert_called_once_with(f"service-{SERVICE_ONE_ID}-template-{fake_uuid}-page-count", 5, ex=2_419_200)
    assert len(mock_get_page_count.call_args_list) == 1


def test_get_page_count_for_letter_returns_cached_value(
    client_request,
    service_one,
    api_user_active,
    mocker,
    fake_uuid,
):
    client_request.login(api_user_active, service_one)

    mock_redis_get = mocker.patch(
        "app.extensions.RedisClient.get",
        return_value="5",
    )

    template = TemplatedLetterImageTemplate(
        template_json(
            service_id=SERVICE_ONE_ID,
            id_=fake_uuid,
            type_="letter",
        )
    )

    for _ in range(3):
        assert template.page_count == 5

    # Redis only gets called once because the instance also caches the value
    mock_redis_get.assert_called_once_with(f"service-{SERVICE_ONE_ID}-template-{fake_uuid}-page-count")


def test_get_page_count_for_letter_does_not_cache_for_personalised_letters(
    client_request,
    service_one,
    api_user_active,
    mocker,
    fake_uuid,
):
    client_request.login(api_user_active, service_one)

    mock_get_page_count = mocker.patch("app.template_previews.get_page_count_for_letter", return_value=5)

    template = TemplatedLetterImageTemplate(
        template_json(
            service_id=SERVICE_ONE_ID,
            id_=fake_uuid,
            type_="letter",
        )
    )

    for _ in range(3):
        # We’re changing the values so the page count might change
        template.values = {"foo": "bar"}
        assert template.page_count == 5

    # No calls to Redis here
    assert len(mock_get_page_count.call_args_list) == 3
