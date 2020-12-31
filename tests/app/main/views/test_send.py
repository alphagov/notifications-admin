# -*- coding: utf-8 -*-
import uuid
from functools import partial
from glob import glob
from io import BytesIO
from itertools import repeat
from os import path
from unittest.mock import ANY
from uuid import uuid4
from zipfile import BadZipFile

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError
from notifications_utils.recipients import RecipientCSV
from notifications_utils.template import (
    LetterImageTemplate,
    LetterPreviewTemplate,
    SMSPreviewTemplate,
)
from xlrd.biffh import XLRDError
from xlrd.xldate import (
    XLDateAmbiguous,
    XLDateError,
    XLDateNegative,
    XLDateTooLarge,
)

from tests import (
    template_json,
    validate_route_permission,
    validate_route_permission_with_client,
)
from tests.conftest import (
    SERVICE_ONE_ID,
    create_active_caseworking_user,
    create_active_user_with_permissions,
    create_multiple_email_reply_to_addresses,
    create_multiple_sms_senders,
    create_platform_admin_user,
    create_template,
    mock_get_service_email_template,
    mock_get_service_letter_template,
    mock_get_service_template,
    normalize_spaces,
)

template_types = ['email', 'sms']

unchanging_fake_uuid = uuid.uuid4()

# The * ignores hidden files, eg .DS_Store
test_spreadsheet_files = glob(path.join('tests', 'spreadsheet_files', '*'))
test_non_spreadsheet_files = glob(path.join('tests', 'non_spreadsheet_files', '*'))


def test_show_correct_title_and_description_for_email_sender_type(
    client_request,
    fake_uuid,
    mock_get_service_email_template,
    multiple_reply_to_email_addresses,
):
    page = client_request.get(
        '.set_sender',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid
    )

    assert page.select_one('h1').text == 'Where should replies come back to?'

    for element in ('legend', 'legend .govuk-visually-hidden'):
        assert normalize_spaces(page.select_one(element).text) == 'Where should replies come back to?'


def test_show_correct_title_and_description_for_sms_sender_type(
    client_request,
    fake_uuid,
    mock_get_service_template,
    multiple_sms_senders,
):
    page = client_request.get(
        '.set_sender',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid
    )

    assert page.select_one('h1').text == 'Who should the message come from?'

    for element in ('legend', 'legend .govuk-visually-hidden'):
        assert normalize_spaces(page.select_one(element).text) == 'Who should the message come from?'


def test_default_email_sender_is_checked_and_has_hint(
    client_request,
    fake_uuid,
    mock_get_service_email_template,
    multiple_reply_to_email_addresses,
):
    page = client_request.get(
        '.set_sender',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid
    )

    assert page.select('.multiple-choice input')[0].has_attr('checked')
    assert normalize_spaces(page.select_one('.multiple-choice label .block-label-hint').text) == "(Default)"
    assert not page.select('.multiple-choice input')[1].has_attr('checked')


def test_default_sms_sender_is_checked_and_has_hint(
    client_request,
    fake_uuid,
    mock_get_service_template,
    multiple_sms_senders_with_diff_default,
):
    page = client_request.get(
        '.set_sender',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid
    )

    assert page.select('.multiple-choice input')[0].has_attr('checked')
    assert normalize_spaces(page.select_one('.multiple-choice label .block-label-hint').text) == "(Default)"
    assert not page.select('.multiple-choice input')[1].has_attr('checked')


def test_default_sms_sender_is_checked_and_has_hint_when_there_are_no_inbound_numbers(
    client_request,
    fake_uuid,
    mock_get_service_template,
    multiple_sms_senders_no_inbound,
):
    page = client_request.get(
        '.set_sender',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid
    )

    assert page.select('.multiple-choice input')[0].has_attr('checked')
    assert normalize_spaces(page.select_one('.multiple-choice label .block-label-hint').text) == "(Default)"
    assert not page.select('.multiple-choice input')[1].has_attr('checked')


def test_default_inbound_sender_is_checked_and_has_hint_with_default_and_receives_text(
    client_request,
    service_one,
    fake_uuid,
    mock_get_service_template,
    multiple_sms_senders
):
    page = client_request.get(
        '.set_sender',
        service_id=service_one['id'],
        template_id=fake_uuid
    )

    assert page.select('.multiple-choice input')[0].has_attr('checked')
    assert normalize_spaces(
        page.select_one('.multiple-choice label .block-label-hint').text) == "(Default and receives replies)"
    assert not page.select('.multiple-choice input')[1].has_attr('checked')
    assert not page.select('.multiple-choice input')[2].has_attr('checked')


def test_sms_sender_has_receives_replies_hint(
    client_request,
    service_one,
    fake_uuid,
    mock_get_service_template,
    multiple_sms_senders
):
    page = client_request.get(
        '.set_sender',
        service_id=service_one['id'],
        template_id=fake_uuid
    )

    assert page.select('.multiple-choice input')[0].has_attr('checked')
    assert normalize_spaces(
        page.select_one('.multiple-choice label .block-label-hint').text) == "(Default and receives replies)"
    assert not page.select('.multiple-choice input')[1].has_attr('checked')
    assert not page.select('.multiple-choice input')[2].has_attr('checked')


@pytest.mark.parametrize('template_type, sender_data', [
    (
        'email',
        create_multiple_email_reply_to_addresses(),
    ),
    (
        'sms',
        create_multiple_sms_senders()
    )
])
def test_sender_session_is_present_after_selected(
    client_request,
    service_one,
    fake_uuid,
    template_type,
    sender_data,
    mocker
):
    template_data = create_template(template_type=template_type)
    mocker.patch('app.service_api_client.get_service_template', return_value={'data': template_data})

    if template_type == 'email':
        mocker.patch('app.service_api_client.get_reply_to_email_addresses', return_value=sender_data)
    else:
        mocker.patch('app.service_api_client.get_sms_senders', return_value=sender_data)

    client_request.post(
        '.set_sender',
        service_id=service_one['id'],
        template_id=fake_uuid,
        _data={'sender': '1234'},
    )

    with client_request.session_transaction() as session:
        assert session['sender_id'] == '1234'


def test_set_sender_redirects_if_no_reply_to_email_addresses(
    client_request,
    fake_uuid,
    mock_get_service_email_template,
    no_reply_to_email_addresses,
):
    client_request.get(
        '.set_sender',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=302,
        _expected_url=url_for(
            '.send_one_off',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True,
        )
    )


def test_set_sender_redirects_if_no_sms_senders(
    client_request,
    fake_uuid,
    mock_get_service_template,
    no_sms_senders,
):
    client_request.get(
        '.set_sender',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=302,
        _expected_url=url_for(
            '.send_one_off',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True,
        )
    )


def test_that_test_files_exist():
    assert len(test_spreadsheet_files) == 8
    assert len(test_non_spreadsheet_files) == 6


def test_should_not_allow_files_to_be_uploaded_without_the_correct_permission(
    client_request,
    mock_get_service_template,
    service_one,
    fake_uuid,
):
    template_id = fake_uuid
    service_one['permissions'] = []

    page = client_request.get(
        '.send_messages',
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
        _follow_redirects=True,
        _expected_status=403,
    )

    assert page.select('main p')[0].text.strip() == "Sending text messages has been disabled for your service."
    assert page.select(".govuk-back-link")[0].text == "Back"
    assert page.select(".govuk-back-link")[0]['href'] == url_for(
        '.view_template',
        service_id=service_one['id'],
        template_id=template_id,
    )


def test_example_spreadsheet(
    client_request,
    mock_get_service_template_with_placeholders_same_as_recipient,
    fake_uuid,
):

    page = client_request.get(
        '.send_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid
    )

    assert normalize_spaces(
        page.select_one('tbody tr').text
    ) == (
        '1 phone number name date'
    )
    assert page.select_one('input[type=file]').has_attr('accept')
    assert page.select_one('input[type=file]')['accept'] == '.csv,.xlsx,.xls,.ods,.xlsm,.tsv'


def test_example_spreadsheet_for_letters(
    client_request,
    service_one,
    mocker,
    mock_get_service_letter_template_with_placeholders,
    fake_uuid,
):
    service_one['permissions'] += ['letter']
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=1)

    page = client_request.get(
        '.send_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid
    )

    assert list(zip(*[
        [normalize_spaces(cell.text) for cell in page.select('tbody tr')[row].select('td')]
        for row in (0, 1)
    ])) == [
        ('1', '2'),
        ('address line 1', 'A. Name'),
        ('address line 2', '123 Example Street'),
        ('address line 3', 'XM4 5HQ'),
        ('address line 4', ''),
        ('address line 5', ''),
        ('address line 6', ''),
        ('address line 7', ''),
        ('name', 'example'),
        ('date', 'example'),
    ]


@pytest.mark.parametrize(
    "filename, acceptable_file",
    list(zip(test_spreadsheet_files, repeat(True))) +
    list(zip(test_non_spreadsheet_files, repeat(False)))
)
def test_upload_files_in_different_formats(
    filename,
    acceptable_file,
    logged_in_client,
    service_one,
    mocker,
    mock_get_service_template,
    mock_s3_set_metadata,
    mock_s3_upload,
    fake_uuid,
):
    with open(filename, 'rb') as uploaded:
        response = logged_in_client.post(
            url_for('main.send_messages', service_id=service_one['id'], template_id=fake_uuid),
            data={'file': (BytesIO(uploaded.read()), filename)},
            content_type='multipart/form-data'
        )
        page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    if acceptable_file:
        assert mock_s3_upload.call_args[0][1]['data'].strip() == (
            "phone number,name,favourite colour,fruit\r\n"
            "07739 468 050,Pete,Coral,tomato\r\n"
            "07527 125 974,Not Pete,Magenta,Avacado\r\n"
            "07512 058 823,Still Not Pete,Crimson,Pear"
        )
        mock_s3_set_metadata.assert_called_once_with(
            SERVICE_ONE_ID,
            fake_uuid,
            original_file_name=filename
        )
    else:
        assert not mock_s3_upload.called
        assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
            'Could not read {}. Try using a different file format.'.format(filename)
        )


def test_send_messages_sanitises_and_truncates_file_name_for_metadata(
    logged_in_client,
    service_one,
    mocker,
    mock_get_service_template_with_placeholders,
    mock_s3_set_metadata,
    mock_s3_get_metadata,
    mock_s3_upload,
    mock_s3_download,
    mock_get_job_doesnt_exist,
    fake_uuid,
):
    filename = f"😁{'a' * 2000}.csv"

    logged_in_client.post(
        url_for('main.send_messages', service_id=service_one['id'], template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), filename)},
        content_type='multipart/form-data',
        follow_redirects=False
    )

    assert len(
        mock_s3_set_metadata.call_args_list[0][1]['original_file_name']
    ) < len(filename)

    assert mock_s3_set_metadata.call_args_list[0][1]['original_file_name'].startswith('?')


@pytest.mark.parametrize('exception, expected_error_message', [
    (partial(UnicodeDecodeError, 'codec', b'', 1, 2, 'reason'), (
        'Could not read example.xlsx. Try using a different file format.'
    )),
    (BadZipFile, (
        'Could not read example.xlsx. Try using a different file format.'
    )),
    (XLRDError, (
        'Could not read example.xlsx. Try using a different file format.'
    )),
    (XLDateError, (
        'example.xlsx contains numbers or dates that Notify cannot understand. '
        'Try formatting all columns as ‘text’ or export your file as CSV.'
    )),
    (XLDateNegative, (
        'example.xlsx contains numbers or dates that Notify cannot understand. '
        'Try formatting all columns as ‘text’ or export your file as CSV.'
    )),
    (XLDateAmbiguous, (
        'example.xlsx contains numbers or dates that Notify cannot understand. '
        'Try formatting all columns as ‘text’ or export your file as CSV.'
    )),
    (XLDateTooLarge, (
        'example.xlsx contains numbers or dates that Notify cannot understand. '
        'Try formatting all columns as ‘text’ or export your file as CSV.'
    )),
])
def test_shows_error_if_parsing_exception(
    logged_in_client,
    mocker,
    mock_get_service_template,
    exception,
    expected_error_message,
    fake_uuid,
):

    def _raise_exception_or_partial_exception(file_content, filename):
        raise exception()

    mocker.patch(
        'app.main.views.send.Spreadsheet.from_file',
        side_effect=_raise_exception_or_partial_exception
    )

    response = logged_in_client.post(
        url_for('main.send_messages', service_id=SERVICE_ONE_ID, template_id=fake_uuid),
        data={'file': (BytesIO(b'example'), 'example.xlsx')},
        content_type='multipart/form-data'
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        expected_error_message
    )


def test_upload_csv_file_with_errors_shows_check_page_with_errors(
    logged_in_client,
    service_one,
    mocker,
    mock_get_service_template_with_placeholders,
    mock_s3_set_metadata,
    mock_s3_get_metadata,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
):

    mocker.patch(
        'app.main.views.send.s3download',
        return_value="""
            phone number,name
            +447700900986
            +447700900986
        """
    )

    response = logged_in_client.post(
        url_for('main.send_messages', service_id=service_one['id'], template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'example.csv')},
        content_type='multipart/form-data',
        follow_redirects=True
    )

    with logged_in_client.session_transaction() as session:
        assert 'file_uploads' not in session

    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.select_one('input[type=file]').has_attr('accept')
    assert page.select_one('input[type=file]')['accept'] == '.csv,.xlsx,.xls,.ods,.xlsm,.tsv'

    content = response.get_data(as_text=True)
    assert 'There’s a problem with example.csv' in content
    assert '+447700900986' in content
    assert 'Missing' in content
    assert 'Upload your file again' in content


def test_upload_csv_file_with_empty_message_shows_check_page_with_errors(
    logged_in_client,
    service_one,
    mocker,
    mock_get_empty_service_template_with_optional_placeholder,
    mock_s3_set_metadata,
    mock_s3_get_metadata,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
):

    mocker.patch(
        'app.main.views.send.s3download',
        return_value="""
            phone number, show_placeholder
            +447700900986, yes
            +447700900986, no
        """
    )

    response = logged_in_client.post(
        url_for('main.send_messages', service_id=service_one['id'], template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'example.csv')},
        content_type='multipart/form-data',
        follow_redirects=True
    )

    with logged_in_client.session_transaction() as session:
        assert 'file_uploads' not in session

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert normalize_spaces(
        page.select_one('.banner-dangerous').text
    ) == (
        'There’s a problem with example.csv '
        'You need to check you have content for the empty message in 1 row.'
    )
    assert [
        normalize_spaces(row.text) for row in page.select('tbody tr')
    ] == [
        '3 No content for this message',
        '+447700900986 no',
    ]
    assert normalize_spaces(page.select_one('.table-field-index').text) == '3'
    assert page.select_one('.table-field-index')['rowspan'] == '2'
    assert normalize_spaces(page.select('tbody tr td')[0].text) == '3'
    assert normalize_spaces(page.select('tbody tr td')[1].text) == (
        'No content for this message'
    )
    assert page.select('tbody tr td')[1]['colspan'] == '2'


def test_upload_csv_file_with_very_long_placeholder_shows_check_page_with_errors(
    logged_in_client,
    service_one,
    mocker,
    mock_get_service_template_with_placeholders,
    mock_s3_set_metadata,
    mock_s3_get_metadata,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
):
    big_placeholder = ' '.join(['not ok'] * 402)
    mocker.patch(
        'app.main.views.send.s3download',
        return_value=f"""
            phone number, name
            +447700900986, {big_placeholder}
            +447700900987, {big_placeholder}
        """
    )

    response = logged_in_client.post(
        url_for('main.send_messages', service_id=service_one['id'], template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'example.csv')},
        content_type='multipart/form-data',
        follow_redirects=True
    )

    with logged_in_client.session_transaction() as session:
        assert 'file_uploads' not in session

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert normalize_spaces(
        page.select_one('.banner-dangerous').text
    ) == (
        'There’s a problem with example.csv '
        'You need to shorten the messages in 2 rows.'
    )
    assert [
        normalize_spaces(row.text) for row in page.select('tbody tr')
    ] == [
        '2 Message is too long',
        f'+447700900986 {big_placeholder}',
        '3 Message is too long',
        f'+447700900987 {big_placeholder}',
    ]
    assert normalize_spaces(page.select_one('.table-field-index').text) == '2'
    assert page.select_one('.table-field-index')['rowspan'] == '2'
    assert normalize_spaces(page.select('tbody tr td')[0].text) == '2'
    assert normalize_spaces(page.select('tbody tr td')[1].text) == (
        'Message is too long'
    )
    assert page.select('tbody tr td')[1]['colspan'] == '2'


def test_upload_csv_file_with_bad_postal_address_shows_check_page_with_errors(
    logged_in_client,
    service_one,
    mocker,
    mock_get_service_letter_template,
    mock_s3_set_metadata,
    mock_s3_get_metadata,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
):
    service_one['permissions'] += ['letter']
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=9)
    mocker.patch(
        'app.main.views.send.s3download',
        return_value='''
            address line 1,     address line 3,  address line 6,
            Firstname Lastname, 123 Example St., SW1A 1AA
            Firstname Lastname, 123 Example St., SW!A !AA
            Firstname Lastname, 123 Example St., France
                              , 123 Example St., SW!A !AA
            "1\n2\n3\n4\n5\n6\n7\n8"
            =Firstname Lastname, 123 Example St., SW1A 1AA
        '''
    )

    response = logged_in_client.post(
        url_for('main.send_messages', service_id=service_one['id'], template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'example.csv')},
        content_type='multipart/form-data',
        follow_redirects=True
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert normalize_spaces(
        page.select_one('.banner-dangerous').text
    ) == (
        'There’s a problem with example.csv '
        'You need to fix 5 addresses.'
    )
    assert [
        normalize_spaces(row.text) for row in page.select('tbody tr')
    ] == [
        '3 Last line of the address must be a real UK postcode',
        'Firstname Lastname 123 Example St. SW!A !AA',

        '4 You do not have permission to send letters to other countries',
        'Firstname Lastname 123 Example St. France',

        '5 Address must be at least 3 lines long',
        '123 Example St. SW!A !AA',

        '6 Address must be no more than 7 lines long',
        '1 2 3 4 5 6 7 8',

        '7 Address lines must not start with any of the following characters: @ ( ) = [ ] ” \\ / ,',
        '=Firstname Lastname 123 Example St. SW1A 1AA',
    ]


def test_upload_csv_file_with_international_letters_permission_shows_appropriate_errors(
    logged_in_client,
    service_one,
    mocker,
    mock_get_service_letter_template,
    mock_s3_set_metadata,
    mock_s3_get_metadata,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
):
    service_one['permissions'] += ['letter', 'international_letters']
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=9)
    mocker.patch(
        'app.main.views.send.s3download',
        return_value='''
            address line 1,     address line 3,  address line 6,
            Firstname Lastname, 123 Example St., SW1A 1AA
            Firstname Lastname, 123 Example St., France
            Firstname Lastname, 123 Example St., SW!A !AA
            Firstname Lastname, 123 Example St., Not France
        '''
    )

    response = logged_in_client.post(
        url_for('main.send_messages', service_id=service_one['id'], template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'example.csv')},
        content_type='multipart/form-data',
        follow_redirects=True
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert normalize_spaces(
        page.select_one('.banner-dangerous').text
    ) == (
        'There’s a problem with example.csv '
        'You need to fix 2 addresses.'
    )
    assert [
        normalize_spaces(row.text) for row in page.select('tbody tr')
    ] == [
        '4 Last line of the address must be a UK postcode or another country',
        'Firstname Lastname 123 Example St. SW!A !AA',

        '5 Last line of the address must be a UK postcode or another country',
        'Firstname Lastname 123 Example St. Not France',
    ]


@pytest.mark.parametrize('row_index, expected_postage', (
    (2, 'Postage: second class'),
    (3, 'Postage: international'),
))
def test_upload_csv_file_with_international_letters_permission_shows_correct_postage(
    client_request,
    service_one,
    mocker,
    mock_get_service_letter_template,
    mock_s3_get_metadata,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
    row_index,
    expected_postage,
):
    service_one['permissions'] += ['letter', 'international_letters']
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=9)
    mocker.patch(
        'app.main.views.send.s3download',
        return_value='''
            address line 1,     address line 3,  address line 6,
            Firstname Lastname, 123 Example St., SW1A 1AA
            Firstname Lastname, 123 Example St., France
        '''
    )

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        row_index=row_index,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one('.letter-postage').text) == expected_postage


@pytest.mark.parametrize('file_contents, expected_error,', [
    (
        """
            telephone,name
            +447700900986
        """,
        (
            'There’s a problem with your column names '
            'Your file needs a column called ‘phone number’. '
            'Right now it has columns called ‘telephone’ and ‘name’.'
        )
    ),
    (
        """
            phone number
            +447700900986
        """,
        (
            'Your column names need to match the double brackets in your template '
            'Your file is missing a column called ‘name’.'
        )
    ),
    (
        """
            phone number, phone number, PHONE_NUMBER
            +447700900111,+447700900222,+447700900333,
        """,
        (
            'There’s a problem with your column names '
            'We found more than one column called ‘phone number’ or ‘PHONE_NUMBER’. '
            'Delete or rename one of these columns and try again.'
        )
    ),
    (
        """
            phone number, name
        """,
        (
            'Your file is missing some rows '
            'It needs at least one row of data.'
        )
    ),
    (
        "+447700900986",
        (
            'Your file is missing some rows '
            'It needs at least one row of data, and columns called ‘name’ and ‘phone number’.'
        )
    ),
    (
        "",
        (
            'Your file is missing some rows '
            'It needs at least one row of data, and columns called ‘name’ and ‘phone number’.'
        )
    ),
    (
        """
            phone number, name
            +447700900986, example
            , example
            +447700900986, example
        """,
        (
            'There’s a problem with example.csv '
            'You need to enter missing data in 1 row.'
        )
    ),
    (
        """
            phone number, name
            +447700900986, example
            +447700900986,
            +447700900986, example
        """,
        (
            'There’s a problem with example.csv '
            'You need to enter missing data in 1 row.'
        )
    ),
])
def test_upload_csv_file_with_missing_columns_shows_error(
    client_request,
    mocker,
    mock_get_service_template_with_placeholders,
    mock_s3_set_metadata,
    mock_s3_get_metadata,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    service_one,
    fake_uuid,
    file_contents,
    expected_error,
):

    mocker.patch('app.main.views.send.s3download', return_value=file_contents)

    page = client_request.post(
        'main.send_messages', service_id=service_one['id'], template_id=fake_uuid,
        _data={'file': (BytesIO(''.encode('utf-8')), 'example.csv')},
        _follow_redirects=True,
    )

    with client_request.session_transaction() as session:
        assert 'file_uploads' not in session

    assert page.select_one('input[type=file]').has_attr('accept')
    assert page.select_one('input[type=file]')['accept'] == '.csv,.xlsx,.xls,.ods,.xlsm,.tsv'
    assert normalize_spaces(page.select('.banner-dangerous')[0].text) == expected_error


def test_upload_csv_invalid_extension(
    logged_in_client,
    mock_login,
    service_one,
    mock_get_service_template,
    fake_uuid,
):

    resp = logged_in_client.post(
        url_for('main.send_messages', service_id=service_one['id'], template_id=fake_uuid),
        data={'file': (BytesIO('contents'.encode('utf-8')), 'invalid.txt')},
        content_type='multipart/form-data',
        follow_redirects=True
    )

    assert resp.status_code == 200
    assert "invalid.txt is not a spreadsheet that Notify can read" in resp.get_data(as_text=True)


def test_upload_valid_csv_redirects_to_check_page(
    client_request,
    mock_get_service_template_with_placeholders,
    mock_s3_upload,
    mock_s3_set_metadata,
    fake_uuid,
):
    client_request.post(
        'main.send_messages', service_id=SERVICE_ONE_ID, template_id=fake_uuid,
        _data={'file': (BytesIO(''.encode('utf-8')), 'valid.csv')},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.check_messages',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            upload_id=fake_uuid,
            _external=True,
        ),
    )


@pytest.mark.parametrize('extra_args, expected_link_in_first_row, expected_recipient, expected_message', [
    (
        {},
        None,
        'To: 07700900001',
        'Test Service: A, Template <em>content</em> with & entity',
    ),
    (
        {'row_index': 2},
        None,
        'To: 07700900001',
        'Test Service: A, Template <em>content</em> with & entity',
    ),
    (
        {'row_index': 4},
        True,
        'To: 07700900003',
        'Test Service: C, Template <em>content</em> with & entity',
    ),
])
def test_upload_valid_csv_shows_preview_and_table(
    client_request,
    mocker,
    mock_get_live_service,
    mock_get_service_template_with_placeholders,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    fake_uuid,
    extra_args,
    expected_link_in_first_row,
    expected_recipient,
    expected_message,
):

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {'template_id': fake_uuid}
        }

    mocker.patch('app.main.views.send.s3download', return_value="""
        phone number,name,thing,thing,thing
        07700900001, A,   foo,  foo,  foo
        07700900002, B,   foo,  foo,  foo
        07700900003, C,   foo,  foo,
    """)

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        **extra_args
    )

    mock_s3_set_metadata.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        notification_count=3,
        template_id=fake_uuid,
        valid=True,
        original_file_name='example.csv',
    )

    assert page.h1.text.strip() == 'Preview of Two week reminder'
    assert page.select_one('.sms-message-recipient').text.strip() == expected_recipient
    assert page.select_one('.sms-message-wrapper').text.strip() == expected_message

    assert page.select_one('.table-field-index').text.strip() == '2'

    if expected_link_in_first_row:
        assert page.select_one('.table-field-index a')['href'] == url_for(
            'main.check_messages',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            upload_id=fake_uuid,
            row_index=2,
            original_file_name='example.csv',
        )
    else:
        assert not page.select_one('.table-field-index').select_one('a')

    for row_index, row in enumerate([
        (
            '<td class="table-field-left-aligned"> <div class=""> 07700900001 </div> </td>',
            '<td class="table-field-left-aligned"> <div class=""> A </div> </td>',
            (
                '<td class="table-field-left-aligned"> '
                '<div class="table-field-status-default"> '
                '<ul> '
                '<li>foo</li> <li>foo</li> <li>foo</li> '
                '</ul> '
                '</div> '
                '</td>'
            )
        ),
        (
            '<td class="table-field-left-aligned"> <div class=""> 07700900002 </div> </td>',
            '<td class="table-field-left-aligned"> <div class=""> B </div> </td>',
            (
                '<td class="table-field-left-aligned"> '
                '<div class="table-field-status-default"> '
                '<ul> '
                '<li>foo</li> <li>foo</li> <li>foo</li> '
                '</ul> '
                '</div> '
                '</td>'
            )
        ),
        (
            '<td class="table-field-left-aligned"> <div class=""> 07700900003 </div> </td>',
            '<td class="table-field-left-aligned"> <div class=""> C </div> </td>',
            (
                '<td class="table-field-left-aligned"> '
                '<div class="table-field-status-default"> '
                '<ul> '
                '<li>foo</li> <li>foo</li> '
                '</ul> '
                '</div> '
                '</td>'
            )
        ),
    ]):
        for index, cell in enumerate(row):
            row = page.select('table tbody tr')[row_index]
            assert 'id' not in row
            assert normalize_spaces(str(row.select('td')[index + 1])) == cell


def test_upload_valid_csv_only_sets_meta_if_filename_known(
    client_request,
    mocker,
    mock_get_live_service,
    mock_get_service_letter_template,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    mock_template_preview,
    fake_uuid,
):

    mocker.patch('app.main.views.send.s3download', return_value="""
        addressline1, addressline2, postcode
        House       , 1 Street    , SW1A 1AA
    """)
    mocker.patch(
        'app.main.views.send.get_page_count_for_letter',
        return_value=5,
    )

    client_request.get(
        'no_cookie.check_messages_preview',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        filetype='pdf',
        _test_page_title=False,
    )

    assert len(mock_s3_set_metadata.call_args_list) == 0


def test_show_all_columns_if_there_are_duplicate_recipient_columns(
    client_request,
    mocker,
    mock_get_live_service,
    mock_get_service_template_with_placeholders,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
    mock_s3_get_metadata,
):

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {'template_id': fake_uuid}
        }

    mocker.patch('app.main.views.send.s3download', return_value="""
        phone number, phone_number, PHONENUMBER
        07700900001,  07700900002,  07700900003
    """)

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one('thead').text) == (
        'Row in file1 phone number phone_number PHONENUMBER'
    )
    assert normalize_spaces(page.select_one('tbody').text) == (
        '2 07700900003 07700900003 07700900003'
    )


@pytest.mark.parametrize('row_index, expected_status', [
    (0, 404),
    (1, 404),
    (2, 200),
    (3, 200),
    (4, 200),
    (5, 404),
])
def test_404_for_previewing_a_row_out_of_range(
    client_request,
    mocker,
    mock_get_live_service,
    mock_get_service_template_with_placeholders,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    fake_uuid,
    row_index,
    expected_status,
):

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {'template_id': fake_uuid}
        }

    mocker.patch('app.main.views.send.s3download', return_value="""
        phone number,name,thing,thing,thing
        07700900001, A,   foo,  foo,  foo
        07700900002, B,   foo,  foo,  foo
        07700900003, C,   foo,  foo,  foo
    """)

    client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        row_index=row_index,
        _expected_status=expected_status,
    )


@pytest.mark.parametrize('template_type', ['sms', 'email', 'letter'])
def test_send_one_off_step_redirects_to_start_if_session_not_setup(
    mocker,
    client_request,
    mock_get_service_statistics,
    mock_get_users_by_service,
    mock_has_no_jobs,
    mock_get_no_contact_lists,
    fake_uuid,
    template_type,
):
    template_data = create_template(template_type=template_type, content='Hi ((name))')
    mocker.patch('app.service_api_client.get_service_template', return_value={'data': template_data})

    with client_request.session_transaction() as session:
        assert 'recipient' not in session
        assert 'placeholders' not in session

    client_request.get(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=0,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.send_one_off',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True,
        )
    )


def test_send_one_off_does_not_send_without_the_correct_permissions(
    client_request,
    mock_get_service_template,
    service_one,
    fake_uuid,
):
    template_id = fake_uuid
    service_one['permissions'] = []

    page = client_request.get(
        '.send_one_off',
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
        _follow_redirects=True,
        _expected_status=403,
    )

    assert page.select('main p')[0].text.strip() == "Sending text messages has been disabled for your service."
    assert page.select(".govuk-back-link")[0].text == "Back"
    assert page.select(".govuk-back-link")[0]['href'] == url_for(
        '.view_template',
        service_id=service_one['id'],
        template_id=template_id,
    )


@pytest.mark.parametrize('user', (
    create_active_user_with_permissions(),
    create_active_caseworking_user(),
))
def test_send_one_off_has_correct_page_title(
    logged_in_client,
    service_one,
    mock_has_no_jobs,
    mock_get_no_contact_lists,
    fake_uuid,
    mocker,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user)
    template_data = create_template(template_type='sms', name='Two week reminder', content='Hi there ((name))')
    mocker.patch('app.service_api_client.get_service_template', return_value={'data': template_data})
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=9)

    response = logged_in_client.get(
        url_for(
            'main.send_one_off',
            service_id=service_one['id'],
            template_id=fake_uuid,
            step_index=0
        ),
        follow_redirects=True,
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert response.status_code == 200
    assert page.h1.text.strip() == "Send ‘Two week reminder’"

    assert len(page.select('.banner-tour')) == 0


@pytest.mark.parametrize('step_index, prefilled, expected_field_label', [
    (
        0,
        {},
        'phone number',
    ),
    (
        1,
        {'phone number': '07900900123'},
        'one',
    ),
    (
        2,
        {'phone number': '07900900123', 'one': 'one'},
        'two',
    ),
])
def test_send_one_off_shows_placeholders_in_correct_order(
    client_request,
    fake_uuid,
    mock_has_no_jobs,
    mock_get_no_contact_lists,
    mock_get_service_template_with_multiple_placeholders,
    step_index,
    prefilled,
    expected_field_label,
):
    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = prefilled

    page = client_request.get(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=step_index,
    )

    assert normalize_spaces(page.select_one('label').text) == expected_field_label


@pytest.mark.parametrize('user, template_type, expected_link_text, expected_link_url', [
    (
        create_active_user_with_permissions(),
        'sms',
        'Use my phone number',
        partial(url_for, 'main.send_one_off_to_myself')
    ),
    (
        create_active_user_with_permissions(),
        'email',
        'Use my email address',
        partial(url_for, 'main.send_one_off_to_myself')
    ),
    (
        create_active_user_with_permissions(),
        'letter',
        None, None
    ),
    (
        create_active_caseworking_user(),
        'sms',
        None, None
    ),
])
def test_send_one_off_has_skip_link(
    client_request,
    service_one,
    fake_uuid,
    mock_get_service_email_template,
    mock_has_no_jobs,
    mock_get_no_contact_lists,
    mocker,
    template_type,
    expected_link_text,
    expected_link_url,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user)
    template_data = create_template(template_id=fake_uuid, template_type=template_type)
    mocker.patch('app.service_api_client.get_service_template', return_value={'data': template_data})
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=9)

    page = client_request.get(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=0,
        _follow_redirects=True,
    )

    skip_links = page.select('form a')

    if expected_link_text and expected_link_url:
        assert skip_links[1].text.strip() == expected_link_text
        assert skip_links[1]['href'] == expected_link_url(
            service_id=service_one['id'],
            template_id=fake_uuid,
        )
    else:
        with pytest.raises(IndexError):
            skip_links[1]


@pytest.mark.parametrize('template_type, expected_sticky', [
    ('sms', False),
    ('email', True),
    ('letter', False),
])
def test_send_one_off_has_sticky_header_for_email(
    mocker,
    client_request,
    fake_uuid,
    mock_has_no_jobs,
    mock_get_no_contact_lists,
    template_type,
    expected_sticky,
):
    template_data = create_template(template_type=template_type, content='((body))')
    mocker.patch('app.service_api_client.get_service_template', return_value={'data': template_data})
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=9)

    page = client_request.get(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=0,
        _follow_redirects=True,
    )

    assert bool(page.select('.js-stick-at-top-when-scrolling')) == expected_sticky


def test_send_one_off_has_sticky_header_for_letter_on_non_address_placeholders(
    mocker,
    client_request,
    fake_uuid,
    mock_get_live_service,
):
    template_data = create_template(template_type='letter', content='((body))')
    mocker.patch('app.service_api_client.get_service_template', return_value={'data': template_data})
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=9)

    with client_request.session_transaction() as session:
        session['recipient'] = ''
        session['placeholders'] = {
            'address line 1': 'foo',
            'address line 2': 'bar',
            'address line 3': '',
            'address line 4': '',
            'address line 5': '',
            'address line 6': '',
            'postcode': 'SW1 1AA',
        }

    page = client_request.get(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=7,  # letter template has 7 placeholders – we’re at the end
        _follow_redirects=True,
    )
    assert page.select('.js-stick-at-top-when-scrolling')


@pytest.mark.parametrize('user', (
    create_active_user_with_permissions(),
    create_active_caseworking_user(),
))
def test_skip_link_will_not_show_on_sms_one_off_if_service_has_no_mobile_number(
    client_request,
    service_one,
    fake_uuid,
    mock_get_service_template,
    mock_has_no_jobs,
    mock_get_no_contact_lists,
    mocker,
    user,
):
    user['mobile_number'] = None
    client_request.login(user)

    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}

    page = client_request.get(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=0,
    )
    skip_link = page.findAll('a', text='Use my phone number')
    assert not skip_link


@pytest.mark.parametrize('user', (
    create_active_user_with_permissions(),
    create_active_caseworking_user(),
))
def test_send_one_off_offers_link_to_upload(
    client_request,
    fake_uuid,
    mock_get_service_template,
    mock_has_jobs,
    mock_get_no_contact_lists,
    user,
):
    client_request.login(user)

    page = client_request.get(
        'main.send_one_off',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _follow_redirects=True,
    )

    back_link = page.select('main a')[0]
    link = page.select_one('form a')

    assert back_link.text.strip() == 'Back'

    assert link.text.strip() == 'Upload a list of phone numbers'
    assert link['href'] == url_for(
        'main.send_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )


def test_send_one_off_has_link_to_use_existing_list(
    client_request,
    mock_get_service_template,
    mock_has_jobs,
    mock_get_contact_lists,
    fake_uuid,
):
    page = client_request.get(
        'main.send_one_off',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _follow_redirects=True,
    )

    assert [
        (link.text, link['href']) for link in page.select('form a')
    ] == [
        (
            'Upload a list of phone numbers',
            url_for(
                'main.send_messages',
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
        ),
        (
            'Use an emergency list',
            url_for(
                'main.choose_from_contact_list',
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
        ),
        (
            'Use my phone number',
            url_for(
                'main.send_one_off_to_myself',
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
        ),
    ]


def test_no_link_to_use_existing_list_for_service_without_lists(
    mocker,
    client_request,
    mock_get_service_template,
    mock_has_jobs,
    fake_uuid,
):
    mocker.patch(
        'app.models.contact_list.ContactLists.client_method',
        return_value=[],
    )
    client_request.login(create_platform_admin_user())
    page = client_request.get(
        'main.send_one_off',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _follow_redirects=True,
    )
    assert [
        link.text for link in page.select('form a')
    ] == [
        'Upload a list of phone numbers',
        'Use my phone number',
    ]


@pytest.mark.parametrize('user', (
    create_active_user_with_permissions(),
    create_active_caseworking_user(),
))
def test_link_to_upload_not_offered_when_entering_personalisation(
    client_request,
    fake_uuid,
    mock_get_service_template_with_placeholders,
    mock_has_jobs,
    user
):
    client_request.login(user)

    with client_request.session_transaction() as session:
        session['recipient'] = '07900900900'
        session['placeholders'] = {'phone number': '07900900900'}

    page = client_request.get(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=1,
    )

    # We’re entering personalisation
    assert page.select_one('input[type=text]')['name'] == 'placeholder_value'
    assert page.select_one('label[for=placeholder_value]').text.strip() == 'name'
    # …but first link on the page is ‘Back’, so not preceeded by ‘Upload’
    assert page.select_one('main a').text == 'Back'
    assert 'Upload' not in page.select_one('main').text


@pytest.mark.parametrize('user', (
    create_active_user_with_permissions(),
    create_active_caseworking_user(),
))
def test_send_one_off_redirects_to_end_if_step_out_of_bounds(
    client_request,
    mock_has_no_jobs,
    mock_get_service_template_with_placeholders,
    fake_uuid,
    mocker,
    user,
):
    client_request.login(user)

    with client_request.session_transaction() as session:
        session['recipient'] = '07900900123'
        session['placeholders'] = {'name': 'foo', 'phone number': '07900900123'}

    client_request.get(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=999,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.check_notification',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True,
        )
    )


@pytest.mark.parametrize('user', (
    create_active_user_with_permissions(),
    create_active_caseworking_user(),
))
def test_send_one_off_redirects_to_start_if_you_skip_steps(
    platform_admin_client,
    service_one,
    fake_uuid,
    mock_get_service_letter_template,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_has_no_jobs,
    mocker,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user)

    with platform_admin_client.session_transaction() as session:
        session['placeholders'] = {'address_line_1': 'foo'}

    response = platform_admin_client.get(url_for(
        'main.send_one_off_step',
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=7,  # letter template has 7 placeholders – we’re at the end
    ))
    assert response.status_code == 302
    assert response.location == url_for(
        'main.send_one_off',
        service_id=service_one['id'],
        template_id=fake_uuid,
        _external=True,
    )


@pytest.mark.parametrize('user', (
    create_active_user_with_permissions(),
    create_active_caseworking_user(),
))
def test_send_one_off_redirects_to_start_if_index_out_of_bounds_and_some_placeholders_empty(
    client_request,
    service_one,
    fake_uuid,
    mock_get_service_email_template,
    mock_s3_download,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_has_no_jobs,
    mocker,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user)
    with client_request.session_transaction() as session:
        session['placeholders'] = {'name': 'foo'}

    client_request.get(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=999,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.send_one_off',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True,
        ),
    )


@pytest.mark.parametrize('user', (
    create_active_user_with_permissions(),
    create_active_caseworking_user(),
))
def test_send_one_off_sms_message_redirects(
    client_request,
    mocker,
    service_one,
    fake_uuid,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user)
    template = {'data': {'template_type': 'sms', 'folder': None}}
    mocker.patch('app.service_api_client.get_service_template', return_value=template)

    client_request.get(
        'main.send_one_off',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=302,
        _expected_response=url_for(
            'main.send_one_off_step',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            step_index=0,
            _external=True,
        )
    )


@pytest.mark.parametrize('user', (
    create_active_user_with_permissions(),
    create_active_caseworking_user(),
))
def test_send_one_off_email_to_self_without_placeholders_redirects_to_check_page(
    client_request,
    mocker,
    service_one,
    mock_get_service_email_template_without_placeholders,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_has_no_jobs,
    fake_uuid,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user)

    with client_request.session_transaction() as session:
        session['recipient'] = 'foo@bar.com'
        session['placeholders'] = {'email address': 'foo@bar.com'}

    page = client_request.get(
        'main.send_one_off_step',
        step_index=1,
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _follow_redirects=True,
    )

    assert page.select('h1')[0].text.strip() == 'Preview of ‘Two week reminder’'


@pytest.mark.parametrize('permissions, expected_back_link_endpoint, extra_args', (
    (
        {'send_messages', 'manage_templates'},
        'main.view_template',
        {'template_id': unchanging_fake_uuid}
    ),
    (
        {'send_messages'},
        'main.choose_template',
        {},
    ),
    (
        {'send_messages', 'view_activity'},
        'main.choose_template',
        {},
    ),
))
def test_send_one_off_step_0_back_link(
    client_request,
    active_user_with_permissions,
    mock_login,
    mock_get_service,
    mock_get_service_template_with_placeholders,
    mock_has_no_jobs,
    mock_get_contact_lists,
    permissions,
    expected_back_link_endpoint,
    extra_args,
):
    active_user_with_permissions['permissions'][SERVICE_ONE_ID] = permissions
    client_request.login(active_user_with_permissions)

    with client_request.session_transaction() as session:
        session['placeholders'] = {}
        session['recipient'] = None

    page = client_request.get(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=unchanging_fake_uuid,
        step_index=0
    )

    assert page.select('.govuk-back-link')[0]['href'] == url_for(
        expected_back_link_endpoint,
        service_id=SERVICE_ONE_ID,
        **extra_args
    )


def test_send_one_off_sms_message_back_link_with_multiple_placeholders(
    client_request,
    mock_get_service_template_with_multiple_placeholders,
    mock_has_no_jobs,
):
    with client_request.session_transaction() as session:
        session['recipient'] = '07900900123'
        session['placeholders'] = {'phone number': '07900900123', 'one': 'bar'}

    page = client_request.get(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=unchanging_fake_uuid,
        step_index=2,
    )

    assert page.select_one('.govuk-back-link')['href'] == url_for(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=unchanging_fake_uuid,
        step_index=1,
    )


def test_send_one_off_letter_redirects_to_right_url(
    platform_admin_client,
    fake_uuid,
    mock_get_service_letter_template,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mocker,
):
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=9)
    with platform_admin_client.session_transaction() as session:
        session['recipient'] = ''
        session['placeholders'] = {
            'address line 1': 'foo',
            'address line 2': 'bar',
            'address line 3': '',
            'address line 4': '',
            'address line 5': '',
            'address line 6': '',
            'address line 7': 'SW1 1AA',
        }

    response = platform_admin_client.get(url_for(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=7,  # letter template has 7 placeholders – we’re at the end
    ))

    assert response.status_code == 302
    assert response.location.startswith(url_for(
        'main.check_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _external=True,
    ))


def test_send_one_off_populates_field_from_session(
    client_request,
    mocker,
    service_one,
    mock_login,
    mock_get_service,
    mock_get_service_template_with_placeholders,
    fake_uuid,
):

    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}
        session['placeholders']['name'] = 'Jo'

    page = client_request.get(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=1,
    )

    assert page.select('input')[0]['value'] == 'Jo'


def test_send_one_off_back_link_populates_address_textarea(
    client_request,
    mocker,
    mock_get_service_letter_template,
    mock_template_preview,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {'address line 1': 'foo', 'address line 2': 'bar', 'address line 3': ''}

    # imagine someone hit the back button to go from line 3 page to line 2 page
    page = client_request.get(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=2,
        _follow_redirects=True
    )

    assert page.select_one('h1').text.strip() == 'Send ‘Two week reminder’'

    form = page.select_one('form')
    assert form.select_one('label').text.strip() == 'Address'

    textarea = form.select_one('textarea')
    assert textarea.attrs['name'] == 'address'
    assert textarea.text == '\r\nfoo\nbar'


@pytest.mark.parametrize('placeholder', (
    'address_line_1',
    'address_line_2',
    'address_line_3',
    'address_line_4',
    'address_line_5',
    'address_line_6',
    'address_line_7',
    'postcode',
))
def test_send_one_off_letter_copes_with_placeholder_from_address_block(
    client_request,
    mocker,
    fake_uuid,
    mock_template_preview,
    no_letter_contact_blocks,
    placeholder,
):
    mocker.patch(
        'app.service_api_client.get_service_template',
        return_value={'data': template_json(
            SERVICE_ONE_ID,
            fake_uuid,
            name="Awkward letter",
            type_="letter",
            subject=f"Hello (({placeholder}))",
            content="We need to talk about ((thing))",
        )},
    )
    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}

    page = client_request.post(
        'main.send_one_off_letter_address',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={'address': '''
            foo
            bar
            SW1A 1AA
        '''},
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one('form label').text) == 'thing'
    assert page.select_one('form input[type=text]')['name'] == 'placeholder_value'
    assert page.select_one('form input[type=text]').get('value') is None

    with client_request.session_transaction() as session:
        assert session['placeholders'] == {
            'address_line_1': 'foo',
            'address_line_2': 'bar',
            'address_line_3': '',
            'address_line_4': '',
            'address_line_5': '',
            'address_line_6': '',
            'address_line_7': 'SW1A 1AA',
            'postcode': 'SW1A 1AA',
        }

    back_link = page.select_one('.govuk-back-link')['href']
    assert back_link == url_for(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=1,
    )
    previous_page = client_request.get_url(back_link, _follow_redirects=True)

    # We’ve skipped past the address placeholder and gone back to the
    # address block
    assert normalize_spaces(previous_page.select_one('form label').text) == 'Address'


@pytest.mark.parametrize('last_line, expected_postage', (
    ('France', 'Postage: international'),
    ('SW1A 1AA', 'Postage: second class'),
))
def test_send_one_off_letter_shows_international_postage(
    client_request,
    service_one,
    mocker,
    fake_uuid,
    mock_get_service_letter_template_with_placeholders,
    mock_template_preview,
    no_letter_contact_blocks,
    last_line,
    expected_postage,
):
    service_one['permissions'] += ['letter', 'international_letters']

    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}

    page = client_request.post(
        'main.send_one_off_letter_address',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={'address': f'''
            123 Example Street
            Paris
            {last_line}
        '''},
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one('form label').text) == 'name'
    assert normalize_spaces(page.select_one('.letter-postage').text) == expected_postage


def test_send_one_off_sms_message_puts_submitted_data_in_session(
    client_request,
    service_one,
    mock_get_service_template_with_placeholders,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_contact_lists,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['recipient'] = '07700 900762'
        session['placeholders'] = {'phone number': '07700 900762'}

    client_request.post(
        'main.send_one_off_step',
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=1,
        _data={'placeholder_value': 'Jo'},
        _expected_status=302,
        _expected_redirect=url_for(
            'main.check_notification',
            service_id=service_one['id'],
            template_id=fake_uuid,
            _external=True,
        )
    )

    with client_request.session_transaction() as session:
        assert session['recipient'] == '07700 900762'
        assert session['placeholders'] == {'phone number': '07700 900762', 'name': 'Jo'}


@pytest.mark.parametrize('filetype', ['pdf', 'png'])
def test_send_test_works_as_letter_preview(
    filetype,
    platform_admin_client,
    mock_get_service_letter_template,
    mock_get_users_by_service,
    mock_get_service_statistics,
    service_one,
    fake_uuid,
    mocker,
):
    service_one['permissions'] = ['letter']
    mocker.patch('app.service_api_client.get_service', return_value={"data": service_one})
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=1)
    mocked_preview = mocker.patch(
        'app.main.views.send.TemplatePreview.from_utils_template',
        return_value='foo'
    )

    service_id = service_one['id']
    template_id = fake_uuid
    with platform_admin_client.session_transaction() as session:
        session['placeholders'] = {'address_line_1': 'Jo Lastname'}
    response = platform_admin_client.get(
        url_for(
            'no_cookie.send_test_preview',
            service_id=service_id,
            template_id=template_id,
            filetype=filetype
        )
    )

    mock_get_service_letter_template.assert_called_with(service_id, template_id, None)

    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'foo'
    assert mocked_preview.call_args[0][0].id == template_id
    assert type(mocked_preview.call_args[0][0]) == LetterImageTemplate
    assert mocked_preview.call_args[0][0].values == {'addressline1': 'Jo Lastname'}
    assert mocked_preview.call_args[0][1] == filetype


def test_send_one_off_clears_session(
    client_request,
    mocker,
    service_one,
    fake_uuid,
):
    template = {'data': {'template_type': 'sms', 'folder': None}}
    mocker.patch('app.service_api_client.get_service_template', return_value=template)

    with client_request.session_transaction() as session:
        session['recipient'] = '07700900001'
        session['placeholders'] = {'foo': 'bar'}

    client_request.get(
        'main.send_one_off',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=302,
    )

    with client_request.session_transaction() as session:
        assert session['recipient'] is None
        assert session['placeholders'] == {}


def test_send_one_off_redirects_to_letter_address(client_request, fake_uuid, mock_get_service_letter_template):
    with client_request.session_transaction() as session:
        session['placeholders'] = {'foo': 'some old data that we dont care about'}

    client_request.get(
        'main.send_one_off',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_redirect=url_for(
            'main.send_one_off_letter_address',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True,
        )
    )
    # make sure it cleared session first
    with client_request.session_transaction() as session:
        assert session['recipient'] is None
        assert session['placeholders'] == {}


def test_send_one_off_letter_address_shows_form(
    client_request,
    fake_uuid,
    mock_get_service_letter_template,
    mock_template_preview,
):
    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}

    page = client_request.get(
        'main.send_one_off_letter_address',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid
    )

    assert page.select_one('h1').text.strip() == 'Send ‘Two week reminder’'

    form = page.select_one('form')

    assert form.select_one('label').text.strip() == 'Address'
    assert form.select_one('textarea').attrs['name'] == 'address'

    upload_link = form.select_one('a')

    assert upload_link.text.strip() == 'Upload a list of addresses'
    assert upload_link['href'] == url_for(
        'main.send_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )

    assert (
        page.find_all('a', {'class': 'govuk-back-link'})[0]['href']
    ) == url_for('main.view_template', service_id=SERVICE_ONE_ID, template_id=fake_uuid)


@pytest.mark.parametrize(['form_data', 'expected_placeholders'], [
    # minimal
    ('\n'.join(['a', 'b', 'sw1a1aa']), {
        'address_line_1': 'a',
        'address_line_2': 'b',
        'address_line_3': '',
        'address_line_4': '',
        'address_line_5': '',
        'address_line_6': '',
        'address_line_7': 'SW1A 1AA',
        'postcode': 'SW1A 1AA',
    }),
    # maximal
    ('\n'.join(['a', 'b', 'c', 'd', 'e', 'f', 'sw1a1aa']), {
        'address_line_1': 'a',
        'address_line_2': 'b',
        'address_line_3': 'c',
        'address_line_4': 'd',
        'address_line_5': 'e',
        'address_line_6': 'f',
        'address_line_7': 'SW1A 1AA',
        'postcode': 'SW1A 1AA',
    }),
    # it ignores empty lines and strips whitespace from each line.
    # It also strips extra whitespace from the middle of lines.
    ('\n  a\ta  \n\n\n      \n\n\n\nb  b   \r\n sw1a1aa \n\n', {
        'address_line_1': 'a\ta',
        'address_line_2': 'b b',
        'address_line_3': '',
        'address_line_4': '',
        'address_line_5': '',
        'address_line_6': '',
        'address_line_7': 'SW1A 1AA',
        'postcode': 'SW1A 1AA',
    }),
])
def test_send_one_off_letter_address_populates_address_fields_in_session(
    client_request,
    fake_uuid,
    mock_get_service_letter_template,
    mock_template_preview,
    form_data,
    expected_placeholders
):
    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}

    client_request.post(
        'main.send_one_off_letter_address',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={'address': form_data},
        # there are no additional placeholders so go straight to the check page
        _expected_redirect=url_for(
            'main.check_notification',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True,
        ),
    )
    with client_request.session_transaction() as session:
        assert session['placeholders'] == expected_placeholders


@pytest.mark.parametrize('form_data, extra_permissions, expected_error_message', [
    (
        '',
        [],
        'Cannot be empty'
    ),
    (
        'a\n\n\n\nb',
        [],
        'Address must be at least 3 lines long',
    ),
    (
        '\n'.join(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']),
        [],
        'Address must be no more than 7 lines long'
    ),
    (
        '\n'.join(['a', 'b', 'c', 'd', 'e', 'f', 'g']),
        [],
        'Last line of the address must be a real UK postcode',
    ),
    (
        '\n'.join(['a', 'b', 'c', 'd', 'e', 'france']),
        [],
        'You do not have permission to send letters to other countries',
    ),
    (
        '\n'.join(['a', 'b', 'c', 'd', 'e', 'f', 'g']),
        ['international_letters'],
        'Last line of the address must be a UK postcode or another country',
    ),
    (
        'a\n(b\nSW1A 1AA',
        [],
        'Address lines must not start with any of the following characters: @ ( ) = [ ] ” \\ / ,',
    ),
])
def test_send_one_off_letter_address_rejects_bad_addresses(
    client_request,
    service_one,
    fake_uuid,
    mock_get_service_letter_template,
    mock_template_preview,
    form_data,
    extra_permissions,
    expected_error_message
):
    service_one['permissions'] += extra_permissions

    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}

    page = client_request.post(
        'main.send_one_off_letter_address',
        _data={'address': form_data},
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=200
    )

    error = page.select('form .error-message')
    assert normalize_spaces(error[0].text) == expected_error_message


def test_send_one_off_letter_address_goes_to_next_placeholder(client_request, mock_template_preview, mocker):
    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}

    template_data = create_template(template_type='letter', content='((foo))')

    mocker.patch('app.service_api_client.get_service_template', return_value={'data': template_data})

    client_request.post(
        'main.send_one_off_letter_address',
        service_id=SERVICE_ONE_ID,
        template_id=template_data['id'],
        _data={'address': 'a\nb\nSW1A 1AA'},
        # step 0-6 represent address line 1-6 and postcode. step 7 is the first non address placeholder
        _expected_redirect=url_for(
            'main.send_one_off_step',
            service_id=SERVICE_ONE_ID,
            template_id=template_data['id'],
            step_index=7,
            _external=True,
        )
    )


def test_download_example_csv(
    logged_in_client,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_get_service_template_with_placeholders_same_as_recipient,
    mock_has_permissions,
    fake_uuid
):

    response = logged_in_client.get(
        url_for('main.get_example_csv', service_id=fake_uuid, template_id=fake_uuid),
        follow_redirects=True
    )
    assert response.status_code == 200
    assert response.get_data(as_text=True) == (
        'phone number,name,date\r\n'
        '07700 900321,example,example\r\n'
    )
    assert 'text/csv' in response.headers['Content-Type']


def test_upload_csvfile_with_valid_phone_shows_all_numbers(
    logged_in_client,
    mock_get_service_template,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_live_service,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    service_one,
    fake_uuid,
    mock_s3_upload,
    mocker,
):

    mocker.patch(
        'app.main.views.send.s3download',
        return_value='\n'.join(['phone number'] + [
            '07700 9007{0:02d}'.format(final_two) for final_two in range(0, 53)
        ])
    )

    response = logged_in_client.post(
        url_for('main.send_messages', service_id=service_one['id'], template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'example.csv')},
        content_type='multipart/form-data',
        follow_redirects=True
    )
    with logged_in_client.session_transaction() as session:
        assert 'file_uploads' not in session

    assert mock_s3_set_metadata.call_count == 2
    assert mock_s3_set_metadata.call_args_list[0] == mocker.call(
        SERVICE_ONE_ID,
        fake_uuid,
        original_file_name='example.csv'
    )
    assert mock_s3_set_metadata.call_args_list[1] == mocker.call(
        SERVICE_ONE_ID,
        fake_uuid,
        notification_count=53,
        template_id=fake_uuid,
        valid=True,
        original_file_name='example.csv',
    )

    content = response.get_data(as_text=True)
    assert response.status_code == 200
    assert '07700 900701' in content
    assert '07700 900749' in content
    assert '07700 900750' not in content
    assert 'Only showing the first 50 rows' in content

    mock_get_service_statistics.assert_called_once_with(service_one['id'], today_only=True)


@pytest.mark.parametrize('international_sms_permission, should_allow_international', [
    (False, False),
    (True, True),
])
def test_upload_csvfile_with_international_validates(
    mocker,
    api_user_active,
    logged_in_client,
    mock_get_service_template,
    mock_s3_set_metadata,
    mock_s3_get_metadata,
    mock_s3_upload,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
    international_sms_permission,
    should_allow_international,
    service_one,
):
    if international_sms_permission:
        service_one['permissions'] += ('sms', 'international_sms')
    mocker.patch('app.service_api_client.get_service', return_value={'data': service_one})

    mocker.patch('app.main.views.send.s3download', return_value='')
    mock_recipients = mocker.patch(
        'app.main.views.send.RecipientCSV',
        return_value=RecipientCSV("", template=SMSPreviewTemplate(
            {'content': 'foo', 'template_type': 'sms'}
        )),
    )

    response = logged_in_client.post(
        url_for('main.send_messages', service_id=fake_uuid, template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'example.csv')},
        content_type='multipart/form-data',
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert mock_recipients.call_args[1]['allow_international_sms'] == should_allow_international


def test_job_from_contact_list_knows_where_its_come_from(
    client_request,
    mocker,
    service_one,
    mock_get_service_template,
    mock_s3_download,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    fake_uuid
):
    page = client_request.get(
        'main.check_messages',
        service_id=service_one['id'],
        upload_id=fake_uuid,
        template_id=fake_uuid,
        contact_list_id=unchanging_fake_uuid,
    )
    assert page.select_one(
        'form input[type=hidden][name=contact_list_id]'
    )['value'] == str(unchanging_fake_uuid)


def test_test_message_can_only_be_sent_now(
    client_request,
    mocker,
    service_one,
    mock_get_service_template,
    mock_s3_download,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    fake_uuid
):
    content = client_request.get(
        'main.check_messages',
        service_id=service_one['id'],
        upload_id=fake_uuid,
        template_id=fake_uuid,
        from_test=True
    )

    assert 'name="scheduled_for"' not in content


def test_letter_can_only_be_sent_now(
    client_request,
    mocker,
    mock_get_live_service,
    mock_get_service_letter_template,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
):
    mocker.patch(
        'app.main.views.send.s3download',
        return_value="addressline1, addressline2, postcode\na,b,sw1 1aa"
    )
    mocker.patch('app.main.views.send.set_metadata_on_csv_upload')
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=1)

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
        template_id=fake_uuid,
    )

    assert 'name="scheduled_for"' not in page
    assert normalize_spaces(
        page.select_one('main [type=submit]').text
    ) == (
        'Send 1 letter'
    )


def test_send_button_is_correctly_labelled(
    client_request,
    mocker,
    mock_get_live_service,
    mock_get_service_template,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
    mock_s3_get_metadata,
):
    mocker.patch('app.main.views.send.s3download', return_value='\n'.join(
        ['phone_number'] + (['07900900123'] * 1000)
    ))
    mocker.patch('app.main.views.send.set_metadata_on_csv_upload')

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
        template_id=fake_uuid,
    )

    assert normalize_spaces(
        page.select_one('main [type=submit]').text
    ) == (
        'Send 1,000 text messages'
    )


@pytest.mark.parametrize('when', [
    '', '2016-08-25T13:04:21.767198'
])
@pytest.mark.parametrize('contact_list_id', [
    '', unchanging_fake_uuid,
])
def test_create_job_should_call_api(
    client_request,
    mock_create_job,
    mock_get_job,
    mock_get_notifications,
    mock_get_service_template,
    mock_get_service_data_retention,
    mocker,
    fake_uuid,
    when,
    contact_list_id,
):
    data = mock_get_job(SERVICE_ONE_ID, fake_uuid)['data']
    job_id = data['id']
    original_file_name = data['original_file_name']
    template_id = data['template']
    notification_count = data['notification_count']
    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': template_id,
                'notification_count': notification_count,
                'valid': True
            }
        }

    page = client_request.post(
        'main.start_job',
        service_id=SERVICE_ONE_ID,
        upload_id=job_id,
        original_file_name=original_file_name,
        _data={
            'scheduled_for': when,
            'contact_list_id': contact_list_id,
        },
        _follow_redirects=True,
        _expected_status=200,
    )

    assert original_file_name in page.text

    mock_create_job.assert_called_with(
        job_id,
        SERVICE_ONE_ID,
        scheduled_for=when,
        contact_list_id=str(contact_list_id),
    )


def test_can_start_letters_job(
    platform_admin_client,
    mock_create_job,
    service_one,
    fake_uuid
):
    with platform_admin_client.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': fake_uuid,
                'notification_count': 123,
                'valid': True
            }
        }

    response = platform_admin_client.post(
        url_for('main.start_job', service_id=service_one['id'], upload_id=fake_uuid),
        data={}
    )
    assert response.status_code == 302
    assert 'just_sent=yes' in response.location


@pytest.mark.parametrize('filetype, extra_args, expected_values, expected_page', [
    (
        'png',
        {},
        {'postcode': 'abc123', 'addressline1': '123 street'},
        1
    ),
    (
        'pdf',
        {},
        {'postcode': 'abc123', 'addressline1': '123 street'},
        None
    ),
    (
        'png',
        {'row_index': 2},
        {'postcode': 'abc123', 'addressline1': '123 street'},
        1
    ),
    (
        'png',
        {'row_index': 3},
        {'postcode': 'cba321', 'addressline1': '321 avenue'},
        1
    ),
    (
        'png',
        {'row_index': 3, 'page': 2},
        {'postcode': 'cba321', 'addressline1': '321 avenue'},
        '2'
    ),
    (
        # pdf expected page is always None
        'pdf',
        {'row_index': 3, 'page': 2},
        {'postcode': 'cba321', 'addressline1': '321 avenue'},
        None
    ),
])
def test_should_show_preview_letter_message(
    filetype,
    platform_admin_client,
    mock_get_service_letter_template,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    service_one,
    fake_uuid,
    mocker,
    extra_args,
    expected_values,
    expected_page
):
    service_one['permissions'] = ['letter']
    mocker.patch('app.service_api_client.get_service', return_value={"data": service_one})
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=1)

    mocker.patch(
        'app.main.views.send.s3download',
        return_value='\n'.join(
            ['address line 1, postcode'] +
            ['123 street, abc123'] +
            ['321 avenue, cba321']
        )
    )
    mocker.patch(
        'app.main.views.send.get_csv_metadata',
        return_value={'original_file_name': f'example.{filetype}'},
    )
    mocked_preview = mocker.patch(
        'app.main.views.send.TemplatePreview.from_utils_template',
        return_value='foo'
    )

    service_id = service_one['id']
    template_id = fake_uuid
    with platform_admin_client.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': fake_uuid,
                'notification_count': 1,
                'valid': True
            }
        }

    response = platform_admin_client.get(
        url_for(
            'no_cookie.check_messages_preview',
            service_id=service_id,
            template_id=fake_uuid,
            upload_id=fake_uuid,
            filetype=filetype,
            **extra_args
        )
    )

    mock_get_service_letter_template.assert_called_with(service_id, template_id, None)

    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'foo'
    assert mocked_preview.call_args[0][0].id == template_id
    assert type(mocked_preview.call_args[0][0]) == LetterPreviewTemplate
    assert mocked_preview.call_args[0][1] == filetype
    assert mocked_preview.call_args[0][0].values == expected_values
    assert mocked_preview.call_args[1] == {'page': expected_page}


def test_dont_show_preview_letter_templates_for_bad_filetype(
    logged_in_client,
    mock_get_service_template,
    service_one,
    fake_uuid
):
    resp = logged_in_client.get(
        url_for(
            'no_cookie.check_messages_preview',
            service_id=service_one['id'],
            template_id=fake_uuid,
            upload_id=fake_uuid,
            filetype='blah'
        )
    )
    assert resp.status_code == 404
    assert mock_get_service_template.called is False


@pytest.mark.parametrize('route, response_code', [
    ('main.send_messages', 200),
    ('main.get_example_csv', 200),
    ('main.send_one_off', 302)
])
def test_route_permissions(
    mocker,
    app_,
    client,
    api_user_active,
    service_one,
    mock_get_service_template,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_notifications,
    mock_create_job,
    mock_s3_upload,
    fake_uuid,
    route,
    response_code,
):
    validate_route_permission(
        mocker,
        app_,
        "GET",
        response_code,
        url_for(
            route,
            service_id=service_one['id'],
            template_id=fake_uuid
        ),
        ['view_activity', 'send_messages'],
        api_user_active,
        service_one)


@pytest.mark.parametrize('route, response_code, method', [
    ('main.check_notification', 200, 'GET'),
    ('main.send_notification', 302, 'POST')
])
def test_route_permissions_send_check_notifications(
    mocker,
    app_,
    client,
    api_user_active,
    service_one,
    mock_send_notification,
    mock_get_service_template,
    fake_uuid,
    route,
    response_code,
    method
):
    with client.session_transaction() as session:
        session['recipient'] = '07700900001'
        session['placeholders'] = {'name': 'a'}
    validate_route_permission_with_client(
        mocker,
        client,
        method,
        response_code,
        url_for(
            route,
            service_id=service_one['id'],
            template_id=fake_uuid
        ),
        ['send_messages'],
        api_user_active,
        service_one
    )


@pytest.mark.parametrize('route, expected_status', [
    ('main.send_messages', 403),
    ('main.get_example_csv', 403),
    ('main.send_one_off', 403),
])
def test_route_permissions_sending(
    mocker,
    app_,
    client,
    api_user_active,
    service_one,
    mock_get_service_template,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_notifications,
    mock_create_job,
    fake_uuid,
    route,
    expected_status,
):
    validate_route_permission(
        mocker,
        app_,
        "GET",
        expected_status,
        url_for(
            route,
            service_id=service_one['id'],
            template_type='sms',
            template_id=fake_uuid),
        ['blah'],
        api_user_active,
        service_one)


@pytest.mark.parametrize(
    'template_type, has_placeholders, extra_args, expected_url',
    [
        (
            'sms',
            False,
            dict(),
            partial(url_for, '.send_messages')
        ),
        (
            'sms',
            True,
            dict(),
            partial(url_for, '.send_messages')
        ),
        (
            'letter',
            False,
            dict(from_test=True),
            partial(url_for, '.send_one_off')
        ),
        (
            'sms',
            True,
            dict(from_test=True),
            partial(url_for, '.send_one_off')
        )
    ]
)
def test_check_messages_back_link(
    client_request,
    mock_get_user_by_email,
    mock_get_users_by_service,
    mock_has_permissions,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_download,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    fake_uuid,
    mocker,
    template_type,
    has_placeholders,
    extra_args,
    expected_url
):
    content = 'Hi there ((name))' if has_placeholders else 'Hi there'
    template_data = create_template(template_id=fake_uuid, template_type=template_type, content=content)
    mocker.patch('app.service_api_client.get_service_template', return_value={'data': template_data})

    mocker.patch(
        'app.main.views.send.get_page_count_for_letter',
        return_value=5,
    )

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'original_file_name': 'valid.csv',
                'template_id': fake_uuid,
                'notification_count': 1,
                'valid': True
            }
        }

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
        template_id=fake_uuid,
        _test_page_title=False,
        **extra_args
    )

    assert (
        page.find_all('a', {'class': 'govuk-back-link'})[0]['href']
    ) == expected_url(service_id=SERVICE_ONE_ID, template_id=fake_uuid)


def test_shows_link_to_end_tour(
    client_request,
    mock_get_notification,
    fake_uuid,
):

    page = client_request.get(
        'main.view_notification',
        service_id=SERVICE_ONE_ID,
        notification_id=fake_uuid,
        help=3,
    )

    assert page.select(".banner-tour a")[0]['href'] == url_for(
        'main.go_to_dashboard_after_tour',
        service_id=SERVICE_ONE_ID,
        example_template_id='5407f4db-51c7-4150-8758-35412d42186a',
    )


def test_go_to_dashboard_after_tour_link(
    logged_in_client,
    mocker,
    api_user_active,
    mock_login,
    mock_get_service,
    mock_has_permissions,
    mock_delete_service_template,
    fake_uuid
):

    resp = logged_in_client.get(
        url_for('main.go_to_dashboard_after_tour', service_id=fake_uuid, example_template_id=fake_uuid)
    )

    assert resp.status_code == 302
    assert resp.location == url_for("main.service_dashboard", service_id=fake_uuid, _external=True)
    mock_delete_service_template.assert_called_once_with(fake_uuid, fake_uuid)


@pytest.mark.parametrize('num_requested,expected_msg', [
    (0, '‘example.csv’ contains 1,234 phone numbers.'),
    (1, 'You can still send 49 messages today, but ‘example.csv’ contains 1,234 phone numbers.')
], ids=['none_sent', 'some_sent'])
def test_check_messages_shows_too_many_messages_errors(
    mocker,
    client_request,
    mock_get_service,  # set message_limit to 50
    mock_get_users_by_service,
    mock_get_service_template,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
    num_requested,
    expected_msg,
    mock_s3_get_metadata
):
    # csv with 100 phone numbers
    mocker.patch('app.main.views.send.s3download', return_value=',\n'.join(
        ['phone number'] + ([mock_get_users_by_service(None)[0]['mobile_number']] * 1234)
    ))
    mocker.patch('app.service_api_client.get_service_statistics', return_value={
        'sms': {'requested': num_requested, 'delivered': 0, 'failed': 0},
        'email': {'requested': 0, 'delivered': 0, 'failed': 0}
    })

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': fake_uuid,
                'notification_count': 1,
                'valid': True
            }
        }

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        _test_page_title=False,
    )

    assert page.find('h1').text.strip() == 'Too many recipients'
    assert page.find('div', class_='banner-dangerous').find('a').text.strip() == 'trial mode'

    # remove excess whitespace from element
    details = page.find('div', class_='banner-dangerous').find_all('p')[1]
    details = ' '.join([line.strip() for line in details.text.split('\n') if line.strip() != ''])
    assert details == expected_msg


def test_check_messages_shows_trial_mode_error(
    client_request,
    mock_s3_get_metadata,
    mock_get_users_by_service,
    mock_get_service_template,
    mock_has_permissions,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
    mocker
):
    mocker.patch('app.main.views.send.s3download', return_value=(
        'phone number,\n07900900321'  # Not in team
    ))

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': '',
            }
        }

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        _test_page_title=False,
    )

    assert ' '.join(
        page.find('div', class_='banner-dangerous').text.split()
    ) == (
        'You cannot send to this phone number '
        'In trial mode you can only send to yourself and members of your team'
    )


@pytest.mark.parametrize('restricted, error_should_be_shown', [
    (True, True),
    (False, False),
])
@pytest.mark.parametrize('number_of_rows, expected_error_message', [
    (1, 'You cannot send this letter'),
    (11, 'You cannot send these letters'),  # Less than trial mode limit
    (111, 'You cannot send these letters'),  # More than trial mode limit
])
def test_check_messages_shows_trial_mode_error_for_letters(
    client_request,
    service_one,
    mock_get_service_letter_template,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    fake_uuid,
    mocker,
    restricted,
    error_should_be_shown,
    number_of_rows,
    expected_error_message,
):
    service_one['restricted'] = restricted
    mocker.patch('app.service_api_client.get_service', return_value={'data': service_one})

    mocker.patch('app.main.views.send.s3download', return_value='\n'.join(
        ['address_line_1,address_line_2,postcode,'] +
        ['First Last,    123 Street,    SW1 1AA'] * number_of_rows
    ))
    mocker.patch(
        'app.main.views.send.get_page_count_for_letter',
        return_value=3,
    )

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': '',
            }
        }

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        _test_page_title=False,
    )

    error = page.select('.banner-dangerous')

    if error_should_be_shown:
        assert normalize_spaces(error[0].text) == (
            '{} '
            'In trial mode you can only preview how your letters will look'
        ).format(expected_error_message)
    else:
        assert not error

    assert len(page.select('.letter img')) == 3

    if number_of_rows > 1:
        assert page.select_one('.table-field-index a').text == '3'


@pytest.mark.parametrize('number_of_rows, expected_error_message', [
    (1, 'This letter is'),
    (11, 'These letters are'),  # TODO: Pluralise too many pages error message for multiple letters
])
def test_check_messages_does_not_allow_to_send_letter_longer_than_10_pages(
    client_request,
    api_user_active,
    mock_get_service_letter_template,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    fake_uuid,
    mocker,
    mock_get_live_service,
    number_of_rows,
    expected_error_message,
):
    mocker.patch('app.main.views.send.s3download', return_value='\n'.join(
        ['address_line_1,address_line_2,postcode,'] +
        ['First Last,    123 Street,    SW1 1AA'] * number_of_rows
    ))
    mocker.patch(
        'app.main.views.send.get_page_count_for_letter',
        return_value=11,
    )

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': '',
            }
        }

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        _test_page_title=False,
    )
    assert page.find('h1', {"data-error-type": "letter-too-long"})

    assert len(page.select('.letter img')) == 10  # if letter longer than 10 pages, only 10 first pages are displayed
    assert not page.select('main [type=submit]')


def test_check_messages_shows_data_errors_before_trial_mode_errors_for_letters(
    mocker,
    client_request,
    mock_get_service_letter_template,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
    mock_s3_get_metadata,
):

    mocker.patch('app.main.views.send.s3download', return_value='\n'.join(
        ['address_line_1,address_line_2,postcode,'] +
        ['              ,              ,SW1 1AA'] +
        ['              ,              ,SW1 1AA']
    ))

    mocker.patch(
        'app.main.views.send.get_page_count_for_letter',
        return_value=5,
    )

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': '',
                'original_file_name': 'example.csv',
            }
        }

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'There’s a problem with example.csv '
        'You need to fix 2 addresses.'
    )
    assert not page.select('.table-field-index a')


@pytest.mark.parametrize('uploaded_file_name', (
    pytest.param('applicants.ods'),  # normal job
    pytest.param('thisisatest.csv', marks=pytest.mark.xfail),  # different template version
    pytest.param('send_me_later.csv'),  # should look at scheduled job
    pytest.param('full_of_regret.csv', marks=pytest.mark.xfail),  # job is cancelled
))
def test_warns_if_file_sent_already(
    client_request,
    mock_get_users_by_service,
    mock_get_live_service,
    mock_get_service_template,
    mock_has_permissions,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    fake_uuid,
    mocker,
    uploaded_file_name,
):
    mocker.patch('app.main.views.send.s3download', return_value=(
        'phone number,\n07900900321'
    ))
    mocker.patch(
        'app.main.views.send.get_csv_metadata',
        return_value={'original_file_name': uploaded_file_name},
    )
    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id="5d729fbd-239c-44ab-b498-75a985f3198f",
        upload_id=fake_uuid,
        original_file_name=uploaded_file_name,
        _test_page_title=False,
    )

    assert normalize_spaces(
        page.select_one('.banner-dangerous').text
    ) == (
        'These messages have already been sent today '
        'If you need to resend them, rename the file and upload it again.'
    )

    mock_get_jobs.assert_called_once_with(SERVICE_ONE_ID, limit_days=0)


def test_check_messages_column_error_doesnt_show_optional_columns(
    mocker,
    client_request,
    mock_get_service_letter_template,
    mock_has_permissions,
    fake_uuid,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
):

    mocker.patch('app.main.views.send.s3download', return_value='\n'.join(
        ['address_line_1,address_line_2,foo'] +
        ['First Lastname,1 Example Road,SW1 1AA']
    ))

    mocker.patch(
        'app.main.views.send.get_page_count_for_letter',
        return_value=5,
    )

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': '',
                'original_file_name': '',
            }
        }

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'There’s a problem with your column names '
        'Your file needs at least 3 address columns, for example ‘address line 1’, '
        '‘address line 2’ and ‘address line 3’. '
        'Right now it has columns called ‘address_line_1’, ‘address_line_2’ and ‘foo’.'
    )


def test_check_messages_adds_sender_id_in_session_to_metadata(
    client_request,
    mocker,
    mock_get_live_service,
    mock_get_service_template,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    fake_uuid,
):
    mocker.patch('app.main.views.send.s3download', return_value=(
        'phone number,\n07900900321'
    ))
    mocker.patch('app.main.views.send.get_sms_sender_from_session')

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {'template_id': fake_uuid}
        }
        session['sender_id'] = 'fake-sender'

    client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        _test_page_title=False,
    )

    mock_s3_set_metadata.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        notification_count=1,
        template_id=fake_uuid,
        sender_id='fake-sender',
        valid=True,
        original_file_name='example.csv',
    )


@pytest.mark.parametrize('extra_args', (
    {},
    {'from_test': True},
))
def test_letters_from_csv_files_dont_have_download_link(
    client_request,
    mocker,
    mock_get_service,
    mock_get_service_letter_template,
    mock_has_permissions,
    fake_uuid,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    extra_args,
):

    mocker.patch('app.main.views.send.s3download', return_value="""
        address_line_1,address_line_2,postcode,
        First Last,    123 Street,    SW1 1AA
    """)

    mocker.patch(
        'app.main.views.send.get_page_count_for_letter',
        return_value=5,
    )

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': '',
            }
        }

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        _test_page_title=False,
        **extra_args
    )

    assert normalize_spaces(
        page.select_one('.banner-dangerous').text
    ) == normalize_spaces(
        'You cannot send this letter '
        'In trial mode you can only preview how your letters will look'
    )

    assert len(page.select('.letter img')) == 5
    assert not page.select('a[download]')


@pytest.mark.parametrize('restricted', [True, False])
def test_one_off_letters_have_download_link(
    client_request,
    mocker,
    api_user_active,
    mock_get_service_letter_template,
    mock_has_permissions,
    fake_uuid,
    mock_get_users_by_service,
    mock_get_service_statistics,
    restricted,
    service_one,
):
    service_one['restricted'] = restricted
    mocker.patch('app.service_api_client.get_service', return_value={'data': service_one})

    mocker.patch(
        'app.main.views.send.get_page_count_for_letter',
        return_value=5,
    )

    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {
            'address_line_1': 'First Last',
            'address_line_2': '123 Street',
            'postcode': 'SW1 1AA',
        }

    page = client_request.get(
        'main.check_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert len(page.select('.letter img')) == 5

    assert page.select_one('a[download]')['href'] == url_for(
        'no_cookie.check_notification_preview',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        filetype='pdf',
    )
    assert page.select_one('a[download]').text == 'Download as a PDF'


def test_send_one_off_letter_errors_in_trial_mode(
    client_request,
    mocker,
    mock_get_service,
    mock_get_service_letter_template,
    mock_has_permissions,
    fake_uuid,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_s3_set_metadata,
):

    mocker.patch(
        'app.main.views.send.get_page_count_for_letter',
        return_value=5,
    )

    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {
            'address_line_1': 'First Last',
            'address_line_2': '123 Street',
            'postcode': 'SW1 1AA',
        }

    page = client_request.get(
        'main.check_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select('.banner-dangerous')) == normalize_spaces(
        'You cannot send this letter '
        'In trial mode you can only preview how your letters will look'
    )

    assert len(page.select('.letter img')) == 5

    assert not page.select('main [type=submit]')
    assert page.select_one('.govuk-back-link').text == 'Back'
    assert page.select_one('a[download]').text == 'Download as a PDF'


def test_send_one_off_letter_errors_if_letter_longer_than_10_pages(
    client_request,
    mocker,
    mock_get_live_service,
    mock_get_service_letter_template,
    mock_has_permissions,
    fake_uuid,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_s3_set_metadata,
):

    mocker.patch(
        'app.main.views.send.get_page_count_for_letter',
        return_value=11,
    )

    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {
            'address_line_1': 'First Last',
            'address_line_2': '123 Street',
            'postcode': 'SW1 1AA',
        }

    page = client_request.get(
        'main.check_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert page.find('h1', {"data-error-type": "letter-too-long"})
    assert len(page.select('.letter img')) == 10

    assert not page.select('main [type=submit]')


def test_check_messages_shows_over_max_row_error(
    client_request,
    mock_get_users_by_service,
    mock_get_service_template_with_placeholders,
    mock_has_permissions,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_s3_get_metadata,
    mock_s3_download,
    fake_uuid,
    mocker
):
    mock_recipients = mocker.patch('app.main.views.send.RecipientCSV').return_value
    mock_recipients.max_rows = 11111
    mock_recipients.__len__.return_value = 99999
    mock_recipients.too_many_rows.return_value = True

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': fake_uuid,
            }
        }

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        _test_page_title=False,
    )

    assert ' '.join(
        page.find('div', class_='banner-dangerous').text.split()
    ) == (
        'Your file has too many rows '
        'Notify can process up to 11,111 rows at once. '
        'Your file has 99,999 rows.'
    )


@pytest.mark.parametrize('existing_session_items', [
    {},
    {'recipient': '07700900001'},
    {'name': 'Jo'}
])
def test_check_notification_redirects_if_session_not_populated(
    client_request,
    service_one,
    fake_uuid,
    existing_session_items,
    mock_get_service_template_with_placeholders
):
    with client_request.session_transaction() as session:
        session.update(existing_session_items)

    client_request.get(
        'main.check_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=301,
        _expected_redirect=url_for(
            'main.send_one_off_step',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            step_index=1,
            _external=True,
        )
    )


def test_check_notification_shows_preview(
    client_request,
    service_one,
    fake_uuid,
    mock_get_service_template
):
    with client_request.session_transaction() as session:
        session['recipient'] = '07700900001'
        session['placeholders'] = {}

    page = client_request.get(
        'main.check_notification',
        service_id=service_one['id'],
        template_id=fake_uuid
    )

    assert page.h1.text.strip() == 'Preview of ‘Two week reminder’'
    assert (
        page.find_all('a', {'class': 'govuk-back-link'})[0]['href']
    ) == url_for(
        'main.send_one_off_step',
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=0,
    )

    # assert tour not visible
    assert not page.select('.banner-tour')

    # post to send_notification with help=0 to ensure no back link is then shown
    assert page.form.attrs['action'] == url_for(
        'main.send_notification',
        service_id=service_one['id'],
        template_id=fake_uuid,
        help='0'
    )


def test_check_notification_shows_back_link(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_template_preview
):
    service_one['restricted'] = False
    mocker.patch(
        'app.service_api_client.get_service_template',
        return_value={'data': template_json(
            SERVICE_ONE_ID,
            fake_uuid,
            name="Awkward letter",
            type_="letter",
            subject="We need to talk about ((thing))",
            content=f"Hello ((address line 3))",
        )},
    )
    with client_request.session_transaction() as session:
        session['recipient'] = 'foo'
        session['placeholders'] = {
            'address_line_1': 'foo',
            'address_line_2': 'bar',
            'address_line_3': '',
            'address_line_4': '',
            'address_line_5': '',
            'address_line_6': '',
            'address_line_7': 'SW1A 1AA',
            'postcode': 'SW1A 1AA',
            'thing': 'a thing',
        }

    page = client_request.get(
        'main.check_notification',
        service_id=service_one['id'],
        template_id=fake_uuid,
    )

    assert page.h1.text.strip() == 'Preview of ‘Awkward letter’'
    back_link = page.find_all('a', {'class': 'govuk-back-link'})[0]['href']
    assert back_link == url_for(
        'main.send_one_off_step',
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=7,
    )

    previous_page = client_request.get_url(back_link)
    assert normalize_spaces(previous_page.select_one('label').text) == 'thing'


@pytest.mark.parametrize('template, recipient, placeholders, expected_personalisation', (
    (
        mock_get_service_template,
        '07700900001',
        {'a': 'b'},
        {'a': 'b'},
    ),
    (
        mock_get_service_email_template,
        'test@example.com',
        {},
        {},
    ),
    (
        mock_get_service_letter_template,
        'foo',
        {},
        {},
    ),
))
def test_send_notification_submits_data(
    client_request,
    fake_uuid,
    mock_send_notification,
    mock_get_service_template,
    template,
    recipient,
    placeholders,
    expected_personalisation,
):
    with client_request.session_transaction() as session:
        session['recipient'] = recipient
        session['placeholders'] = placeholders

    client_request.post(
        'main.send_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid
    )

    mock_send_notification.assert_called_once_with(
        SERVICE_ONE_ID,
        template_id=fake_uuid,
        recipient=recipient,
        personalisation=expected_personalisation,
        sender_id=None
    )


@pytest.mark.parametrize('placeholders', (
    {'address line 1': 'Foo'},
    {'ADDRESSLINE_1': 'Foo'},
))
def test_send_notification_submits_data_for_letter(
    client_request,
    fake_uuid,
    mock_send_notification,
    mock_get_service_letter_template,
    placeholders,
):
    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = placeholders

    client_request.post(
        'main.send_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid
    )
    assert mock_send_notification.call_args[1]['recipient'] == 'Foo'


def test_send_notification_clears_session(
    client_request,
    service_one,
    fake_uuid,
    mock_send_notification,
    mock_get_service_template,
):
    with client_request.session_transaction() as session:
        session['recipient'] = '07700900001'
        session['placeholders'] = {'a': 'b'}

    client_request.post(
        'main.send_notification',
        service_id=service_one['id'],
        template_id=fake_uuid
    )

    with client_request.session_transaction() as session:
        assert 'recipient' not in session
        assert 'placeholders' not in session


def test_send_notification_redirects_if_missing_data(
    client_request,
    fake_uuid,
):
    with client_request.session_transaction() as session:
        session['placeholders'] = {'a': 'b'}

    client_request.post(
        'main.send_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=302,
        _expected_redirect=url_for(
            '.send_one_off',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True,
        ),
    )


@pytest.mark.parametrize('extra_args, extra_redirect_args', [
    ({}, {}),
    ({'help': '3'}, {'help': '3'})
])
def test_send_notification_redirects_to_view_page(
    client_request,
    fake_uuid,
    mock_send_notification,
    mock_get_service_template,
    extra_args,
    extra_redirect_args
):
    with client_request.session_transaction() as session:
        session['recipient'] = '07700900001'
        session['placeholders'] = {'a': 'b'}

    client_request.post(
        'main.send_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=302,
        _expected_redirect=url_for(
            '.view_notification',
            service_id=SERVICE_ONE_ID,
            notification_id=fake_uuid,
            _external=True,
            **extra_redirect_args
        ),
        **extra_args
    )


TRIAL_MODE_MSG = (
    'Cannot send to this recipient when service is in trial mode – '
    'see https://www.notifications.service.gov.uk/trial-mode'
)
TOO_LONG_MSG = 'Text messages cannot be longer than 918 characters. Your message is 954 characters.'
SERVICE_DAILY_LIMIT_MSG = 'Exceeded send limits (1000) for today'


@pytest.mark.parametrize('exception_msg, expected_h1, expected_err_details', [
    (
        TRIAL_MODE_MSG,
        'You cannot send to this phone number',
        'In trial mode you can only send to yourself and members of your team'
    ),
    (
        TOO_LONG_MSG,
        'Message too long',
        'Text messages cannot be longer than 918 characters. Your message is 954 characters.'
    ),
    (
        SERVICE_DAILY_LIMIT_MSG,
        'Daily limit reached',
        'You can only send 1,000 messages per day in trial mode.'
    ),
])
def test_send_notification_shows_error_if_400(
    client_request,
    service_one,
    fake_uuid,
    mocker,
    mock_get_service_template_with_placeholders,
    exception_msg,
    expected_h1,
    expected_err_details
):

    class MockHTTPError(HTTPError):
        message = exception_msg

    mocker.patch(
        'app.notification_api_client.send_notification',
        side_effect=MockHTTPError(),
    )
    with client_request.session_transaction() as session:
        session['recipient'] = '07700900001'
        session['placeholders'] = {'name': 'a' * 900}

    page = client_request.post(
        'main.send_notification',
        service_id=service_one['id'],
        template_id=fake_uuid,
        _expected_status=200
    )

    assert normalize_spaces(page.select('.banner-dangerous h1')[0].text) == expected_h1
    assert normalize_spaces(page.select('.banner-dangerous p')[0].text) == expected_err_details
    assert not page.find('input[type=submit]')


def test_send_notification_shows_email_error_in_trial_mode(
    client_request,
    fake_uuid,
    mocker,
    mock_get_service_email_template,
):
    class MockHTTPError(HTTPError):
        message = TRIAL_MODE_MSG
        status_code = 400

    mocker.patch(
        'app.notification_api_client.send_notification',
        side_effect=MockHTTPError(),
    )
    with client_request.session_transaction() as session:
        session['recipient'] = 'test@example.com'
        session['placeholders'] = {'date': 'foo', 'thing': 'bar'}

    page = client_request.post(
        'main.send_notification',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=200,
    )

    assert normalize_spaces(page.select('.banner-dangerous h1')[0].text) == (
        'You cannot send to this email address'
    )
    assert normalize_spaces(page.select('.banner-dangerous p')[0].text) == (
        'In trial mode you can only send to yourself and members of your team'
    )


@pytest.mark.parametrize('endpoint, extra_args', [
    ('main.check_messages', {
        'template_id': uuid4(), 'upload_id': uuid4()
    }),
    ('main.send_one_off_step', {
        'template_id': uuid4(), 'step_index': 0
    }),
])
@pytest.mark.parametrize('reply_to_address', [
    None,
    uuid4(),
])
def test_reply_to_is_previewed_if_chosen(
    client_request,
    mocker,
    mock_get_service_email_template,
    mock_s3_download,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_get_no_contact_lists,
    get_default_reply_to_email_address,
    fake_uuid,
    endpoint,
    extra_args,
    reply_to_address,
):
    mocker.patch('app.main.views.send.s3download', return_value="""
        email_address,date,thing
        notify@digital.cabinet-office.gov.uk,foo,bar
    """)

    with client_request.session_transaction() as session:
        session['recipient'] = 'notify@digital.cabinet-office.gov.uk'
        session['placeholders'] = {}
        session['file_uploads'] = {
            fake_uuid: {'template_id': fake_uuid}
        }
        session['sender_id'] = reply_to_address

    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        **extra_args
    )

    email_meta = page.select_one('.email-message-meta').text

    if reply_to_address:
        assert 'test@example.com' in email_meta
    else:
        assert 'test@example.com' not in email_meta


@pytest.mark.parametrize('endpoint, extra_args', [
    ('main.check_messages', {'template_id': uuid4(), 'upload_id': uuid4()}),
    ('main.send_one_off_step', {'template_id': uuid4(), 'step_index': 0}),
])
@pytest.mark.parametrize('sms_sender', [
    None,
    uuid4(),
])
def test_sms_sender_is_previewed(
    client_request,
    mocker,
    mock_get_service_template,
    mock_s3_download,
    mock_s3_get_metadata,
    mock_s3_set_metadata,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_get_jobs,
    mock_get_no_contact_lists,
    get_default_sms_sender,
    fake_uuid,
    endpoint,
    extra_args,
    sms_sender,
):

    mocker.patch('app.main.views.send.s3download', return_value="""
        phone number,date,thing
        7700900986,foo,bar
    """)

    with client_request.session_transaction() as session:
        session['recipient'] = '7700900986'
        session['placeholders'] = {}
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': fake_uuid,
                'notification_count': 1,
                'valid': True
            }
        }
        session['sender_id'] = sms_sender

    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        **extra_args
    )

    sms_sender_on_page = page.select_one('.sms-message-sender')

    if sms_sender:
        assert sms_sender_on_page.text.strip() == 'From: GOVUK'
    else:
        assert not sms_sender_on_page


def test_redirects_to_template_if_job_exists_already(
    client_request,
    mock_get_service_email_template,
    mock_get_job,
    fake_uuid,
):

    client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        original_file_name='example.csv',
        _expected_status=301,
        _expected_redirect=url_for(
            'main.send_messages',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            _external=True,
        )
    )


@pytest.mark.parametrize((
    'template_type, '
    'expected_list_id, '
    'expected_filenames, '
    'expected_time, '
    'expected_count'
), (
    (
        'email',
        '6ce466d0-fd6a-11e5-82f5-e0accb9d11a6',
        ['EmergencyContactList.xls'],
        'Uploaded today at 10:59am',
        '100 email addresses',
    ),
    (
        'sms',
        'd7b0bd1a-d1c7-4621-be5c-3c1b4278a2ad',
        ['phone number list.csv', 'UnusedList.tsv'],
        'Uploaded today at 1:00pm',
        '123 phone numbers',
    ),
))
@freeze_time('2020-03-13 13:00')
def test_choose_from_contact_list(
    mocker,
    client_request,
    mock_get_contact_lists,
    fake_uuid,
    template_type,
    expected_list_id,
    expected_filenames,
    expected_time,
    expected_count,
):
    template = create_template(template_type=template_type)
    mocker.patch(
        'app.service_api_client.get_service_template',
        return_value={'data': template},
    )
    page = client_request.get(
        'main.choose_from_contact_list',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )
    assert [
        normalize_spaces(filename.text)
        for filename in page.select('.file-list-filename-large')
    ] == expected_filenames

    assert page.select_one('a.file-list-filename-large')['href'] == url_for(
        'main.send_from_contact_list',
        service_id=SERVICE_ONE_ID,
        template_id=template['id'],
        contact_list_id=expected_list_id,
    )
    assert normalize_spaces(page.select_one('.file-list-hint-large').text) == (
        expected_time
    )
    assert normalize_spaces(page.select_one('.big-number-smallest').text) == (
        expected_count
    )


def test_choose_from_contact_list_with_personalised_template(
    mocker,
    client_request,
    mock_get_contact_lists,
    fake_uuid,
):
    template = create_template(
        content="Hey ((name)) ((thing)) is happening"
    )
    mocker.patch(
        'app.service_api_client.get_service_template',
        return_value={'data': template},
    )
    page = client_request.get(
        'main.choose_from_contact_list',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )
    assert [
        normalize_spaces(p.text) for p in page.select('main p')
    ] == [
        'You cannot use an emergency contact list with this template because '
        'it is personalised with ((name)) and ((thing)).',
        'Emergency contact lists can only include email addresses or phone numbers.',
    ]
    assert not page.select('table')


def test_choose_from_contact_list_with_no_lists(
    mocker,
    client_request,
    mock_get_service_template,
    fake_uuid,
):
    mocker.patch(
        'app.models.contact_list.ContactLists.client_method',
        return_value=[],
    )
    page = client_request.get(
        'main.choose_from_contact_list',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )
    assert [
        normalize_spaces(p.text) for p in page.select('main p')
    ] == [
        'You have not saved any lists of phone numbers yet.',
        'To upload and save an emergency contact list, go to the uploads page.',
    ]
    assert page.select_one('main p a')['href'] == url_for(
        'main.uploads',
        service_id=SERVICE_ONE_ID,
    )
    assert not page.select('table')


def test_send_from_contact_list(
    mocker,
    client_request,
    fake_uuid,
    mock_get_contact_list,
):
    new_uuid = uuid.uuid4()
    mock_download = mocker.patch('app.models.contact_list.s3download', return_value='contents')
    mock_get_metadata = mocker.patch('app.models.contact_list.get_csv_metadata', return_value={
        'example_key': 'example value',
    })
    mock_upload = mocker.patch('app.models.contact_list.s3upload', return_value=new_uuid)
    mock_set_metadata = mocker.patch('app.models.contact_list.set_metadata_on_csv_upload')
    client_request.get(
        'main.send_from_contact_list',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        contact_list_id=fake_uuid,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.check_messages',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            upload_id=new_uuid,
            contact_list_id=fake_uuid,
            _external=True,
        )
    )
    mock_download.assert_called_once_with(
        SERVICE_ONE_ID, fake_uuid, bucket='test-contact-list'
    )
    mock_get_metadata.assert_called_once_with(
        SERVICE_ONE_ID, fake_uuid, bucket='test-contact-list'
    )
    mock_upload.assert_called_once_with(
        SERVICE_ONE_ID, {'data': 'contents'}, ANY
    )
    mock_set_metadata.assert_called_once_with(
        SERVICE_ONE_ID, new_uuid, example_key='example value'
    )


def test_send_to_myself_sets_placeholder_and_redirects_for_email(
    mocker, client_request, fake_uuid, mock_get_service_email_template
):
    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}

    client_request.get(
        'main.send_one_off_to_myself',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=302,
        _expected_url=url_for(
            'main.send_one_off_step',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            step_index=1,
            _external=True,
        )
    )

    with client_request.session_transaction() as session:
        assert session['recipient'] == 'test@user.gov.uk'
        assert session['placeholders'] == {'email address': 'test@user.gov.uk'}


def test_send_to_myself_sets_placeholder_and_redirects_for_sms(
    mocker, client_request, fake_uuid, mock_get_service_template
):
    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}

    client_request.get(
        'main.send_one_off_to_myself',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=302,
        _expected_url=url_for(
            'main.send_one_off_step',
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            step_index=1,
            _external=True,
        )
    )

    with client_request.session_transaction() as session:
        assert session['recipient'] == '07700 900762'
        assert session['placeholders'] == {'phone number': '07700 900762'}


def test_send_to_myself_404s_for_letter(
    mocker, client_request, fake_uuid, mock_get_service_letter_template
):
    with client_request.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}

    client_request.get(
        'main.send_one_off_to_myself',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_status=404,
    )
