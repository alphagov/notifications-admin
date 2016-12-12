from bs4 import BeautifulSoup, element
from functools import partial
import pytest
from flask import url_for
from werkzeug.exceptions import InternalServerError
from unittest.mock import Mock, ANY
from freezegun import freeze_time
from tests.conftest import (
    mock_get_services,
    mock_get_services_with_no_services,
    mock_get_services_with_one_service
)
from app.main.views.feedback import has_live_services, in_business_hours


def no_redirect():
    return lambda _external=True: None


def test_logged_in_user_redirects_to_choose_service(app_,
                                                    api_user_active,
                                                    mock_get_user,
                                                    mock_get_user_by_email,
                                                    mock_login):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.index'))
            assert response.status_code == 302

            response = client.get(url_for('main.sign_in', follow_redirects=True))
            assert response.location == url_for('main.choose_service', _external=True)


def test_get_support_index_page(client):
    resp = client.get(url_for('main.support'))
    assert resp.status_code == 200


@freeze_time('2016-12-12 12:00:00.000000')
@pytest.mark.parametrize('support_type, expected_h1', [
    ('problem', 'Report a problem'),
    ('question', 'Ask a question or give feedback'),
])
@pytest.mark.parametrize('logged_in, expected_form_field, expected_contact_details', [
    (True, type(None), 'We’ll reply to test@user.gov.uk'),
    (True, type(None), 'We’ll reply to test@user.gov.uk'),
    (False, element.Tag, 'Leave your details below if you\'d like a response.'),
])
def test_choose_support_type(
    client,
    api_user_active,
    mock_get_user,
    mock_get_services,
    logged_in,
    expected_form_field,
    expected_contact_details,
    support_type,
    expected_h1
):
    if logged_in:
        client.login(api_user_active)
    response = client.post(
        url_for('main.support'),
        data={'support_type': support_type}, follow_redirects=True
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == expected_h1
    assert isinstance(page.find('input', {'name': 'name'}), expected_form_field)
    assert isinstance(page.find('input', {'name': 'email_address'}), expected_form_field)
    assert page.find('form').find('p').text.strip() == expected_contact_details


@freeze_time('2016-12-12 12:00:00.000000')
@pytest.mark.parametrize('ticket_type, expected_status_code', [
    ('problem', 200),
    ('question', 200),
    ('gripe', 404)
])
def test_get_feedback_page(client, ticket_type, expected_status_code):
    response = client.get(url_for('main.feedback', ticket_type=ticket_type))
    assert response.status_code == expected_status_code


@freeze_time("2016-12-12 12:00:00.000000")
@pytest.mark.parametrize('data, expected_message, expected_person_name, expected_email, logged_in, is_anonymous', [
    (
        {'feedback': "blah", 'name': 'Fred'},
        'Environment: http://localhost/\nFred (no email address supplied)\nblah',
        'Fred',
        'donotreply@notifications.service.gov.uk',
        False,
        True,
    ),
    (
        {'feedback': "blah"},
        'Environment: http://localhost/\n (no email address supplied)\nblah',
        None,
        'donotreply@notifications.service.gov.uk',
        False,
        True,
    ),
    (
        {'feedback': "blah", 'name': "Steve Irwin", 'email_address': 'rip@gmail.com'},
        'Environment: http://localhost/\n\nblah',
        'Steve Irwin',
        'rip@gmail.com',
        False,
        False,
    ),
    (
        {'feedback': "blah"},
        'Environment: http://localhost/\n\nblah',
        'Test User',
        'test@user.gov.uk',
        True,
        False,
    ),
])
@pytest.mark.parametrize('ticket_type', ['problem', 'question'])
def test_post_problem_or_question(
    client,
    api_user_active,
    mock_get_user,
    mock_get_services,
    mocker,
    ticket_type,
    data,
    expected_message,
    expected_person_name,
    expected_email,
    logged_in,
    is_anonymous,
):
    mock_post = mocker.patch(
        'app.main.views.feedback.requests.post',
        return_value=Mock(status_code=201)
    )
    if logged_in:
        client.login(api_user_active)
    resp = client.post(
        url_for('main.feedback', ticket_type=ticket_type),
        data=data,
    )
    assert resp.status_code == 302
    assert resp.location == url_for('main.thanks', urgent=True, anonymous=is_anonymous, _external=True)
    mock_post.assert_called_with(
        ANY,
        data={
            'department_id': ANY,
            'agent_team_id': ANY,
            'subject': 'Notify feedback',
            'message': expected_message,
            'person_email': expected_email,
            'person_name': expected_person_name,
            'label': ticket_type,
            'urgency': ANY,
        },
        headers=ANY
    )


@pytest.mark.parametrize('ticket_type, severe, is_in_business_hours, numeric_urgency, is_urgent', [

    # business hours, always urgent
    ('problem', True, True, 10, True),
    ('question', True, True, 10, True),
    ('problem', False, True, 10, True),
    ('question', False, True, 10, True),

    # out of hours, non emergency, never urgent
    ('problem', False, False, 1, False),
    ('question', False, False, 1, False),

    # out of hours, emergency problems are urgent
    ('problem', True, False, 10, True),
    ('question', True, False, 1, False),

])
def test_urgency(
    logged_in_client,
    api_user_active,
    mock_get_user,
    mock_get_services,
    mocker,
    ticket_type,
    severe,
    is_in_business_hours,
    numeric_urgency,
    is_urgent,
):
    mocker.patch('app.main.views.feedback.in_business_hours', return_value=is_in_business_hours)
    mock_post = mocker.patch('app.main.views.feedback.requests.post', return_value=Mock(status_code=201))
    response = logged_in_client.post(
        url_for('main.feedback', ticket_type=ticket_type, severe=severe),
        data={'feedback': "blah"},
    )
    assert response.status_code == 302
    assert response.location == url_for('main.thanks', urgent=is_urgent, anonymous=False, _external=True)
    assert mock_post.call_args[1]['data']['urgency'] == numeric_urgency


ids, params = zip(*[
    ('non-logged in users always have to triage', (
        'problem', False, False, True,
        302, partial(url_for, 'main.triage')
    )),
    ('trial services are never high priority', (
        'problem', False, True, False,
        200, no_redirect()
    )),
    ('we can triage in hours', (
        'problem', True, True, True,
        200, no_redirect()
    )),
    ('only problems are high priority', (
        'question', False, True, True,
        200, no_redirect()
    )),
    ('should triage out of hours', (
        'problem', False, True, True,
        302, partial(url_for, 'main.triage')
    ))
])


@pytest.mark.parametrize(
    (
        'ticket_type, is_in_business_hours, logged_in, has_live_services,'
        'expected_status, expected_redirect'
    ),
    params, ids=ids
)
def test_redirects_to_triage(
    client,
    api_user_active,
    mocker,
    mock_get_user,
    ticket_type,
    is_in_business_hours,
    logged_in,
    has_live_services,
    expected_status,
    expected_redirect,
):
    mocker.patch('app.main.views.feedback.has_live_services', return_value=has_live_services)
    mocker.patch('app.main.views.feedback.in_business_hours', return_value=is_in_business_hours)
    if logged_in:
        client.login(api_user_active)

    response = client.get(url_for('main.feedback', ticket_type=ticket_type))
    assert response.status_code == expected_status
    assert response.location == expected_redirect(_external=True)


@pytest.mark.parametrize('get_services_mock, expected_return_value', [
    (mock_get_services, True),
    (mock_get_services_with_no_services, False),
    (mock_get_services_with_one_service, False),
])
def test_has_live_services(
    mocker,
    fake_uuid,
    get_services_mock,
    expected_return_value
):
    get_services_mock(mocker, fake_uuid)
    assert has_live_services(12345) == expected_return_value


@pytest.mark.parametrize('when, is_in_business_hours', [

    ('2016-06-06 09:29:59', False),  # opening time, summer and winter
    ('2016-12-12 09:29:59', False),
    ('2016-06-06 09:30:00', True),
    ('2016-12-12 09:30:00', True),

    ('2016-12-12 12:00:00', True),   # middle of the day

    ('2016-12-12 17:29:59', True),   # closing time
    ('2016-12-12 17:30:00', False),

    ('2016-12-10 12:00:00', False),  # Saturday
    ('2016-12-11 12:00:00', False),  # Sunday
    ('2016-01-01 12:00:00', False),  # Bank holiday

])
def test_in_business_hours(when, is_in_business_hours):
    with freeze_time(when):
        assert in_business_hours() == is_in_business_hours


@pytest.mark.parametrize('choice, expected_redirect_param', [
    ('yes', True),
    ('no', False),
])
def test_triage_redirects_to_correct_url(client, mocker, choice, expected_redirect_param):
    response = client.post(url_for('main.triage'), data={'severe': choice})
    assert response.status_code == 302
    assert response.location == url_for(
        'main.feedback',
        ticket_type='problem',
        severe=expected_redirect_param,
        _external=True,
    )


@pytest.mark.parametrize('is_in_business_hours, severe, expected_status_code, expected_redirect', [
    (True, True, 200, no_redirect()),
    (True, False, 200, no_redirect()),
    (False, False, 200, no_redirect()),
    (False, True, 302, partial(url_for, 'main.bat_phone')),
])
def test_should_be_shown_the_bat_email(
    client,
    active_user_with_permissions,
    mocker,
    service_one,
    mock_get_services,
    is_in_business_hours,
    severe,
    expected_status_code,
    expected_redirect,
):

    mocker.patch('app.main.views.feedback.in_business_hours', return_value=is_in_business_hours)

    feedback_page = url_for('main.feedback', ticket_type='problem', severe=severe)

    response = client.get(feedback_page)

    assert response.status_code == expected_status_code
    assert response.location == expected_redirect(_external=True)

    # logged in users should never be redirected to the bat email page
    client.login(active_user_with_permissions, mocker, service_one)
    logged_in_response = client.get(feedback_page)
    assert logged_in_response.status_code == 200


def test_bat_email_page(
    client,
    active_user_with_permissions,
    mocker,
    service_one,
):

    bat_phone_page = url_for('main.bat_phone')

    response = client.get(bat_phone_page)
    assert response.status_code == 200

    client.login(active_user_with_permissions, mocker, service_one)
    logged_in_response = client.get(bat_phone_page)
    assert logged_in_response.status_code == 302
    assert logged_in_response.location == url_for('main.feedback', ticket_type='problem', _external=True)


@freeze_time('2016-12-12 12:00:00.000000')
@pytest.mark.parametrize('ticket_type', ['problem', 'question'])
def test_log_error_on_post(app_, mocker, ticket_type):
    mock_post = mocker.patch(
        'app.main.views.feedback.requests.post',
        return_value=Mock(
            status_code=401,
            json=lambda: {
                'error_code': 'invalid_auth',
                'error_message': 'Please provide a valid API key or token'}))
    with app_.test_request_context():
        mock_logger = mocker.patch.object(app_.logger, 'error')
        with app_.test_client() as client:
            with pytest.raises(InternalServerError):
                resp = client.post(
                    url_for('main.feedback', ticket_type=ticket_type),
                    data={'feedback': "blah", 'name': "Steve Irwin", 'email_address': 'rip@gmail.com'})
            assert mock_post.called
            mock_logger.assert_called_with(
                "Deskpro create ticket request failed with {} '{}'".format(mock_post().status_code, mock_post().json()))


@pytest.mark.parametrize('logged_in', [True, False])
@pytest.mark.parametrize('urgent, anonymous, message', [

    (True, False, 'We’ll get back to you within 30 minutes.'),
    (False, False, 'We’ll get back to you by the next working day.'),

    (True, True, 'We’ll look into it within 30 minutes.'),
    (False, True, 'We’ll look into it by the next working day.'),

])
def test_thanks(
    client,
    mocker,
    api_user_active,
    mock_get_user,
    urgent,
    anonymous,
    message,
    logged_in,
):
    if logged_in:
        client.login(api_user_active)
    response = client.get(url_for('main.thanks', urgent=urgent, anonymous=anonymous))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert ' '.join(page.find('main').find('p').text.split()) == message
