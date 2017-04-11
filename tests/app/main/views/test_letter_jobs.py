from flask import url_for
from bs4 import BeautifulSoup

from app import format_datetime_short

valid_letter_jobs = [
    {
        'service_name': {'name': 'test_name'},
        'template_version': 1,
        'id': 'test_id',
        'job_status': 'test_status',
        'created_at': '2017-04-01T12:00:00'
    },
    {
        'service_name': {'name': 'test_name 2'},
        'template_version': 2,
        'id': 'test_id 2',
        'job_status': 'test_status 2',
        'created_at': '2017-04-02T13:00:00'
    },
    {
        'service_name': {'name': 'test_name 3'},
        'template_version': 3,
        'id': 'test_id 3',
        'job_status': 'test_status 3',
        'created_at': '2017-04-03T14:00:00'
    }
]

send_letter_jobs_response = {"response": "Task created to send files to DVLA"}


def test_get_letter_jobs_returns_list_of_all_letter_jobs(logged_in_platform_admin_client, mocker):
    mock_get_letters = mocker.patch('app.letter_jobs_client.get_letter_jobs', return_value=valid_letter_jobs)

    response = logged_in_platform_admin_client.get(url_for('main.letter_jobs'))

    assert mock_get_letters.called
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string == 'Letter jobs'

    table = page.find('table')
    table_body = table.find('tbody')
    rows = table_body.find_all('tr')

    assert len(rows) == len(valid_letter_jobs)

    for row_pos in range(len(rows)):
        cols = rows[row_pos].find_all('td')
        assert valid_letter_jobs[row_pos]['service_name']['name'] == cols[0].text
        assert valid_letter_jobs[row_pos]['id'] == cols[1].text
        assert valid_letter_jobs[row_pos]['job_status'] == cols[2].text
        assert format_datetime_short(valid_letter_jobs[row_pos]['created_at']) == cols[3].text


def test_post_letter_jobs_select_1_letter_job_submits_1_job(logged_in_platform_admin_client, mocker):
    letter_jobs_first_selected = {'job_id': ['test_id']}

    mock_get_letters = mocker.patch('app.letter_jobs_client.get_letter_jobs', return_value=valid_letter_jobs)
    mock_send_letters = mocker.patch('app.letter_jobs_client.send_letter_jobs', return_value=send_letter_jobs_response)

    response = logged_in_platform_admin_client.post(url_for('main.letter_jobs'), data=letter_jobs_first_selected)

    assert mock_get_letters.called
    assert mock_send_letters.called
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    table = page.find('table')
    table_body = table.find('tbody')
    rows = table_body.find_all('tr')

    assert len(rows) == len(valid_letter_jobs)

    colr0 = rows[0].find_all('td')
    colr1 = rows[1].find_all('td')
    colr2 = rows[2].find_all('td')

    assert colr0[5].text == "sending"
    assert colr1[5].text == ""
    assert colr2[5].text == ""

    message = page.find('p', attrs={'id': 'message'}).text
    assert "Task created to send files to DVLA" in message


def test_post_letter_jobs_none_selected_shows_message(logged_in_platform_admin_client, mocker):
    mock_get_letters = mocker.patch('app.letter_jobs_client.get_letter_jobs', return_value=valid_letter_jobs)
    mock_send_letters = mocker.patch('app.letter_jobs_client.send_letter_jobs', return_value=send_letter_jobs_response)

    response = logged_in_platform_admin_client.post(url_for('main.letter_jobs'), data={})

    assert mock_get_letters.called
    assert not mock_send_letters.called
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    message = page.find('p', attrs={'id': 'message'}).text

    assert "No jobs selected" in message
