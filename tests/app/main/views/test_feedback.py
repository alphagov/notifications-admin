from bs4 import BeautifulSoup
from functools import partial
import pytest
from flask import url_for
from werkzeug.exceptions import InternalServerError
from unittest.mock import Mock, ANY


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


@pytest.mark.parametrize('support_type, expected_h1', [
    ('problem', 'Report a problem'),
    ('question', 'Ask a question or give feedback'),
])
def test_choose_support_type(client, support_type, expected_h1):
    response = client.post(
        url_for('main.support'),
        data={'support_type': support_type}, follow_redirects=True
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == expected_h1


@pytest.mark.parametrize('ticket_type, expected_status_code', [
    ('problem', 200),
    ('question', 200),
    ('gripe', 404)
])
def test_get_feedback_page(client, ticket_type, expected_status_code):
    response = client.get(url_for('main.feedback', ticket_type=ticket_type))
    assert response.status_code == expected_status_code


@pytest.mark.parametrize('data, expected_message, expected_person_name, expected_email', [
    (
        {'feedback': "blah", 'name': 'Fred'},
        'Environment: http://localhost/\nFred (no email address supplied)\nblah',
        'Fred',
        'donotreply@notifications.service.gov.uk',
    ),
    (
        {'feedback': "blah"},
        'Environment: http://localhost/\n (no email address supplied)\nblah',
        None,
        'donotreply@notifications.service.gov.uk',
    ),
    (
        {'feedback': "blah", 'name': "Steve Irwin", 'email_address': 'rip@gmail.com'},
        'Environment: http://localhost/\n\nblah',
        'Steve Irwin',
        'rip@gmail.com',
    ),
])
@pytest.mark.parametrize('ticket_type', ['problem', 'question'])
def test_post_feedback_with_name_but_no_email(
    client,
    mocker,
    ticket_type,
    data,
    expected_message,
    expected_person_name,
    expected_email,
):
    mock_post = mocker.patch(
        'app.main.views.feedback.requests.post',
        return_value=Mock(status_code=201)
    )
    resp = client.post(
        url_for('main.feedback', ticket_type=ticket_type),
        data=data,
    )
    assert resp.status_code == 302
    mock_post.assert_called_with(
        ANY,
        data={
            'department_id': ANY,
            'agent_team_id': ANY,
            'subject': 'Notify feedback',
            'message': expected_message.format(ticket_type),
            'person_email': expected_email,
            'person_name': expected_person_name,
            'label': ticket_type,
        },
        headers=ANY
    )


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
