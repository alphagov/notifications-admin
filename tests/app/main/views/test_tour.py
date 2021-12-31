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


def test_should_clear_session_on_tour_start(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {'one': 'hello', 'phone number': '07700 900762'}

    client_request.get(
        'main.begin_tour',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    with client_request.session_transaction() as session:
        assert session['placeholders'] == {}


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
    notify_admin,
    client,
    api_user_active,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    validate_route_permission(
        mocker,
        notify_admin,
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


def test_should_200_for_get_tour_step(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {}

    page = client_request.get(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=1
    )

    assert 'Example text message' in normalize_spaces(page.select_one('title').text)
    assert normalize_spaces(
        page.select('.banner-tour .heading-medium')[0].text
    ) == (
        'Try sending yourself this example'
    )
    selected_hint = page.select('.banner-tour .govuk-grid-row')[1]
    selected_hint_text = normalize_spaces(selected_hint.select(".govuk-body")[0].text)
    assert "greyed-out-step" not in selected_hint["class"]
    assert selected_hint_text == 'The template pulls in the data you provide'

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


def test_should_show_empty_text_box(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {'phone number': '07700 900762'}

    page = client_request.get(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=1
    )

    textbox = page.select_one('[data-module=autofocus][data-force-focus=True] .govuk-input')
    assert 'value' not in textbox
    assert textbox['name'] == 'placeholder_value'
    assert textbox['class'] == [
        'govuk-input', 'govuk-!-width-full',
    ]
    # data-module=autofocus is set on a containing element so it
    # shouldn’t also be set on the textbox itself
    assert 'data-module' not in textbox
    assert normalize_spaces(
        page.select_one('label[for=placeholder_value]').text
    ) == 'one'


def test_should_prefill_answers_for_get_tour_step(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = session['placeholders'] = {'one': 'hello', 'phone number': '07700 900762'}

    page = client_request.get(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=1
    )

    assert page.select('.govuk-input')[0]['value'] == 'hello'


@pytest.mark.parametrize('template_type', ['email', 'letter', 'broadcast'])
@pytest.mark.parametrize('method', ['get', 'post'])
def test_should_404_if_non_sms_template_for_tour_step(
    client_request,
    fake_uuid,
    mocker,
    template_type,
    method
):
    mocker.patch(
        'app.service_api_client.get_service_template',
        return_value={'data': create_template(template_type=template_type)}
    )

    getattr(client_request, method)(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=1,
        _expected_status=404
    )


def test_should_404_for_get_tour_step_0(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {}

    client_request.get(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=0,
        _expected_status=404
    )


@pytest.mark.parametrize('method', ['GET', 'POST'])
def test_should_403_if_user_does_not_have_send_permissions_for_tour_step(
    mocker,
    notify_admin,
    client,
    api_user_active,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
    method
):
    validate_route_permission(
        mocker,
        notify_admin,
        method,
        403,
        url_for(
            'main.tour_step',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            step_index=1
        ),
        ['view_activity'],
        api_user_active,
        service_one
    )


def test_tour_step_redirects_to_tour_start_if_placeholders_doesnt_exist_in_session(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        assert 'placeholders' not in session

    client_request.get(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=1,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.begin_tour',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True,
        ),
    )


def test_back_link_from_first_get_tour_step_points_to_tour_start(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {}

    page = client_request.get(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=1
    )

    assert page.select('.govuk-back-link')[0]['href'] == url_for(
        "main.begin_tour",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid
    )


def test_back_link_from_get_tour_step_points_to_previous_step(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {}

    page = client_request.get(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=2
    )

    assert page.select('.govuk-back-link')[0]['href'] == url_for(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=1
    )


def test_post_tour_step_saves_data_and_redirects_to_next_step(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {}

    client_request.post(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=1,
        _data={'placeholder_value': 'hello'},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.tour_step',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            step_index=2,
            _external=True,
        ),
    )

    with client_request.session_transaction() as session:
        assert session['placeholders'] == {'one': 'hello', 'phone number': '07700 900762'}


def test_post_tour_step_adds_data_to_saved_data_and_redirects_to_next_step(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {'one': 'hello', 'phone number': '07700 900762'}

    client_request.post(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=2,
        _data={'placeholder_value': 'is it me you are looking for'},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.tour_step',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            step_index=3,
            _external=True,
        ),
    )

    with client_request.session_transaction() as session:
        assert session['placeholders'] == {
            'one': 'hello', 'two': 'is it me you are looking for', 'phone number': '07700 900762'
        }


def test_post_tour_step_raises_validation_error_for_form_error(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {'one': 'hi', 'phone number': '07700 900762'}

    page = client_request.post(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=2,
        _data={'placeholder_value': ''},
        _expected_status=200,  # should this be 400
    )

    assert normalize_spaces(
        page.select('.govuk-error-message')[0].text
    ) == (
        'Error: Cannot be empty'
    )

    assert normalize_spaces(
        page.select('.sms-message-recipient')[0].text
    ) == (
        'To: 07700 900762'
    )

    assert normalize_spaces(
        page.select('.sms-message-wrapper')[0].text
    ) == (
        'service one: hi ((two)) ((three))'
    )

    with client_request.session_transaction() as session:
        assert session['placeholders'] == {'one': 'hi', 'phone number': '07700 900762'}


def test_post_final_tour_step_saves_data_and_redirects_to_check_notification(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {'one': 'hello', 'two': 'hi', 'phone number': '07700 900762'}

    client_request.post(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=3,
        _data={'placeholder_value': 'howdy'},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.check_tour_notification',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True
        ),
    )

    with client_request.session_transaction() as session:
        assert session['placeholders'] == {
            'one': 'hello', 'two': 'hi', 'three': 'howdy', 'phone number': '07700 900762'
        }


def test_get_test_step_out_of_index_redirects_to_first_step(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {}

    client_request.get(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=4,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.tour_step',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            step_index=1,
            _external=True
        ),
    )


def test_get_test_step_out_of_index_redirects_to_check_notification_if_all_placeholders_filled(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {'one': 'hello', 'two': 'hi', 'three': 'howdy', 'phone number': '07700 900762'}

    client_request.get(
        'main.tour_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=4,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.check_tour_notification',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True
        ),
    )


def test_should_200_for_check_tour_notification(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {'one': 'hello', 'two': 'hi', 'three': 'howdy', 'phone number': '07700 900762'}

    page = client_request.get(
        'main.check_tour_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    assert normalize_spaces(
        page.select('.banner-tour .heading-medium')[0].text
    ) == (
        'Try sending yourself this example'
    )
    selected_hint = page.select('.banner-tour .govuk-grid-row')[1]
    selected_hint_text = normalize_spaces(selected_hint.select(".govuk-body")[0].text)
    assert "greyed-out-step" not in selected_hint["class"]
    assert selected_hint_text == 'The template pulls in the data you provide'

    assert normalize_spaces(
        page.select('.sms-message-recipient')[0].text
    ) == (
        'To: 07700 900762'
    )
    assert normalize_spaces(
        page.select('.sms-message-wrapper')[0].text
    ) == (
        'service one: hello hi howdy'
    )

    # post to send_notification keeps help argument
    assert page.form.attrs['action'] == url_for(
        'main.send_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        help='3'
    )


def test_back_link_from_check_tour_notification_points_to_last_tour_step(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {'one': 'hello', 'two': 'hi', 'three': 'howdy', 'phone number': '07700 900762'}

    page = client_request.get(
        'main.check_tour_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    assert page.select('.govuk-back-link')[0]['href'] == url_for(
        "main.tour_step",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=3
    )


def test_check_tour_notification_redirects_to_tour_start_if_placeholders_doesnt_exist_in_session(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        assert 'placeholders' not in session

    client_request.get(
        'main.check_tour_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=1,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.begin_tour',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True,
        ),
    )


def test_check_tour_notification_redirects_to_first_step_if_not_all_placeholders_in_session(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    service_one,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {'one': 'hello', 'two': 'hi', 'phone number': '07700 900762'}

    client_request.get(
        'main.check_tour_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.tour_step',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            step_index=1,
            _external=True
        ),
    )


def test_shows_link_to_end_tour(
    client_request,
    mock_get_notification,
    fake_uuid,
):

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        help=3,
    )

    assert page.select(".banner-tour a")[0]['href'] == url_for(
        'main.go_to_dashboard_after_tour',
        service_id=SERVICE_ONE_ID,
        example_template_id='5407f4db-51c7-4150-8758-35412d42186a',
    )


def test_go_to_dashboard_after_tour_link(
    client_request,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_has_permissions,
    mock_delete_service_template,
    fake_uuid
):
    client_request.get(
        'main.go_to_dashboard_after_tour',
        service_id=fake_uuid,
        example_template_id=fake_uuid,
        _expected_redirect=url_for(
            "main.service_dashboard",
            service_id=fake_uuid,
            _external=True,
        )
    )

    mock_delete_service_template.assert_called_once_with(fake_uuid, fake_uuid)
