import json
from flask import url_for


def test_should_return_list_of_all_templates(app_,
                                             db_,
                                             db_session,
                                             mock_active_user,
                                             mock_get_service_templates,
                                             mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_active_user)
            service_id = 123
            response = client.get(url_for(
                '.manage_service_templates', service_id=service_id))

    assert response.status_code == 200
    mock_get_service_templates.assert_called_with(service_id)


def test_should_show_page_for_one_templates(app_,
                                            db_,
                                            db_session,
                                            mock_api_user,
                                            mock_get_service_template,
                                            mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_api_user)
            service_id = 123
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
                                                db_,
                                                db_session,
                                                mock_api_user,
                                                mock_get_service_template,
                                                mock_update_service_template,
                                                mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_api_user)
            service_id = 123
            template_id = 456
            name = "new name"
            type_ = "sms"
            content = "template content"
            data = {
                'id': template_id,
                'name': name,
                'template_type': type_,
                "template_content": content,
                "service": service_id
            }
            response = client.post(url_for(
                '.edit_service_template',
                service_id=service_id,
                template_id=template_id), data=data)

            assert response.status_code == 302
            assert response.location == url_for(
                '.manage_service_templates', service_id=service_id, _external=True)
            mock_update_service_template.assert_called_with(
                template_id, name, type_, content, service_id)


def test_should_show_delete_template_page(app_,
                                          db_,
                                          db_session,
                                          mock_api_user,
                                          mock_get_service_template,
                                          mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_api_user)
            service_id = 123
            template_id = 456
            response = client.get(url_for(
                '.delete_service_template',
                service_id=service_id,
                template_id=template_id))

    assert response.status_code == 200
    assert 'Are you sure' in response.get_data(as_text=True)
    mock_get_service_template.assert_called_with(
        service_id, template_id)


def test_should_redirect_when_deleting_a_template(app_,
                                                  db_,
                                                  db_session,
                                                  mock_api_user,
                                                  mock_get_service_template,
                                                  mock_delete_service_template,
                                                  mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_api_user)
            service_id = 123
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
                template_id=template_id), data=data)

            assert response.status_code == 302
            assert response.location == url_for(
                '.manage_service_templates',
                service_id=service_id, _external=True)
            mock_get_service_template.assert_called_with(
                service_id, template_id)
            mock_delete_service_template.assert_called_with(
                service_id, template_id)
