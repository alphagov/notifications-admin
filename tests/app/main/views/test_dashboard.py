def test_should_show_recent_jobs_on_dashboard(notifications_admin):
    response = notifications_admin.test_client().get('/dashboard')

    assert response.status_code == 200
    assert 'Test message 1' in response.get_data(as_text=True)
    assert 'Asdfgg' in response.get_data(as_text=True)
