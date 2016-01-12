def test_should_show_overview_page(notifications_admin):
    response = notifications_admin.test_client().get('/user-profile')

    assert response.status_code == 200
