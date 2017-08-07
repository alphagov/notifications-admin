from flask import url_for, session

import app
from app.utils import is_gov_user


def test_non_gov_user_cannot_see_add_service_button(
    client,
    mock_login,
    mock_get_non_govuser,
    api_nongov_user_active,
):
    client.login(api_nongov_user_active)
    response = client.get(url_for('main.choose_service'))
    assert 'Add a new service' not in response.get_data(as_text=True)
    assert response.status_code == 200


def test_get_should_render_add_service_template(
    logged_in_client,
    api_user_active,
    mocker,
):
    response = logged_in_client.get(url_for('main.add_service'))
    assert response.status_code == 200
    assert 'Which service do you want to set up notifications for?' in response.get_data(as_text=True)


def test_should_add_service_and_redirect_to_tour_when_no_services(
    app_,
    logged_in_client,
    mocker,
    mock_create_service,
    mock_create_service_template,
    mock_get_services_with_no_services,
    api_user_active,
):
    response = logged_in_client.post(
        url_for('main.add_service'),
        data={'name': 'testing the post'})
    assert mock_get_services_with_no_services.called
    mock_create_service.assert_called_once_with(
        service_name='testing the post',
        message_limit=app_.config['DEFAULT_SERVICE_LIMIT'],
        restricted=True,
        user_id=api_user_active.id,
        email_from='testing.the.post'
    )
    mock_create_service_template.assert_called_once_with(
        'Example text message template',
        'sms',
        (
            'Hey ((name)), I’m trying out Notify. Today is '
            '((day of week)) and my favourite colour is ((colour)).'
        ),
        101,
        process_type='priority',
    )
    assert session['service_id'] == 101
    assert response.status_code == 302
    assert response.location == url_for(
        'main.start_tour',
        service_id=101,
        template_id="Example%20text%20message%20template",
        _external=True
    )


def test_should_add_service_and_redirect_to_dashboard_when_existing_service(
    app_,
    logged_in_client,
    mocker,
    mock_create_service,
    mock_create_service_template,
    mock_get_services,
    api_user_active,
):
    response = logged_in_client.post(
        url_for('main.add_service'),
        data={'name': 'testing the post'})
    assert mock_get_services.called
    mock_create_service.assert_called_once_with(
        service_name='testing the post',
        message_limit=app_.config['DEFAULT_SERVICE_LIMIT'],
        restricted=True,
        user_id=api_user_active.id,
        email_from='testing.the.post'
    )
    assert len(mock_create_service_template.call_args_list) == 0
    assert session['service_id'] == 101
    assert response.status_code == 302
    assert response.location == url_for('main.service_dashboard', service_id=101, _external=True)


def test_should_return_form_errors_when_service_name_is_empty(
    logged_in_client,
    mocker,
    api_user_active,
):
    response = logged_in_client.post(url_for('main.add_service'), data={})
    assert response.status_code == 200
    assert 'Can’t be empty' in response.get_data(as_text=True)


def test_should_return_form_errors_with_duplicate_service_name_regardless_of_case(
    logged_in_client,
    mocker,
    service_one,
    api_user_active,
    mock_create_duplicate_service,
):
    response = logged_in_client.post(url_for('main.add_service'), data={'name': 'SERVICE TWO'})
    print(response.status_code)
    assert response.status_code == 400
    assert response.message == "Duplicate service name 'SERVICE_TWO'"
    assert 'This service name is already in use' in response.get_data(as_text=True)
    assert mock_create_duplicate_service.called


def test_non_whitelist_user_cannot_access_create_service_page(
    logged_in_client,
    mock_login,
    mock_get_non_govuser,
    api_nongov_user_active,
):
    assert not is_gov_user(api_nongov_user_active.email_address)
    response = logged_in_client.get(url_for('main.add_service'))
    assert response.status_code == 403


def test_non_whitelist_user_cannot_create_service(
    logged_in_client,
    mock_login,
    mock_get_non_govuser,
    api_nongov_user_active,
):
    assert not is_gov_user(api_nongov_user_active.email_address)
    response = logged_in_client.post(url_for('main.add_service'), data={'name': 'SERVICE TWO'})
    assert response.status_code == 403
