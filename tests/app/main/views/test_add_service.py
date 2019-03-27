import pytest
from flask import session, url_for

from app.utils import is_gov_user


def test_non_gov_user_cannot_see_add_service_button(
    client,
    mock_login,
    mock_get_non_govuser,
    api_nongov_user_active,
    mock_get_organisations_and_services_for_user
):
    client.login(api_nongov_user_active)
    response = client.get(url_for('main.choose_account'))
    assert 'Add a new service' not in response.get_data(as_text=True)
    assert response.status_code == 200


def test_get_should_render_add_service_template(
    client_request
):
    page = client_request.get('main.add_service')
    assert 'About your service' in page.text


def test_should_add_service_and_redirect_to_tour_when_no_services(
    app_,
    client_request,
    mock_create_service,
    mock_create_service_template,
    mock_get_services_with_no_services,
    api_user_active,
    mock_create_or_update_free_sms_fragment_limit,
    mock_get_all_email_branding,
):
    client_request.post(
        'main.add_service',
        _data={
            'name': 'testing the post',
            'organisation_type': 'local',
        },
        _expected_status=302,
        _expected_redirect=url_for(
            'main.start_tour',
            service_id=101,
            template_id="Example%20text%20message%20template",
            _external=True,
        ),
    )
    assert mock_get_services_with_no_services.called
    mock_create_service.assert_called_once_with(
        service_name='testing the post',
        organisation_type='local',
        message_limit=app_.config['DEFAULT_SERVICE_LIMIT'],
        restricted=True,
        user_id=api_user_active.id,
        email_from='testing.the.post',
        service_domain=None
    )
    mock_create_service_template.assert_called_once_with(
        'Example text message template',
        'sms',
        (
            'Hey ((name)), I’m trying out Notify. Today is '
            '((day of week)) and my favourite colour is ((colour)).'
        ),
        101,
    )
    assert session['service_id'] == 101
    mock_create_or_update_free_sms_fragment_limit.assert_called_once_with(101, 25000)


@pytest.mark.parametrize('organisation_type, free_allowance, service_domain', [
    ('central', 250 * 1000, None),
    ('local', 25 * 1000, None),
    ('nhs', 25 * 1000, 'nhs.uk'),
])
def test_should_add_service_and_redirect_to_dashboard_when_existing_service(
    app_,
    client_request,
    mock_create_service,
    mock_create_service_template,
    mock_get_services,
    mock_update_service,
    api_user_active,
    organisation_type,
    free_allowance,
    service_domain,
    mock_create_or_update_free_sms_fragment_limit,
    mock_get_all_email_branding,
):
    client_request.post(
        'main.add_service',
        _data={
            'name': 'testing the post',
            'organisation_type': organisation_type,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            'main.service_dashboard',
            service_id=101,
            _external=True,
        )
    )
    assert mock_get_services.called
    mock_create_service.assert_called_once_with(
        service_name='testing the post',
        organisation_type=organisation_type,
        message_limit=app_.config['DEFAULT_SERVICE_LIMIT'],
        restricted=True,
        user_id=api_user_active.id,
        email_from='testing.the.post',
        service_domain=service_domain
    )
    mock_create_or_update_free_sms_fragment_limit.assert_called_once_with(101, free_allowance)
    assert len(mock_create_service_template.call_args_list) == 0
    assert session['service_id'] == 101


@pytest.mark.parametrize('organisation_type, email_address, expected_branding', [
    ('central', 'test@example.voa.gsi.gov.uk', '5'),
    ('central', 'test@example.voa.gov.uk', '5'),
    ('central', 'test@example.gov.uk', None),
    # Anyone choosing ‘NHS’ for organisation type gets NHS branding no
    # matter what their email domain is (but we look it up based on the
    # `nhs.uk` domain to avoid hard-coding a branding ID anywhere)
    ('nhs', 'test@example.voa.gov.uk', '4'),
    ('nhs', 'test@nhs.uk', '4'),
])
def test_should_lookup_branding_for_known_domain(
    app_,
    client_request,
    active_user_with_permissions,
    mock_create_service,
    mock_get_services,
    mock_update_service,
    mock_create_or_update_free_sms_fragment_limit,
    mock_get_all_email_branding,
    organisation_type,
    email_address,
    expected_branding,
):
    active_user_with_permissions.email_address = email_address
    client_request.login(active_user_with_permissions)
    client_request.post(
        'main.add_service',
        _data={
            'name': 'testing the post',
            'organisation_type': organisation_type,
        }
    )
    mock_get_all_email_branding.assert_called_once_with()
    assert mock_create_service.called is True
    if expected_branding:
        mock_update_service.assert_called_once_with(
            101,
            email_branding=expected_branding,
        )
    else:
        assert mock_update_service.called is False


def test_should_return_form_errors_when_service_name_is_empty(
    client_request
):
    page = client_request.post(
        'main.add_service',
        data={},
        _expected_status=200,
    )
    assert 'Can’t be empty' in page.text


def test_should_return_form_errors_with_duplicate_service_name_regardless_of_case(
    client_request,
    mock_create_duplicate_service,
    mock_get_all_email_branding,
):
    page = client_request.post(
        'main.add_service',
        _data={
            'name': 'SERVICE ONE',
            'organisation_type': 'central',
        },
        _expected_status=200,
    )
    assert page.select_one('.error-message').text.strip() == (
        'This service name is already in use'
    )


def test_non_whitelist_user_cannot_access_create_service_page(
    client_request,
    mock_get_non_govuser,
    api_nongov_user_active,
):
    assert not is_gov_user(api_nongov_user_active.email_address)
    client_request.get(
        'main.add_service',
        _expected_status=403,
    )


def test_non_whitelist_user_cannot_create_service(
    client_request,
    mock_get_non_govuser,
    api_nongov_user_active,
):
    assert not is_gov_user(api_nongov_user_active.email_address)
    client_request.post(
        'main.add_service',
        _data={'name': 'SERVICE TWO'},
        _expected_status=403,
    )
