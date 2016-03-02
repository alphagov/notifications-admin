from flask import url_for
from bs4 import BeautifulSoup


def test_should_return_list_of_all_jobs(app_,
                                        service_one,
                                        api_user_active,
                                        mock_get_user,
                                        mock_get_user_by_email,
                                        mock_login,
                                        mock_get_jobs):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.view_jobs', service_id=101))

        assert response.status_code == 200
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
        assert page.h1.string == 'Notifications activity'
        jobs = page.tbody.find_all('tr')
        assert len(jobs) == 5


def test_should_show_page_for_one_job(app_,
                                      service_one,
                                      api_user_active,
                                      mock_login,
                                      mock_get_user,
                                      mock_get_user_by_email,
                                      mock_get_service,
                                      mock_get_service_template,
                                      job_data,
                                      mock_get_job):
    service_id = job_data['service']
    job_id = job_data['id']
    file_name = job_data['original_file_name']

    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(api_user_active)
            response = client.get(url_for('main.view_job', service_id=service_id, job_id=job_id))

        assert response.status_code == 200
        content = response.get_data(as_text=True)
        assert "Test Service: Your vehicle tax is about to expire" in content
        assert file_name in content
