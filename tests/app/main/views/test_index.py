import pytest
from flask import (url_for, current_app)
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


def test_get_feedback_page(app_):
    with app_.test_request_context():
        with app_.test_client() as client:
            resp = client.get(url_for('main.feedback'))
            assert resp.status_code == 200


def test_post_feedback_with_no_name_email(app_, mocker):
    mock_post = mocker.patch(
        'app.main.views.index.requests.post',
        return_value=Mock(status_code=201))
    with app_.test_request_context():
        with app_.test_client() as client:
            resp = client.post(url_for('main.feedback'), data={'feedback': "blah"})
            assert resp.status_code == 302


def test_post_feedback_with_no_name_email(app_, mocker):
    mock_post = mocker.patch(
        'app.main.views.index.requests.post',
        return_value=Mock(status_code=201))
    with app_.test_request_context():
        with app_.test_client() as client:
            resp = client.post(url_for('main.feedback'), data={'feedback': "blah"})
            assert resp.status_code == 302
            mock_post.assert_called_with(
                ANY,
                data={
                    'agent_team_id': ANY,
                    'subject': 'Notify feedback',
                    'message': '\n\nblah',
                    'person_email': ANY},
                headers=ANY)


def test_post_feedback_with_name_email(app_, mocker):
    mock_post = mocker.patch(
        'app.main.views.index.requests.post',
        return_value=Mock(status_code=201))
    with app_.test_request_context():
        with app_.test_client() as client:
            resp = client.post(
                url_for('main.feedback'),
                data={'feedback': "blah", 'name': "Steve Irwin", 'email_address': 'rip@gmail.com'})
            assert resp.status_code == 302
            mock_post.assert_called_with(
                ANY,
                data={
                    'subject': 'Notify feedback',
                    'agent_team_id': ANY,
                    'message': 'Steve Irwin\nrip@gmail.com\nblah',
                    'person_email': ANY},
                headers=ANY)


def test_log_error_on_post(app_, mocker):
    mock_post = mocker.patch(
        'app.main.views.index.requests.post',
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
                    url_for('main.feedback'),
                    data={'feedback': "blah", 'name': "Steve Irwin", 'email_address': 'rip@gmail.com'})
            mock_post.assert_called_with(
                ANY,
                data={
                    'subject': 'Notify feedback',
                    'agent_team_id': ANY,
                    'message': 'Steve Irwin\nrip@gmail.com\nblah',
                    'person_email': ANY},
                headers=ANY)
            mock_logger.assert_called_with(
                "Deskpro create ticket request failed with {} '{}'".format(mock_post().status_code, mock_post().json()))
