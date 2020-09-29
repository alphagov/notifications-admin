import pytest
from flask import url_for

from app import current_user
from tests import validate_route_permission
from tests.conftest import SERVICE_ONE_ID, create_template, normalize_spaces


def test_should_200_for_tour_start(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    page = client_request.get(
        'main.begin_tour',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    assert normalize_spaces(
        page.select('.banner-tour .heading-medium')[0].text
    ) == (
        'Try sending yourself this example'
    )
    selected_hint = page.select('.banner-tour .govuk-grid-row')[0]
    selected_hint_text = normalize_spaces(selected_hint.select(".govuk-body")[0].text)
    assert "greyed-out-step" not in selected_hint["class"]
    assert selected_hint_text == 'Every message is sent from a template'

    assert normalize_spaces(
        page.select('.sms-message-recipient')[0].text
    ) == (
        'To: 07700 900762'
    )
    assert normalize_spaces(
        page.select('.sms-message-wrapper')[0].text
    ) == (
        'service one: ((one)) ((two)) ((three))'
    )

    assert page.select('a.govuk-button')[0]['href'] == url_for(
        '.tour_step', service_id=SERVICE_ONE_ID, template_id=fake_uuid, step_index=1
    )


@pytest.mark.parametrize('template_type', ['email', 'letter', 'broadcast'])
def test_should_404_if_non_sms_template_for_tour_start(
    client_request,
    fake_uuid,
    mocker,
    template_type,
):
    mocker.patch(
        'app.service_api_client.get_service_template',
        return_value={'data': create_template(template_type=template_type)}
    )

    client_request.get(
        'main.begin_tour',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=404,
    )


def test_should_404_if_no_mobile_number_for_tour_start(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
    active_user_with_permissions_no_mobile
):
    client_request.login(active_user_with_permissions_no_mobile)
    assert current_user.mobile_number is None
    client_request.get(
        'main.begin_tour',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=404,
    )


def test_should_403_if_user_does_not_have_send_permissions_for_tour_start(
    mocker,
    app_,
    client,
    api_user_active,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    validate_route_permission(
        mocker,
        app_,
        "GET",
        403,
        url_for(
            'main.begin_tour',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
        ['view_activity'],
        api_user_active,
        service_one)
