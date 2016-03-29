import json
import uuid
from tests import validate_route_permission

from flask import url_for


def test_should_show_page_for_one_templates(app_,
                                            api_user_active,
                                            mock_get_service_template,
                                            mock_get_user,
                                            mock_get_user_by_email,
                                            mock_login,
                                            mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = str(uuid.uuid4())
            template_id = 456
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
                                                mock_get_service_template,
                                                mock_update_service_template,
                                                mock_get_user,
                                                mock_get_user_by_email,
                                                mock_login,
                                                mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = str(uuid.uuid4())
            template_id = 456
            name = "new name"
            content = "template content"
            data = {
                'id': template_id,
                'name': name,
                'template_content': content,
                'type': 'sms',
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
                template_id, name, 'sms', content, service_id)


def test_should_show_delete_template_page(app_,
                                          api_user_active,
                                          mock_get_service_template,
                                          mock_get_user,
                                          mock_get_user_by_email,
                                          mock_login,
                                          mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = str(uuid.uuid4())
            template_id = 456
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
                                                  mock_get_service_template,
                                                  mock_delete_service_template,
                                                  mock_get_user,
                                                  mock_get_user_by_email,
                                                  mock_login,
                                                  mock_has_permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            service_id = str(uuid.uuid4())
            template_id = 456
            name = "new name"
            type_ = "sms"
            content = "template content"
            data = {
                'id': template_id,
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
                           mock_get_service_template):
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
                    template_id=123),
                ['manage_templates'],
                api_user_active,
                service_one)


def test_route_permissions_for_choose_tempalte(mocker,
                                               app_,
                                               api_user_active,
                                               service_one,
                                               mock_get_service_template):
    with app_.test_request_context():
        validate_route_permission(
            mocker,
            app_,
            "GET",
            200,
            url_for(
                'main.choose_template',
                service_id=service_one['id'],
                template_type='sms',
                template_id=123),
            ['view_activity'],
            api_user_active,
            service_one)


def test_route_invalid_permissions(mocker,
                                   app_,
                                   api_user_active,
                                   service_one,
                                   mock_get_service_template):
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
                    template_id=123),
                ['view_activity'],
                api_user_active,
                service_one)
