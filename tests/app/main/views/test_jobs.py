def test_should_return_list_of_all_jobs(notifications_admin):
    response = notifications_admin.test_client().get('/jobs')

    assert response.status_code == 200
    assert 'This page will be where we show the list of jobs that this service has processed' in response.get_data(as_text=True)  # noqa


def test_should_show_page_for_one_job(notifications_admin):
    response = notifications_admin.test_client().get('/jobs/job')

    assert response.status_code == 200
    assert 'contact-demo.csv sent with Reminder template' in response.get_data(as_text=True)


def test_should_show_page_for_one_notification(notifications_admin):
    response = notifications_admin.test_client().get('/jobs/job/notification/3')

    assert response.status_code == 200
    assert 'Text message' in response.get_data(as_text=True)
    assert '+44 7700 900 522' in response.get_data(as_text=True)
