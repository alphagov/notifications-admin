def test_should_return_list_of_all_jobs(notifications_admin):
    response = notifications_admin.test_client().get('/jobs')

    assert response.status_code == 200
    assert 'Test message 1' in response.get_data(as_text=True)
    assert 'Final reminder' in response.get_data(as_text=True)


def test_should_show_page_for_one_job(notifications_admin):
    response = notifications_admin.test_client().get('/jobs/job')

    assert response.status_code == 200
    assert 'dispatch_20151114.csv' in response.get_data(as_text=True)
    assert 'Test message 1' in response.get_data(as_text=True)


def test_should_show_page_for_one_notification(notifications_admin):
    response = notifications_admin.test_client().get('/jobs/job/notification/3')

    assert response.status_code == 200
    assert 'Text message' in response.get_data(as_text=True)
    assert '+44 7700 900 522' in response.get_data(as_text=True)
