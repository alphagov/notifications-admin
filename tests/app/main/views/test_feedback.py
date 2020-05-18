from functools import partial
from unittest.mock import ANY

import pytest
from bs4 import BeautifulSoup, element
from flask import url_for
from freezegun import freeze_time

from app.main.views.feedback import has_live_services, in_business_hours
from app.models.feedback import (
    GENERAL_TICKET_TYPE,
    PROBLEM_TICKET_TYPE,
    QUESTION_TICKET_TYPE,
)
from tests.conftest import normalize_spaces


def no_redirect():
    return lambda _external=True: None


def test_get_support_index_page(
    client_request,
):
    page = client_request.get('.support')
    assert page.select_one('form')['method'] == 'post'
    assert 'action' not in page.select_one('form')
    assert normalize_spaces(page.select_one('h1').text) == 'Support'
    assert normalize_spaces(
        page.select_one('form label[for=support_type-0]').text
    ) == 'Report a problem'
    assert page.select_one('form input#support_type-0')['value'] == 'report-problem'
    assert normalize_spaces(
        page.select_one('form label[for=support_type-1]').text
    ) == 'Ask a question or give feedback'
    assert page.select_one('form input#support_type-1')['value'] == 'ask-question-give-feedback'
    assert normalize_spaces(
        page.select_one('form button[type=submit]').text
    ) == 'Continue'


def test_get_support_index_page_when_signed_out(
    client_request,
):
    client_request.logout()
    page = client_request.get('.support')
    assert page.select_one('form')['method'] == 'post'
    assert 'action' not in page.select_one('form')
    assert normalize_spaces(
        page.select_one('form label[for=who-0]').text
    ) == (
        'I work in the public sector and need to send emails, text messages or letters'
    )
    assert page.select_one('form input#who-0')['value'] == 'public-sector'
    assert normalize_spaces(
        page.select_one('form label[for=who-1]').text
    ) == (
        'I’m a member of the public with a question for the government'
    )
    assert page.select_one('form input#who-1')['value'] == 'public'
    assert normalize_spaces(
        page.select_one('form button[type=submit]').text
    ) == 'Continue'


@freeze_time('2016-12-12 12:00:00.000000')
@pytest.mark.parametrize('support_type, expected_h1', [
    (PROBLEM_TICKET_TYPE, 'Report a problem'),
    (QUESTION_TICKET_TYPE, 'Ask a question or give feedback'),
])
def test_choose_support_type(
    client_request,
    support_type,
    expected_h1
):
    page = client_request.post(
        'main.support',
        _data={'support_type': support_type},
        _follow_redirects=True,
    )
    assert page.h1.string.strip() == expected_h1
    assert not page.select_one('input[name=name]')
    assert not page.select_one('input[name=email_address]')
    assert page.find('form').find('p').text.strip() == (
        'We’ll reply to test@user.gov.uk'
    )


@freeze_time('2016-12-12 12:00:00.000000')
def test_get_support_as_someone_in_the_public_sector(
    client_request,
):
    client_request.logout()
    page = client_request.post(
        'main.support',
        _data={'who': 'public-sector'},
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select('h1')) == (
        'Contact GOV.UK Notify support'
    )
    assert page.select_one('form textarea[name=feedback]')
    assert page.select_one('form input[name=name]')
    assert page.select_one('form input[name=email_address]')
    assert page.select_one('form button[type=submit]')


def test_get_support_as_member_of_public(
    client_request,
):
    client_request.logout()
    page = client_request.post(
        'main.support',
        _data={'who': 'public'},
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select('h1')) == (
        'The GOV.UK Notify service is for people who work in the government'
    )
    assert len(page.select('h2 a')) == 3
    assert not page.select('form')
    assert not page.select('input')
    assert not page.select('form [type=submit]')


@freeze_time('2016-12-12 12:00:00.000000')
@pytest.mark.parametrize('ticket_type, expected_status_code', [
    (PROBLEM_TICKET_TYPE, 200),
    (QUESTION_TICKET_TYPE, 200),
    ('gripe', 404)
])
def test_get_feedback_page(client, ticket_type, expected_status_code):
    response = client.get(url_for('main.feedback', ticket_type=ticket_type))
    assert response.status_code == expected_status_code


@freeze_time('2016-12-12 12:00:00.000000')
@pytest.mark.parametrize('ticket_type', [PROBLEM_TICKET_TYPE, QUESTION_TICKET_TYPE])
def test_passed_non_logged_in_user_details_through_flow(client, mocker, ticket_type):
    mock_post = mocker.patch(
        'app.main.views.feedback.zendesk_client.create_ticket',
        return_value={'id': 12345},
    )
    mock_logger = mocker.patch('app.current_app.logger.info')

    data = {'feedback': 'blah', 'name': 'Steve Irwin', 'email_address': 'rip@gmail.com'}

    resp = client.post(
        url_for('main.feedback', ticket_type=ticket_type),
        data=data
    )

    assert resp.status_code == 302
    assert resp.location == url_for(
        'main.thanks',
        out_of_hours_emergency=False,
        email_address_provided=True,
        _external=True,
    )
    mock_post.assert_called_with(
        subject='Notify feedback',
        message='blah\n',
        user_email='rip@gmail.com',
        user_name='Steve Irwin',
        ticket_type=ticket_type,
        p1=ANY
    )
    mock_logger.assert_called_once_with('Created Zendesk ticket 12345')


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
            email_address_provided=True,
            out_of_hours_emergency=False,
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
@pytest.mark.parametrize('ticket_type', [
    PROBLEM_TICKET_TYPE,
    QUESTION_TICKET_TYPE,
])
def test_email_address_required_for_problems_and_questions(
    client_request,
    mocker,
    data,
    ticket_type,
):
    mocker.patch('app.main.views.feedback.zendesk_client')
    client_request.logout()
    page = client_request.post(
        'main.feedback',
        ticket_type=ticket_type,
        _data=data,
        _expected_status=200
    )
    assert isinstance(page.find('span', {'class': 'error-message'}), element.Tag)


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


@pytest.mark.parametrize('ticket_type, severe, is_in_business_hours, is_out_of_hours_emergency', [

    # business hours, never an emergency
    (PROBLEM_TICKET_TYPE, 'yes', True, False),
    (QUESTION_TICKET_TYPE, 'yes', True, False),
    (PROBLEM_TICKET_TYPE, 'no', True, False),
    (QUESTION_TICKET_TYPE, 'no', True, False),

    # out of hours, if the user says it’s not an emergency
    (PROBLEM_TICKET_TYPE, 'no', False, False),
    (QUESTION_TICKET_TYPE, 'no', False, False),

    # out of hours, only problems can be emergencies
    (PROBLEM_TICKET_TYPE, 'yes', False, True),
    (QUESTION_TICKET_TYPE, 'yes', False, False),

])
def test_urgency(
    client_request,
    mocker,
    ticket_type,
    severe,
    is_in_business_hours,
    is_out_of_hours_emergency,
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
            out_of_hours_emergency=is_out_of_hours_emergency,
            email_address_provided=True,
            _external=True,
        ),
    )
    assert mock_post.call_args[1]['p1'] == is_out_of_hours_emergency


ids, params = zip(*[
    ('non-logged in users always have to triage', (
        GENERAL_TICKET_TYPE, False, False, True,
        302, partial(url_for, 'main.triage', ticket_type=GENERAL_TICKET_TYPE)
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
        302, partial(url_for, 'main.triage', ticket_type=PROBLEM_TICKET_TYPE)
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


@pytest.mark.parametrize('ticket_type, expected_h1', (
    (PROBLEM_TICKET_TYPE, 'Report a problem'),
    (GENERAL_TICKET_TYPE, 'Contact GOV.UK Notify support'),
))
def test_options_on_triage_page(
    client_request,
    ticket_type,
    expected_h1,
):
    page = client_request.get('main.triage', ticket_type=ticket_type)
    assert normalize_spaces(page.select_one('h1').text) == expected_h1
    assert page.select('form input[type=radio]')[0]['value'] == 'yes'
    assert page.select('form input[type=radio]')[1]['value'] == 'no'


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
        _expected_redirect=url_for('.triage', ticket_type=PROBLEM_TICKET_TYPE, _external=True),
    )
    with client_request.session_transaction() as session:
        assert session['feedback_message'] == 'foo'

    page = client_request.get(
        'main.feedback',
        ticket_type=PROBLEM_TICKET_TYPE,
        severe='yes',
    )

    with client_request.session_transaction() as session:
        assert page.find('textarea', {'name': 'feedback'}).text == '\r\nfoo'
        assert 'feedback_message' not in session


def test_has_live_services(mock_get_services):
    assert has_live_services(12345) is True


def test_has_live_services_when_there_are_no_services(mock_get_services_with_no_services):
    assert has_live_services(12345) is False


def test_has_live_services_when_service_is_not_live(mock_get_services_with_one_service):
    assert has_live_services(12345) is False


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


@pytest.mark.parametrize('ticket_type', (
    GENERAL_TICKET_TYPE,
    PROBLEM_TICKET_TYPE,
))
@pytest.mark.parametrize('choice, expected_redirect_param', [
    ('yes', 'yes'),
    ('no', 'no'),
])
def test_triage_redirects_to_correct_url(
    client_request,
    ticket_type,
    choice,
    expected_redirect_param,
):
    client_request.post(
        'main.triage',
        ticket_type=ticket_type,
        _data={'severe': choice},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.feedback',
            ticket_type=ticket_type,
            severe=expected_redirect_param,
            _external=True,
        ),
    )


@pytest.mark.parametrize('extra_args, expected_back_link', [
    (
        {'severe': 'yes'},
        partial(url_for, 'main.triage', ticket_type=PROBLEM_TICKET_TYPE)
    ),
    (
        {'severe': 'no'},
        partial(url_for, 'main.triage', ticket_type=PROBLEM_TICKET_TYPE)
    ),
    (
        {'severe': 'foo'},  # hacking the URL
        partial(url_for, 'main.support')
    ),
    (
        {},
        partial(url_for, 'main.support')
    ),
])
def test_back_link_from_form(
    client_request,
    extra_args,
    expected_back_link,
):
    page = client_request.get(
        'main.feedback',
        ticket_type=PROBLEM_TICKET_TYPE,
        **extra_args
    )
    assert page.select_one('.govuk-back-link')['href'] == expected_back_link()
    assert normalize_spaces(page.select_one('h1').text) == 'Report a problem'


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
            302, partial(url_for, 'main.triage', ticket_type=PROBLEM_TICKET_TYPE),
            302, partial(url_for, 'main.triage', ticket_type=PROBLEM_TICKET_TYPE),
        ),

        # User hasn’t answered the triage question
        (
            False, None,
            302, partial(url_for, 'main.triage', ticket_type=PROBLEM_TICKET_TYPE),
            302, partial(url_for, 'main.triage', ticket_type=PROBLEM_TICKET_TYPE),
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


@pytest.mark.parametrize(
    (
        'severe,'
        'expected_status_code, expected_redirect,'
        'expected_status_code_when_logged_in, expected_redirect_when_logged_in'
    ),
    [
        # User hasn’t answered the triage question
        (
            None,
            302, partial(url_for, 'main.triage', ticket_type=GENERAL_TICKET_TYPE),
            302, partial(url_for, 'main.triage', ticket_type=GENERAL_TICKET_TYPE),
        ),

        # Escalation is needed for non-logged-in users
        (
            'yes',
            302, partial(url_for, 'main.bat_phone'),
            200, no_redirect(),
        ),
    ]
)
def test_should_be_shown_the_bat_email_for_general_questions(
    client,
    active_user_with_permissions,
    mocker,
    service_one,
    mock_get_services,
    severe,
    expected_status_code,
    expected_redirect,
    expected_status_code_when_logged_in,
    expected_redirect_when_logged_in,
):

    mocker.patch('app.main.views.feedback.in_business_hours', return_value=False)

    feedback_page = url_for('main.feedback', ticket_type=GENERAL_TICKET_TYPE, severe=severe)

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
    assert page.select('main a')[0].text == 'Back'
    assert page.select('main a')[0]['href'] == url_for('main.support')
    assert page.select('main a')[2].text == 'Fill in this form'
    assert page.select('main a')[2]['href'] == url_for('main.feedback', ticket_type=PROBLEM_TICKET_TYPE, severe='no')
    next_page_response = client.get(page.select('main a')[2]['href'])
    next_page = BeautifulSoup(next_page_response.data.decode('utf-8'), 'html.parser')
    assert next_page.h1.text.strip() == 'Report a problem'

    client.login(active_user_with_permissions, mocker, service_one)
    logged_in_response = client.get(bat_phone_page)
    assert logged_in_response.status_code == 302
    assert logged_in_response.location == url_for('main.feedback', ticket_type=PROBLEM_TICKET_TYPE, _external=True)


@pytest.mark.parametrize('out_of_hours_emergency, email_address_provided, out_of_hours, message', (

    # Out of hours emergencies trump everything else
    (
        True, True, True,
        'We’ll reply in the next 30 minutes.',
    ),
    (
        True, False, False,  # Not a real scenario
        'We’ll reply in the next 30 minutes.',
    ),

    # Anonymous tickets don’t promise a reply
    (
        False, False, False,
        'We’ll read your message in the next 30 minutes.',
    ),
    (
        False, False, True,
        'We’ll read your message when we’re back in the office.',
    ),

    # When we look at your ticket depends on whether we’re in normal
    # business hours
    (
        False, True, False,
        'We’ll read your message in the next 30 minutes and reply within one working day.',
    ),
    (
        False, True, True,
        'We’ll reply within one working day.'
    ),

))
def test_thanks(
    client_request,
    mocker,
    api_user_active,
    mock_get_user,
    out_of_hours_emergency,
    email_address_provided,
    out_of_hours,
    message,
):
    mocker.patch('app.main.views.feedback.in_business_hours', return_value=(not out_of_hours))
    page = client_request.get(
        'main.thanks',
        out_of_hours_emergency=out_of_hours_emergency,
        email_address_provided=email_address_provided,
    )
    assert normalize_spaces(page.find('main').find('p').text) == message
