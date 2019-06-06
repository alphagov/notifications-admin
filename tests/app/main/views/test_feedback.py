from functools import partial
from unittest.mock import ANY

import pytest
from bs4 import BeautifulSoup, element
from flask import url_for
from freezegun import freeze_time

from app.main.views.feedback import (
    PROBLEM_TICKET_TYPE,
    QUESTION_TICKET_TYPE,
    has_live_services,
    in_business_hours,
)
from tests.conftest import (
    active_user_with_permissions,
    mock_get_services,
    mock_get_services_with_no_services,
    mock_get_services_with_one_service,
    normalize_spaces,
)


def no_redirect():
    return lambda _external=True: None


@pytest.mark.parametrize('endpoint', [
    'main.old_feedback',
    'main.support',
])
def test_get_support_index_page(
    client,
    endpoint,
):
    response = client.get(url_for('main.support'), follow_redirects=True)
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == 'Support'


@freeze_time('2016-12-12 12:00:00.000000')
@pytest.mark.parametrize('support_type, expected_h1', [
    (PROBLEM_TICKET_TYPE, 'Report a problem'),
    (QUESTION_TICKET_TYPE, 'Ask a question or give feedback'),
])
@pytest.mark.parametrize('logged_in, expected_form_field, expected_contact_details', [
    (True, type(None), 'We’ll reply to test@user.gov.uk'),
    (False, element.Tag, None),
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
    if expected_contact_details:
        assert page.find('form').find('p').text.strip() == expected_contact_details


@freeze_time('2016-12-12 12:00:00.000000')
@pytest.mark.parametrize('ticket_type, expected_status_code', [
    (PROBLEM_TICKET_TYPE, 200),
    (QUESTION_TICKET_TYPE, 200),
    ('gripe', 404)
])
def test_get_feedback_page(client, ticket_type, expected_status_code):
    response = client.get(url_for('main.feedback', ticket_type=ticket_type))
    assert response.status_code == expected_status_code


@pytest.mark.parametrize('prefilled_body, expected_textarea', [
    (
        'agreement',
        (
            'Please can you tell me if there’s an agreement in place '
            'between GOV.UK Notify and my organisation?'
        )
    ),
    (
        'foo',
        ''
    ),
])
@freeze_time('2016-12-12 12:00:00.000000')
def test_get_feedback_page_with_prefilled_body(
    client_request,
    mocker,
    fake_uuid,
    prefilled_body,
    expected_textarea,
):
    user = active_user_with_permissions(fake_uuid)
    user['email_address'] = 'test@marinemanagement.org.uk'
    mocker.patch('app.user_api_client.get_user', return_value=user)
    mock_post = mocker.patch('app.main.views.feedback.zendesk_client.create_ticket')
    page = client_request.get(
        'main.feedback',
        ticket_type=QUESTION_TICKET_TYPE,
        body=prefilled_body,
    )
    assert page.select_one('textarea').text == (
        expected_textarea
    )
    client_request.post(
        'main.feedback',
        ticket_type=QUESTION_TICKET_TYPE,
        body='agreement',
        _data={'feedback': 'blah', 'name': 'Example', 'email_address': 'test@example.com'}
    )
    message = mock_post.call_args[1]['message']
    assert message.startswith('blah')
    assert 'Please send' not in message


@freeze_time('2016-12-12 12:00:00.000000')
@pytest.mark.parametrize('ticket_type', [PROBLEM_TICKET_TYPE, QUESTION_TICKET_TYPE])
def test_passed_non_logged_in_user_details_through_flow(client, mocker, ticket_type):
    mock_post = mocker.patch('app.main.views.feedback.zendesk_client.create_ticket')

    data = {'feedback': 'blah', 'name': 'Steve Irwin', 'email_address': 'rip@gmail.com'}

    resp = client.post(
        url_for('main.feedback', ticket_type=ticket_type),
        data=data
    )

    assert resp.status_code == 302
    assert resp.location == url_for('main.thanks', urgent=True, anonymous=False, _external=True)
    mock_post.assert_called_with(
        subject='Notify feedback',
        message='blah\n',
        user_email='rip@gmail.com',
        user_name='Steve Irwin',
        ticket_type=ticket_type,
        p1=ANY
    )


@freeze_time("2016-12-12 12:00:00.000000")
@pytest.mark.parametrize('data', [
    {'feedback': 'blah'},
    {'feedback': 'blah', 'name': 'Ignored', 'email_address': 'ignored@email.com'}
])
@pytest.mark.parametrize('ticket_type', [PROBLEM_TICKET_TYPE, QUESTION_TICKET_TYPE])
def test_passes_user_details_through_flow(
    client_request,
    mocker,
    ticket_type,
    data
):
    mock_post = mocker.patch('app.main.views.feedback.zendesk_client.create_ticket')

    client_request.post(
        'main.feedback',
        ticket_type=ticket_type,
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.thanks',
            urgent=True,
            anonymous=False,
            _external=True,
        ),
    )

    mock_post.assert_called_with(
        subject='Notify feedback',
        message=ANY,
        user_email='test@user.gov.uk',
        user_name='Test User',
        ticket_type=ticket_type,
        p1=ANY
    )
    assert mock_post.call_args[1]['message'] == '\n'.join([
        'blah',
        'Service: "service one"',
        url_for(
            'main.service_dashboard',
            service_id='596364a0-858e-42c8-9062-a8fe822260eb',
            _external=True
        ),
        ''
    ])


@freeze_time('2016-12-12 12:00:00.000000')
@pytest.mark.parametrize('data', [
    {'feedback': 'blah', 'name': 'Fred'},
    {'feedback': 'blah'},
])
@pytest.mark.parametrize('ticket_type, expected_response, things_expected_in_url, expected_error', [
    (PROBLEM_TICKET_TYPE, 200, [], element.Tag),
    (QUESTION_TICKET_TYPE, 302, ['thanks', 'anonymous=True', 'urgent=True'], type(None)),
])
def test_email_address_required_for_problems(
    client,
    mocker,
    data,
    ticket_type,
    expected_response,
    things_expected_in_url,
    expected_error
):
    mocker.patch('app.main.views.feedback.zendesk_client')
    response = client.post(
        url_for('main.feedback', ticket_type=ticket_type),
        data=data,
    )
    assert response.status_code == expected_response
    # This is to work around non-deterministic query ordering in Flask url_for
    for thing in things_expected_in_url:
        assert thing in response.location
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert isinstance(page.find('span', {'class': 'error-message'}), expected_error)


@freeze_time('2016-12-12 12:00:00.000000')
@pytest.mark.parametrize('ticket_type', (
    PROBLEM_TICKET_TYPE, QUESTION_TICKET_TYPE
))
def test_email_address_must_be_valid_if_provided_to_support_form(
    client,
    mocker,
    ticket_type,
):
    response = client.post(
        url_for('main.feedback', ticket_type=ticket_type),
        data={
            'feedback': 'blah',
            'email_address': 'not valid',
        },
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(page.select_one('span.error-message').text) == (
        'Enter a valid email address'
    )


@pytest.mark.parametrize('ticket_type, severe, is_in_business_hours, is_urgent, is_p1', [

    # business hours, always urgent, never p1
    (PROBLEM_TICKET_TYPE, 'yes', True, True, False),
    (QUESTION_TICKET_TYPE, 'yes', True, True, False),
    (PROBLEM_TICKET_TYPE, 'no', True, True, False),
    (QUESTION_TICKET_TYPE, 'no', True, True, False),

    # out of hours, non emergency, never urgent, not p1
    (PROBLEM_TICKET_TYPE, 'no', False, False, False),
    (QUESTION_TICKET_TYPE, 'no', False, False, False),

    # out of hours, emergency problems are urgent and p1
    (PROBLEM_TICKET_TYPE, 'yes', False, True, True),
    (QUESTION_TICKET_TYPE, 'yes', False, False, False),

])
def test_urgency(
    client_request,
    mocker,
    ticket_type,
    severe,
    is_in_business_hours,
    is_urgent,
    is_p1,
):
    mocker.patch('app.main.views.feedback.in_business_hours', return_value=is_in_business_hours)
    mock_post = mocker.patch('app.main.views.feedback.zendesk_client.create_ticket')
    client_request.post(
        'main.feedback',
        ticket_type=ticket_type,
        severe=severe,
        _data={'feedback': 'blah', 'email_address': 'test@example.com'},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.thanks',
            urgent=is_urgent,
            anonymous=False,
            _external=True,
        ),
    )
    assert mock_post.call_args[1]['p1'] == is_p1


ids, params = zip(*[
    ('non-logged in users always have to triage', (
        PROBLEM_TICKET_TYPE, False, False, True,
        302, partial(url_for, 'main.triage')
    )),
    ('trial services are never high priority', (
        PROBLEM_TICKET_TYPE, False, True, False,
        200, no_redirect()
    )),
    ('we can triage in hours', (
        PROBLEM_TICKET_TYPE, True, True, True,
        200, no_redirect()
    )),
    ('only problems are high priority', (
        QUESTION_TICKET_TYPE, False, True, True,
        200, no_redirect()
    )),
    ('should triage out of hours', (
        PROBLEM_TICKET_TYPE, False, True, True,
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


def test_doesnt_lose_message_if_post_across_closing(
    client_request,
    mocker,
):

    mocker.patch('app.main.views.feedback.has_live_services', return_value=True)
    mocker.patch('app.main.views.feedback.in_business_hours', return_value=False)

    page = client_request.post(
        'main.feedback',
        ticket_type=PROBLEM_TICKET_TYPE,
        _data={'feedback': 'foo'},
        _expected_status=302,
        _expected_redirect=url_for('.triage', _external=True),
    )
    with client_request.session_transaction() as session:
        assert session['feedback_message'] == 'foo'

    page = client_request.get(
        'main.feedback',
        ticket_type=PROBLEM_TICKET_TYPE,
        severe='yes',
    )

    with client_request.session_transaction() as session:
        assert page.find('textarea', {'name': 'feedback'}).text == 'foo'
        assert 'feedback_message' not in session


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

    ('2016-06-06 09:29:59+0100', False),  # opening time, summer and winter
    ('2016-12-12 09:29:59+0000', False),
    ('2016-06-06 09:30:00+0100', True),
    ('2016-12-12 09:30:00+0000', True),

    ('2016-12-12 12:00:00+0000', True),   # middle of the day

    ('2016-12-12 17:29:59+0000', True),   # closing time
    ('2016-12-12 17:30:00+0000', False),

    ('2016-12-10 12:00:00+0000', False),  # Saturday
    ('2016-12-11 12:00:00+0000', False),  # Sunday
    ('2016-01-01 12:00:00+0000', False),  # Bank holiday

])
def test_in_business_hours(when, is_in_business_hours):
    with freeze_time(when):
        assert in_business_hours() == is_in_business_hours


@pytest.mark.parametrize('choice, expected_redirect_param', [
    ('yes', 'yes'),
    ('no', 'no'),
])
def test_triage_redirects_to_correct_url(client, choice, expected_redirect_param):
    response = client.post(url_for('main.triage'), data={'severe': choice})
    assert response.status_code == 302
    assert response.location == url_for(
        'main.feedback',
        ticket_type=PROBLEM_TICKET_TYPE,
        severe=expected_redirect_param,
        _external=True,
    )


@pytest.mark.parametrize(
    (
        'is_in_business_hours, severe,'
        'expected_status_code, expected_redirect,'
        'expected_status_code_when_logged_in, expected_redirect_when_logged_in'
    ),
    [
        (
            True, 'yes',
            200, no_redirect(),
            200, no_redirect()
        ),
        (
            True, 'no',
            200, no_redirect(),
            200, no_redirect()
        ),
        (
            False, 'no',
            200, no_redirect(),
            200, no_redirect(),
        ),

        # Treat empty query param as mangled URL – ask question again
        (
            False, '',
            302, partial(url_for, 'main.triage'),
            302, partial(url_for, 'main.triage'),
        ),

        # User hasn’t answered the triage question
        (
            False, None,
            302, partial(url_for, 'main.triage'),
            302, partial(url_for, 'main.triage'),
        ),

        # Escalation is needed for non-logged-in users
        (
            False, 'yes',
            302, partial(url_for, 'main.bat_phone'),
            200, no_redirect(),
        ),
    ]
)
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
    expected_status_code_when_logged_in,
    expected_redirect_when_logged_in,
):

    mocker.patch('app.main.views.feedback.in_business_hours', return_value=is_in_business_hours)

    feedback_page = url_for('main.feedback', ticket_type=PROBLEM_TICKET_TYPE, severe=severe)

    response = client.get(feedback_page)

    assert response.status_code == expected_status_code
    assert response.location == expected_redirect(_external=True)

    # logged in users should never be redirected to the bat email page
    client.login(active_user_with_permissions, mocker, service_one)
    logged_in_response = client.get(feedback_page)
    assert logged_in_response.status_code == expected_status_code_when_logged_in
    assert logged_in_response.location == expected_redirect_when_logged_in(_external=True)


def test_bat_email_page(
    client,
    active_user_with_permissions,
    mocker,
    service_one,
):
    bat_phone_page = url_for('main.bat_phone')

    response = client.get(bat_phone_page)
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.select('main a')[1].text == 'Fill in this form'
    assert page.select('main a')[1]['href'] == url_for('main.feedback', ticket_type=PROBLEM_TICKET_TYPE, severe='no')
    next_page_response = client.get(page.select('main a')[1]['href'])
    next_page = BeautifulSoup(next_page_response.data.decode('utf-8'), 'html.parser')
    assert next_page.h1.text.strip() == 'Report a problem'

    client.login(active_user_with_permissions, mocker, service_one)
    logged_in_response = client.get(bat_phone_page)
    assert logged_in_response.status_code == 302
    assert logged_in_response.location == url_for('main.feedback', ticket_type=PROBLEM_TICKET_TYPE, _external=True)


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
