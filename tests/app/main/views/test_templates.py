import json
import uuid
from bs4 import BeautifulSoup
from tests import validate_route_permission

from flask import url_for


def test_should_show_page_for_one_templates(app_,
                                            api_user_active,
                                            mock_login,
                                            mock_get_service,
                                            mock_get_service_template,
                                            mock_get_user,
                                            mock_get_user_by_email,
                                            mock_has_permissions,
                                            fake_uuid):
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
                '.choose_template', service_id=service_id, template_type='sms', _external=True)
            mock_update_service_template.assert_called_with(
                template_id, name, 'sms', content, service_id, None)


def test_should_show_interstitial_when_making_breaking_change(
    app_,
    api_user_active,
    mock_login,
    mock_get_service_template,
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
                    'template_content': "hello ((name))",
                    'template_type': 'sms',
                    'service': service_id
                }
            )

            assert response.status_code == 200
            page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
            assert page.h1.string.strip() == "Confirm changes"

            for key, value in {
                'name': 'new name',
                'subject': '',
                'template_content': 'hello ((name))',
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
            assert (
                "Content has a character count greater"
                " than the limit of 459"
            ) in resp.get_data(as_text=True)


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
            assert (
                "Content has a character count greater"
                " than the limit of 459"
            ) in resp.get_data(as_text=True)


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
            content = "template content"
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
                '.choose_template',
                service_id=service_id,
                template_type='email',
                _external=True)
            mock_update_service_template.assert_called_with(
                template_id, name, 'email', content, service_id, subject)


def test_should_show_delete_template_page(app_,
                                          api_user_active,
                                          mock_login,
                                          mock_get_service,
                                          mock_get_service_template,
                                          mock_get_user,
                                          mock_get_user_by_email,
                                          mock_has_permissions,
                                          fake_uuid):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = fake_uuid
            template_id = fake_uuid
            response = client.get(url_for(
                '.delete_service_template',
                service_id=service_id,
                template_id=template_id))

    content = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Are you sure' in content
    assert 'Two week reminder' in content
    assert 'Your vehicle tax is about to expire' in content
    mock_get_service_template.assert_called_with(
        service_id, template_id)


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


def test_route_permissions(mocker,
                           app_,
                           api_user_active,
                           service_one,
                           mock_get_service_template,
                           fake_uuid):
    routes = [
        'main.add_service_template',
        'main.edit_service_template',
        'main.delete_service_template']
    with app_.test_request_context():
        for route in routes:
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


def test_route_invalid_permissions(mocker,
                                   app_,
                                   api_user_active,
                                   service_one,
                                   mock_get_service_template,
                                   fake_uuid):
    routes = [
        'main.add_service_template',
        'main.edit_service_template',
        'main.delete_service_template']
    with app_.test_request_context():
        for route in routes:
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
