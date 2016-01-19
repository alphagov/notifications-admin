from flask import url_for


def test_should_return_list_of_all_templates(app_, db_, db_session, active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.get(url_for('.manage_templates', service_id=123))

    assert response.status_code == 200


def test_should_show_page_for_one_templates(app_, db_, db_session, active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.get(url_for('.edit_template', service_id=123, template_id=1))

    assert response.status_code == 200


def test_should_redirect_when_saving_a_template(app_, db_, db_session, active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.post(url_for('.edit_template', service_id=123, template_id=1))

            assert response.status_code == 302
            assert response.location == url_for('.manage_templates', service_id=123, _external=True)


def test_should_show_delete_template_page(app_, db_, db_session, active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.get(url_for('.delete_template', service_id=123, template_id=1))

    assert response.status_code == 200
    assert 'Are you sure' in response.get_data(as_text=True)


def test_should_redirect_when_deleting_a_template(app_, db_, db_session, active_user):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(active_user)
            response = client.post(url_for('.delete_template', service_id=123, template_id=1))

            assert response.status_code == 302
            assert response.location == url_for('.manage_templates', service_id=123, _external=True)
