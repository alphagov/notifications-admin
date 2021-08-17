import uuid

import pytest
from flask import url_for

from tests.conftest import SERVICE_ONE_ID, normalize_spaces


def test_returned_letter_summary(
    client_request,
    mocker
):
    summary_data = [{'returned_letter_count': 1234, 'reported_at': '2019-12-24'}]
    mock = mocker.patch("app.service_api_client.get_returned_letter_summary",
                        return_value=summary_data)

    page = client_request.get("main.returned_letter_summary", service_id=SERVICE_ONE_ID)

    mock.assert_called_once_with(SERVICE_ONE_ID)

    assert page.h1.string.strip() == 'Returned letters'
    assert normalize_spaces(
        page.select_one('.table-field').text
    ) == (
        '24 December 2019 '
        '1,234 letters'
    )
    assert page.select_one('.table-field a')['href'] == url_for(
        '.returned_letters',
        service_id=SERVICE_ONE_ID,
        reported_at='2019-12-24',
    )


def test_returned_letter_summary_with_one_letter(
    client_request,
    mocker
):
    summary_data = [{'returned_letter_count': 1, 'reported_at': '2019-12-24'}]
    mock = mocker.patch("app.service_api_client.get_returned_letter_summary",
                        return_value=summary_data)

    page = client_request.get("main.returned_letter_summary", service_id=SERVICE_ONE_ID)

    mock.assert_called_once_with(SERVICE_ONE_ID)

    assert page.h1.string.strip() == 'Returned letters'
    assert normalize_spaces(
        page.select_one('.table-field').text
    ) == (
        '24 December 2019 '
        '1 letter'
    )


def test_returned_letters_page(
    client_request,
    mocker
):
    data = [
        {
            'notification_id': uuid.uuid4(),
            'client_reference': client_reference,
            'created_at': '2019-12-24 13:30',
            'email_address': 'test@gov.uk',
            'template_name': template_name,
            'template_id': uuid.uuid4(),
            'template_version': None,
            'original_file_name': original_file_name,
            'job_row_number': None,
            'uploaded_letter_file_name': uploaded_letter_file_name,
        }
        for client_reference, template_name, original_file_name, uploaded_letter_file_name in (
            ('ABC123', 'Example template', None, None),
            (None, 'Example template', 'Example spreadsheet.xlsx', None),
            (None, 'Example template', None, None),
            ('DEF456', None, None, 'Example precompiled.pdf'),
            (None, None, None, 'Example one-off.pdf'),
            ('XYZ999', None, None, None),
        )
    ]
    mocker.patch('app.service_api_client.get_returned_letters', return_value=data)

    page = client_request.get(
        'main.returned_letters',
        service_id=SERVICE_ONE_ID,
        reported_at='2019-12-24',
    )

    assert [
        'Template name Originally sent',
        'Example template Reference ABC123 Sent 24 December 2019',
        'Example template Sent from Example spreadsheet.xlsx Sent 24 December 2019',
        'Example template No reference provided Sent 24 December 2019',
        'Example precompiled.pdf Reference DEF456 Sent 24 December 2019',
        'Example one-off.pdf No reference provided Sent 24 December 2019',
        'Provided as PDF Reference XYZ999 Sent 24 December 2019',
    ] == [
        normalize_spaces(row.text) for row in page.select('tr')
    ]


@pytest.mark.parametrize('number_of_letters, expected_message', (
    pytest.param(
        51,
        'Only showing the first 50 of 51 rows'
    ),
    pytest.param(
        1234,
        'Only showing the first 50 of 1,234 rows'
    ),
))
def test_returned_letters_page_with_many_letters(
    client_request,
    mocker,
    number_of_letters,
    expected_message,
):
    data = [
        {
            'notification_id': uuid.uuid4(),
            'client_reference': None,
            'created_at': '2019-12-24 13:30',
            'email_address': 'test@gov.uk',
            'template_name': 'Example template',
            'template_id': uuid.uuid4(),
            'template_version': None,
            'original_file_name': None,
            'job_row_number': None,
            'uploaded_letter_file_name': None,
        }
    ] * number_of_letters
    mocker.patch('app.service_api_client.get_returned_letters', return_value=data)

    page = client_request.get(
        'main.returned_letters',
        service_id=SERVICE_ONE_ID,
        reported_at='2019-12-24',
    )

    assert len(data) == number_of_letters
    assert len(page.select('tbody tr')) == 50
    assert normalize_spaces(
        page.select_one('.table-show-more-link').text
    ) == (
        expected_message
    )
    assert page.select_one('a[download]').text == (
        'Download this report'
    )
    assert page.select_one('a[download]')['href'] == url_for(
        '.returned_letters_report',
        service_id=SERVICE_ONE_ID,
        reported_at='2019-12-24',
    )


def test_returned_letters_reports(
    client_request,
    mocker
):
    data = [{
        'notification_id': '12345678',
        'client_reference': '2344567',
        'created_at': '2019-12-24 13:30',
        'email_address': 'test@gov.uk',
        'template_name': 'First letter template',
        'template_id': '3445667',
        'template_version': 2,
        'original_file_name': None,
        'job_row_number': None,
        'uploaded_letter_file_name': 'test_letter.pdf',
    }]
    mock = mocker.patch("app.service_api_client.get_returned_letters", return_value=data)

    response = client_request.get_response("main.returned_letters_report",
                                           service_id=SERVICE_ONE_ID,
                                           reported_at='2019-12-24')

    report = response.get_data(as_text=True)
    mock.assert_called_once_with(SERVICE_ONE_ID, '2019-12-24')
    assert report.strip() == (
        'Notification ID,Reference,Date sent,Sent by,Template name,Template ID,Template version,'
        + 'Spreadsheet file name,Spreadsheet row number,Uploaded letter file name\r\n'
        + '12345678,2344567,2019-12-24 13:30,test@gov.uk,'
        + 'First letter template,3445667,2,,,test_letter.pdf'
    )


def test_returned_letters_reports_returns_404_for_bad_date(
        client_request,
        mocker
):
    mock = mocker.patch("app.service_api_client.get_returned_letters")
    client_request.get_response("main.returned_letters_report",
                                service_id=SERVICE_ONE_ID,
                                reported_at='19-12-2019',
                                _expected_status=404)
    assert mock.called is False
