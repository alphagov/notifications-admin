def test_styleguide_can_render(notifications_admin):
    response = notifications_admin.test_client().get('/_styleguide')

    assert response.status_code == 200
