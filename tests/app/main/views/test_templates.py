def test_should_return_list_of_all_templates(notifications_admin):
    response = notifications_admin.test_client().get('/templates')

    assert response.status_code == 200


def test_should_show_page_for_one_templates(notifications_admin):
    response = notifications_admin.test_client().get('/templates/template')

    assert response.status_code == 200


def test_should_redirect_when_saving_a_template(notifications_admin):
    response = notifications_admin.test_client().post('/templates/template')

    assert response.status_code == 302
    assert response.location == 'http://localhost/templates'
