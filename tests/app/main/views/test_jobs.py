from tests.app.main import create_test_user


def test_should_return_list_of_all_jobs(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/jobs')

        assert response.status_code == 200
        assert 'Test message 1' in response.get_data(as_text=True)
        assert 'Final reminder' in response.get_data(as_text=True)


def test_should_show_page_for_one_job(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            # TODO filename will be part of job metadata not in session
            with client.session_transaction() as s:
                s[456] = 'dispatch_20151114.csv'
        user = create_test_user('active')
        client.login(user)
        response = client.get('/services/123/jobs/456')

        assert response.status_code == 200
        assert 'dispatch_20151114.csv' in response.get_data(as_text=True)
        assert 'Test message 1' in response.get_data(as_text=True)


def test_should_show_page_for_one_notification(notifications_admin, notifications_admin_db, notify_db_session):
    with notifications_admin.test_request_context():
        with notifications_admin.test_client() as client:
            user = create_test_user('active')
            client.login(user)
            response = client.get('/services/123/jobs/456/notification/3')

        assert response.status_code == 200
        assert 'Text message' in response.get_data(as_text=True)
        assert '+44 7700 900 522' in response.get_data(as_text=True)
