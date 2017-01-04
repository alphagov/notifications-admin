from functools import partial
from itertools import repeat
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError

from tests import validate_route_permission, template_json, single_notification_json
from tests.conftest import (
    mock_get_service_email_template,
    mock_get_template_version,
)
from app.main.views.templates import get_last_use_message, get_human_readable_delta


def test_should_show_page_for_one_template(
        app_,
        api_user_active,
        mock_login,
        mock_get_service,
        mock_get_service_template,
        mock_get_user,
        mock_get_user_by_email,
        mock_has_permissions,
        fake_uuid
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            template_id = fake_uuid
            response = client.get(url_for(
                '.edit_service_template',
                service_id=service_id,
                template_id=template_id))

    assert response.status_code == 200
    assert "Two week reminder" in response.get_data(as_text=True)
    assert "Your vehicle tax is about to expire" in response.get_data(as_text=True)
    mock_get_service_template.assert_called_with(
        service_id, template_id)


@pytest.mark.parametrize('view_suffix, expected_content_type', [
    ('as_pdf', 'application/pdf'),
    ('as_png', 'image/png'),
])
@pytest.mark.parametrize('view, extra_view_args', [
    ('.view_letter_template', {}),
    ('.view_template_version', {'version': 1}),
])
@patch('app.main.views.templates.LetterPreviewTemplate.jinja_template.render', return_value='foo')
def test_should_show_preview_letter_templates(
    mock_letter_preview,
    view,
    extra_view_args,
    view_suffix,
    expected_content_type,
    client,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_email_template,
    mock_get_user,
    mock_get_user_by_email,
    mock_has_permissions,
    fake_uuid,
    mocker
):
    client.login(api_user_active)
    service_id, template_id = repeat(fake_uuid, 2)
    response = client.get(url_for(
        '{}_{}'.format(view, view_suffix),
        service_id=service_id,
        template_id=template_id,
        **extra_view_args
    ))

    assert response.status_code == 200
    assert response.content_type == expected_content_type
    mock_get_service_email_template.assert_called_with(service_id, template_id, **extra_view_args)
    print(mock_letter_preview)
    print(mock_letter_preview.call_args)
    assert mock_letter_preview.call_args[0][0]['message'] == (
        "<h2>Your <span class='placeholder'>((thing))</span> is due soon</h2>\n"
        "<p>Your vehicle tax expires on <span class='placeholder'>((date))</span></p>"
    )


def test_should_redirect_when_saving_a_template(app_,
                                                api_user_active,
                                                mock_login,
                                                mock_get_service_template,
                                                mock_update_service_template,
                                                mock_get_user,
                                                mock_get_service,
                                                mock_get_user_by_email,
                                                mock_has_permissions,
                                                fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            template_id = fake_uuid
            name = "new name"
            content = "template content"
            data = {
                'id': template_id,
                'name': name,
                'template_content': content,
                'template_type': 'sms',
                'service': service_id
            }
            response = client.post(url_for(
                '.edit_service_template',
                service_id=service_id,
                template_id=template_id), data=data)

            assert response.status_code == 302
            assert response.location == url_for(
                '.view_template', service_id=service_id, template_id=template_id, _external=True)
            mock_update_service_template.assert_called_with(
                template_id, name, 'sms', content, service_id, None)


def test_should_show_interstitial_when_making_breaking_change(
        app_,
        api_user_active,
        mock_login,
        mock_get_service_email_template,
        mock_update_service_template,
        mock_get_user,
        mock_get_service,
        mock_get_user_by_email,
        mock_has_permissions,
        fake_uuid
):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            template_id = fake_uuid
            response = client.post(
                url_for('.edit_service_template', service_id=service_id, template_id=template_id),
                data={
                    'id': template_id,
                    'name': "new name",
                    'template_content': "hello",
                    'template_type': 'email',
                    'subject': 'reminder',
                    'service': service_id
                }
            )

            assert response.status_code == 200
            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            assert page.h1.string.strip() == "Confirm changes"

            for key, value in {
                'name': 'new name',
                'subject': 'reminder',
                'template_content': 'hello',
                'confirm': 'true'
            }.items():
                assert page.find('input', {'name': key})['value'] == value


def test_should_not_create_too_big_template(app_,
                                            api_user_active,
                                            mock_login,
                                            mock_get_service_template,
                                            mock_get_user,
                                            mock_get_service,
                                            mock_get_user_by_email,
                                            mock_create_service_template_content_too_big,
                                            mock_has_permissions,
                                            fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            template_type = 'sms'
            data = {
                'name': "new name",
                'template_content': "template content",
                'template_type': template_type,
                'service': service_id
            }
            resp = client.post(url_for(
                '.add_service_template',
                service_id=service_id,
                template_type=template_type
            ), data=data)

            assert resp.status_code == 200
            assert "Content has a character count greater than the limit of 459" in resp.get_data(as_text=True)


def test_should_not_update_too_big_template(app_,
                                            api_user_active,
                                            mock_login,
                                            mock_get_service_template,
                                            mock_get_user,
                                            mock_get_service,
                                            mock_get_user_by_email,
                                            mock_update_service_template_400_content_too_big,
                                            mock_has_permissions,
                                            fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            template_type = 'sms'
            template_id = fake_uuid
            data = {
                'id': fake_uuid,
                'name': "new name",
                'template_content': "template content",
                'service': service_id,
                'template_type': 'sms'
            }
            resp = client.post(url_for(
                '.edit_service_template',
                service_id=service_id,
                template_id=template_id), data=data)

            assert resp.status_code == 200
            assert "Content has a character count greater than the limit of 459" in resp.get_data(as_text=True)


def test_should_redirect_when_saving_a_template_email(app_,
                                                      api_user_active,
                                                      mock_login,
                                                      mock_get_service_email_template,
                                                      mock_update_service_template,
                                                      mock_get_user,
                                                      mock_get_service,
                                                      mock_get_user_by_email,
                                                      mock_has_permissions,
                                                      fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            template_id = fake_uuid
            name = "new name"
            content = "template content ((thing)) ((date))"
            subject = "subject"
            data = {
                'id': template_id,
                'name': name,
                'template_content': content,
                'template_type': 'email',
                'service': service_id,
                'subject': subject
            }
            response = client.post(url_for(
                '.edit_service_template',
                service_id=service_id,
                template_id=template_id), data=data)
            assert response.status_code == 302
            assert response.location == url_for(
                '.view_template',
                service_id=service_id,
                template_id=template_id,
                _external=True)
            mock_update_service_template.assert_called_with(
                template_id, name, 'email', content, service_id, subject)


def test_should_show_delete_template_page_with_time_block(app_,
                                                          api_user_active,
                                                          mock_login,
                                                          mock_get_service,
                                                          mock_get_service_template,
                                                          mock_get_user,
                                                          mock_get_user_by_email,
                                                          mock_has_permissions,
                                                          fake_uuid,
                                                          mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            with freeze_time('2012-01-01 12:00:00'):
                template = template_json('1234', '1234', "Test template", "sms", "Something very interesting")
                notification = single_notification_json('1234', template=template)

                mocker.patch('app.template_statistics_client.get_template_statistics_for_template',
                             return_value=notification)

            with freeze_time('2012-01-01 12:10:00'):
                client.login(api_user_active)
                service_id = fake_uuid
                template_id = fake_uuid
                response = client.get(url_for(
                    '.delete_service_template',
                    service_id=service_id,
                    template_id=template_id))
    content = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Test template was last used 10 minutes ago. Are you sure you want to delete it?' in content
    assert 'Are you sure' in content
    assert 'Two week reminder' in content
    assert 'Your vehicle tax is about to expire' in content
    mock_get_service_template.assert_called_with(service_id, template_id)


def test_should_show_delete_template_page_with_never_used_block(app_,
                                                                api_user_active,
                                                                mock_login,
                                                                mock_get_service,
                                                                mock_get_service_template,
                                                                mock_get_user,
                                                                mock_get_user_by_email,
                                                                mock_has_permissions,
                                                                fake_uuid,
                                                                mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            mocker.patch(
                'app.template_statistics_client.get_template_statistics_for_template',
                side_effect=HTTPError(response=Mock(status_code=404), message="Default message")
            )

            client.login(api_user_active)
            service_id = fake_uuid
            template_id = fake_uuid
            response = client.get(url_for(
                '.delete_service_template',
                service_id=service_id,
                template_id=template_id))

            content = response.get_data(as_text=True)
            assert response.status_code == 200
            assert 'Two week reminder has never been used. Are you sure you want to delete it?' in content
            assert 'Are you sure' in content
            assert 'Two week reminder' in content
            assert 'Your vehicle tax is about to expire' in content
            mock_get_service_template.assert_called_with(service_id, template_id)


def test_should_redirect_when_deleting_a_template(app_,
                                                  api_user_active,
                                                  mock_login,
                                                  mock_get_service,
                                                  mock_get_service_template,
                                                  mock_delete_service_template,
                                                  mock_get_user,
                                                  mock_get_user_by_email,
                                                  mock_has_permissions,
                                                  fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            template_id = fake_uuid
            name = "new name"
            type_ = "sms"
            content = "template content"
            data = {
                'id': str(template_id),
                'name': name,
                'template_type': type_,
                'content': content,
                'service': service_id
            }
            response = client.post(url_for(
                '.delete_service_template',
                service_id=service_id,
                template_id=template_id
            ), data=data)

            assert response.status_code == 302
            assert response.location == url_for(
                '.choose_template',
                service_id=service_id, template_type=type_, _external=True)
            mock_get_service_template.assert_called_with(
                service_id, template_id)
            mock_delete_service_template.assert_called_with(
                service_id, template_id)


@freeze_time('2016-01-01T15:00')
def test_should_show_page_for_a_deleted_template(
        app_,
        api_user_active,
        mock_login,
        mock_get_service,
        mock_get_deleted_template,
        mock_get_user,
        mock_get_user_by_email,
        mock_has_permissions,
        fake_uuid
):
    with app_.test_request_context(), app_.test_client() as client:
        client.login(api_user_active)
        service_id = fake_uuid
        template_id = fake_uuid
        response = client.get(url_for(
            '.view_template',
            service_id=service_id,
            template_id=template_id
        ))

        assert response.status_code == 200

        content = response.get_data(as_text=True)
        assert url_for("main.edit_service_template", service_id=fake_uuid, template_id=fake_uuid) not in content
        assert url_for("main.send_from_api", service_id=fake_uuid, template_id=fake_uuid) not in content
        assert url_for("main.send_test", service_id=fake_uuid, template_id=fake_uuid) not in content
        assert "This template was deleted<br/>1 January 2016" in content

        mock_get_deleted_template.assert_called_with(service_id, template_id)


@pytest.mark.parametrize('route', [
    'main.add_service_template',
    'main.edit_service_template',
    'main.delete_service_template'
])
def test_route_permissions(route,
                           mocker,
                           app_,
                           api_user_active,
                           service_one,
                           mock_get_service_template,
                           mock_get_template_statistics_for_template,
                           fake_uuid):
    with app_.test_request_context():
        validate_route_permission(
            mocker,
            app_,
            "GET",
            200,
            url_for(
                route,
                service_id=service_one['id'],
                template_type='sms',
                template_id=fake_uuid),
            ['manage_templates'],
            api_user_active,
            service_one)


def test_route_permissions_for_choose_template(mocker,
                                               app_,
                                               api_user_active,
                                               service_one,
                                               mock_get_service_templates):
    mocker.patch('app.job_api_client.get_job')
    with app_.test_request_context():
        validate_route_permission(
            mocker,
            app_,
            "GET",
            200,
            url_for(
                'main.choose_template',
                service_id=service_one['id'],
                template_type='sms'),
            ['view_activity'],
            api_user_active,
            service_one)


@pytest.mark.parametrize('route', [
    'main.add_service_template',
    'main.edit_service_template',
    'main.delete_service_template'
])
def test_route_invalid_permissions(route,
                                   mocker,
                                   app_,
                                   api_user_active,
                                   service_one,
                                   mock_get_service_template,
                                   mock_get_template_statistics_for_template,
                                   fake_uuid):
    with app_.test_request_context():
        validate_route_permission(
            mocker,
            app_,
            "GET",
            403,
            url_for(
                route,
                service_id=service_one['id'],
                template_type='sms',
                template_id=fake_uuid),
            ['view_activity'],
            api_user_active,
            service_one)


def test_get_last_use_message_returns_no_template_message():
    assert get_last_use_message('My Template', []) == 'My Template has never been used'


@freeze_time('2000-01-01T15:00')
def test_get_last_use_message_uses_most_recent_statistics():
    template_statistics = [
        {
            'updated_at': '2000-01-01T12:00:00.000000+00:00'
        },
        {
            'updated_at': '2000-01-01T09:00:00.000000+00:00'
        },
    ]
    assert get_last_use_message('My Template', template_statistics) == 'My Template was last used 3 hours ago'


@pytest.mark.parametrize('from_time, until_time, message', [
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 1, 12, 0, 59), 'under a minute'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 1, 12, 1), '1 minute'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 1, 12, 2, 35), '2 minutes'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 1, 12, 59), '59 minutes'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 1, 13, 0), '1 hour'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 1, 14, 0), '2 hours'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 2, 11, 59), '23 hours'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 2, 12, 0), '1 day'),
    (datetime(2000, 1, 1, 12, 0), datetime(2000, 1, 3, 14, 0), '2 days'),
])
def test_get_human_readable_delta(from_time, until_time, message):
    assert get_human_readable_delta(from_time, until_time) == message
