from tests.conftest import SERVICE_ONE_ID, normalize_spaces


def test_returned_letter_summary(
    client_request,
    mocker
):
    summary_data = [{'returned_letter_count': 30, 'reported_at': '2019-12-24'}]
    mock = mocker.patch("app.service_api_client.get_returned_letter_summary",
                        return_value=summary_data)

    page = client_request.get("main.returned_letter_summary", service_id=SERVICE_ONE_ID)

    mock.assert_called_once_with(SERVICE_ONE_ID)

    expected_text = "Returned letters reported on Tuesday 24 December 2019 - 30 letters"
    assert page.h1.string.strip() == 'Returned letters'
    assert normalize_spaces(page.select('.table-field-left-aligned')[0].text) == expected_text


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
        + 'Spreadsheet file name,Spreadsheet row number,Uploaded letter\r\n'
        + '12345678,2344567,2019-12-24 13:30,test@gov.uk,'
        + 'First letter template,3445667,2,,,test_letter.pdf'
    )
