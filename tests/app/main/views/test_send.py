# -*- coding: utf-8 -*-
import sys
import uuid
from functools import partial
from glob import glob
from io import BytesIO
from itertools import repeat
from os import path
from zipfile import BadZipFile

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from notifications_python_client.errors import HTTPError
from notifications_utils.recipients import RecipientCSV
from notifications_utils.template import (
    LetterImageTemplate,
    LetterPreviewTemplate,
)
from xlrd.biffh import XLRDError
from xlrd.xldate import (
    XLDateAmbiguous,
    XLDateError,
    XLDateNegative,
    XLDateTooLarge,
)

from tests import (
    validate_route_permission,
    validate_route_permission_with_client,
)
from tests.conftest import (
    SERVICE_ONE_ID,
    active_caseworking_user,
    active_user_with_permissions,
    fake_uuid,
    mock_get_international_service,
    mock_get_live_service,
    mock_get_service,
    mock_get_service_email_template,
    mock_get_service_letter_template,
    mock_get_service_template,
    mock_get_service_template_with_placeholders,
    multiple_reply_to_email_addresses,
    multiple_sms_senders,
    multiple_sms_senders_no_inbound,
    multiple_sms_senders_with_diff_default,
    no_reply_to_email_addresses,
    no_sms_senders,
    normalize_spaces,
)

template_types = ['email', 'sms']

unchanging_fake_uuid = uuid.uuid4()

# The * ignores hidden files, eg .DS_Store
test_spreadsheet_files = glob(path.join('tests', 'spreadsheet_files', '*'))
test_non_spreadsheet_files = glob(path.join('tests', 'non_spreadsheet_files', '*'))


@pytest.mark.parametrize('template_mock, sender_data, expected_title, expected_description', [
    (
        mock_get_service_email_template,
        multiple_reply_to_email_addresses,
        'Where should replies come back to?',
        'Where should replies come back to?',
    ),
    (
        mock_get_service_template,
        multiple_sms_senders,
        'Who should the message come from?',
        'Who should the message come from?',
    )
])
def test_show_correct_title_and_description_for_sender_type(
    client_request,
    service_one,
    fake_uuid,
    template_mock,
    sender_data,
    expected_title,
    expected_description,
    mocker
):
    template_mock(mocker)
    sender_data(mocker)

    page = client_request.get(
        '.set_sender',
        service_id=service_one['id'],
        template_id=fake_uuid
    )

    assert page.select_one('h1').text == expected_title

    for element in ('legend', 'legend .visually-hidden'):
        assert normalize_spaces(page.select_one(element).text) == expected_description


@pytest.mark.parametrize('template_mock, sender_data', [
    (
        mock_get_service_email_template,
        multiple_reply_to_email_addresses,
    ),
    (
        mock_get_service_template,
        multiple_sms_senders_with_diff_default
    ),
    (
        mock_get_service_template,
        multiple_sms_senders_no_inbound
    )
])
def test_default_sender_is_checked_and_has_hint(
    client_request,
    service_one,
    fake_uuid,
    template_mock,
    sender_data,
    mocker
):
    template_mock(mocker)
    sender_data(mocker)
    page = client_request.get(
        '.set_sender',
        service_id=service_one['id'],
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


@pytest.mark.parametrize('template_mock, sender_data', [
    (
        mock_get_service_email_template,
        multiple_reply_to_email_addresses,
    ),
    (
        mock_get_service_template,
        multiple_sms_senders
    )
])
def test_sender_session_is_present_after_selected(
    logged_in_client,
    service_one,
    fake_uuid,
    template_mock,
    sender_data,
    mocker
):
    template_mock(mocker)
    sender_data(mocker)
    logged_in_client.post(
        url_for('.set_sender', service_id=service_one['id'], template_id=fake_uuid),
        data={'sender': '1234'}
    )

    with logged_in_client.session_transaction() as session:
        assert session['sender_id'] == '1234'


@pytest.mark.parametrize('template_mock, sender_data', [
    (
        mock_get_service_email_template,
        no_reply_to_email_addresses,
    ),
    (
        mock_get_service_template,
        no_sms_senders
    )
])
def test_set_sender_redirects_if_no_sender_data(
    logged_in_client,
    service_one,
    fake_uuid,
    template_mock,
    sender_data,
    mocker
):
    template_mock(mocker)
    sender_data(mocker)
    response = logged_in_client.get(
        url_for('.set_sender', service_id=service_one['id'], template_id=fake_uuid)
    )
    assert response.status_code == 302
    expected_url = url_for(
        '.send_one_off',
        service_id=service_one['id'],
        template_id=fake_uuid,
        _external=True,
    )
    assert response.location == expected_url


def test_that_test_files_exist():
    assert len(test_spreadsheet_files) == 8
    assert len(test_non_spreadsheet_files) == 6


def test_should_not_allow_files_to_be_uploaded_without_the_correct_permission(
    logged_in_client,
    mock_get_service_template,
    service_one,
    fake_uuid,
):
    template_id = fake_uuid
    service_one['permissions'] = []

    response = logged_in_client.get(url_for(
        '.send_messages',
        service_id=service_one['id'],
        template_id=template_id),
        follow_redirects=True)
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert response.status_code == 200
    assert page.select('main p')[0].text.strip() == "Sending text messages has been disabled for your service."
    assert page.select(".page-footer-back-link")[0].text == "Back to the template"
    assert page.select(".page-footer-back-link")[0]['href'] == url_for(
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
    else:
        assert not mock_s3_upload.called
        assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
            'Couldn’t read {}. Try using a different file format.'.format(filename)
        )


@pytest.mark.parametrize('exception, expected_error_message', [
    (partial(UnicodeDecodeError, 'codec', b'', 1, 2, 'reason'), (
        'Couldn’t read example.xlsx. Try using a different file format.'
    )),
    (BadZipFile, (
        'Couldn’t read example.xlsx. Try using a different file format.'
    )),
    (XLRDError, (
        'Couldn’t read example.xlsx. Try using a different file format.'
    )),
    (XLDateError, (
        'example.xlsx contains numbers or dates that Notify can’t understand. '
        'Try formatting all columns as ‘text’ or export your file as CSV.'
    )),
    (XLDateNegative, (
        'example.xlsx contains numbers or dates that Notify can’t understand. '
        'Try formatting all columns as ‘text’ or export your file as CSV.'
    )),
    (XLDateAmbiguous, (
        'example.xlsx contains numbers or dates that Notify can’t understand. '
        'Try formatting all columns as ‘text’ or export your file as CSV.'
    )),
    (XLDateTooLarge, (
        'example.xlsx contains numbers or dates that Notify can’t understand. '
        'Try formatting all columns as ‘text’ or export your file as CSV.'
    )),
])
def test_shows_error_if_parsing_exception(
    logged_in_client,
    mocker,
    mock_get_service_template,
    exception,
    expected_error_message,
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


def test_upload_csvfile_with_errors_shows_check_page_with_errors(
    logged_in_client,
    service_one,
    mocker,
    mock_get_service_template_with_placeholders,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
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
        data={'file': (BytesIO(''.encode('utf-8')), 'invalid.csv')},
        content_type='multipart/form-data',
        follow_redirects=True
    )

    with logged_in_client.session_transaction() as session:
        assert 'file_uploads' not in session

    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert 'There is a problem with invalid.csv' in content
    assert '+447700900986' in content
    assert 'Missing' in content
    assert 'Re-upload your file' in content


@pytest.mark.parametrize('file_contents, expected_error,', [
    (
        """
            telephone,name
            +447700900986
        """,
        (
            'Your file needs a column called ‘phone number’ '
            'Right now it has columns called ‘telephone’ and ‘name’. '
            'Skip to file contents'
        )
    ),
    (
        """
            phone number
            +447700900986
        """,
        (
            'The columns in your file need to match the double brackets in your template '
            'Your file is missing a column called ‘name’. '
            'Skip to file contents'
        )
    ),
    (
        """
            phone number, phone number, PHONE_NUMBER
            +447700900111,+447700900222,+447700900333,
        """,
        (
            'Your file has more than one column called ‘phone number’ or ‘PHONE_NUMBER’ '
            'Delete or rename one of these columns and try again. '
            'Skip to file contents'
        )
    ),
    (
        """
            phone number, name
        """,
        (
            'Your file is missing some rows '
            'It needs at least one row of data. '
            'Skip to file contents'
        )
    ),
    (
        "+447700900986",
        (
            'Your file is missing some rows '
            'It needs at least one row of data, and columns called ‘name’ and ‘phone number’. '
            'Skip to file contents'
        )
    ),
    (
        "",
        (
            'Your file is missing some rows '
            'It needs at least one row of data, and columns called ‘name’ and ‘phone number’. '
            'Skip to file contents'
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
            'There is a problem with invalid.csv '
            'You need to enter missing data in 1 row '
            'Skip to file contents'
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
            'There is a problem with invalid.csv '
            'You need to enter missing data in 1 row '
            'Skip to file contents'
        )
    ),
])
def test_upload_csvfile_with_missing_columns_shows_error(
    client_request,
    mocker,
    mock_get_service_template_with_placeholders,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    service_one,
    fake_uuid,
    file_contents,
    expected_error,
):

    mocker.patch('app.main.views.send.s3download', return_value=file_contents)

    page = client_request.post(
        'main.send_messages', service_id=service_one['id'], template_id=fake_uuid,
        _data={'file': (BytesIO(''.encode('utf-8')), 'invalid.csv')},
        _follow_redirects=True,
    )

    with client_request.session_transaction() as session:
        assert 'file_uploads' not in session

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
    assert "invalid.txt isn’t a spreadsheet that Notify can read" in resp.get_data(as_text=True)


def test_upload_valid_csv_redirects_to_check_page(
    client_request,
    mock_get_service_template_with_placeholders,
    mock_s3_upload,
    fake_uuid,
):
    client_request.post(
        'main.send_messages', service_id=SERVICE_ONE_ID, template_id=fake_uuid,
        _data={'file': (BytesIO(''.encode('utf-8')), 'valid.csv')},
        _expected_status=302,
        expected_redirect='foo'
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
        original_file_name='example.csv',
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
            '<td class="table-field-center-aligned "> <div class=""> 07700900001 </div> </td>',
            '<td class="table-field-center-aligned "> <div class=""> A </div> </td>',
            (
                '<td class="table-field-center-aligned "> '
                '<div class="table-field-status-default"> '
                '<ul class="list list-bullet"> '
                '<li>foo</li> <li>foo</li> <li>foo</li> '
                '</ul> '
                '</div> '
                '</td>'
            )
        ),
        (
            '<td class="table-field-center-aligned "> <div class=""> 07700900002 </div> </td>',
            '<td class="table-field-center-aligned "> <div class=""> B </div> </td>',
            (
                '<td class="table-field-center-aligned "> '
                '<div class="table-field-status-default"> '
                '<ul class="list list-bullet"> '
                '<li>foo</li> <li>foo</li> <li>foo</li> '
                '</ul> '
                '</div> '
                '</td>'
            )
        ),
        (
            '<td class="table-field-center-aligned "> <div class=""> 07700900003 </div> </td>',
            '<td class="table-field-center-aligned "> <div class=""> C </div> </td>',
            (
                '<td class="table-field-center-aligned "> '
                '<div class="table-field-status-default"> '
                '<ul class="list list-bullet"> '
                '<li>foo</li> <li>foo</li> '
                '</ul> '
                '</div> '
                '</td>'
            )
        ),
    ]):
        for index, cell in enumerate(row):
            row = page.select('table tbody tr')[row_index]
            assert normalize_spaces(str(row.select('td')[index + 1])) == cell


def test_upload_valid_csv_only_sets_meta_if_filename_known(
    client_request,
    mocker,
    mock_get_live_service,
    mock_get_service_letter_template,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_s3_set_metadata,
    fake_uuid,
):

    mocker.patch('app.main.views.send.s3download', return_value="""
        addressline1, addressline2, postcode
        House       , 1 Street    , SW1A 1AA
    """)
    mocker.patch(
        'app.main.views.send.TemplatePreview.from_utils_template',
        return_value='foo'
    )

    client_request.get(
        'main.check_messages_preview',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        filetype='pdf',
        _test_page_title=False,
    )

    assert len(mock_s3_set_metadata.call_args_list) == 0


def test_file_name_truncated_to_fit_in_s3_metadata(
    client_request,
    mocker,
    mock_get_live_service,
    mock_get_service_template_with_placeholders,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_s3_set_metadata,
    fake_uuid,
):

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {'template_id': fake_uuid}
        }

    mocker.patch('app.main.views.send.s3download', return_value="""
        phone number,name,thing,thing,thing
        07700900001, A,   foo,  foo,  foo
    """)

    file_name = 'ü😁' * 2000

    client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        original_file_name=file_name,
    )
    assert sys.getsizeof(
        file_name.encode('utf-8')
    ) > 2000

    assert sys.getsizeof(''.join((
        '{}{}'.format(key, value) for key, value in
        mock_s3_set_metadata.call_args_list[0][1].items()
    )).encode('utf-8')) == 1724


def test_show_all_columns_if_there_are_duplicate_recipient_columns(
    client_request,
    mocker,
    mock_get_live_service,
    mock_get_service_template_with_placeholders,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    fake_uuid,
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


@pytest.mark.parametrize('user', (
    active_user_with_permissions,
    active_caseworking_user,
))
def test_send_test_doesnt_show_file_contents(
    logged_in_client,
    mocker,
    mock_get_service_template,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    service_one,
    fake_uuid,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user(fake_uuid))
    mocker.patch('app.main.views.send.s3download', return_value="""
        phone number
        07700 900 986
    """)

    response = logged_in_client.get(
        url_for('main.send_test', service_id=service_one['id'], template_id=fake_uuid),
        follow_redirects=True,
    )

    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.select('h1')[0].text.strip() == 'Preview of Two week reminder'
    assert len(page.select('table')) == 0
    assert len(page.select('.banner-dangerous')) == 0
    assert page.select_one('button[type=submit]').text.strip() == 'Send 1 text message'


@pytest.mark.parametrize('user, endpoint, template_mock, expected_recipient', [
    (
        active_user_with_permissions,
        'main.send_test_step',
        mock_get_service_template_with_placeholders,
        '07700 900762'
    ),
    (
        active_user_with_permissions,
        'main.send_test_step',
        mock_get_service_email_template,
        'test@user.gov.uk'
    ),
    (
        active_caseworking_user,
        'main.send_test_step',
        mock_get_service_email_template,
        'caseworker@example.gov.uk'
    ),
    (
        active_user_with_permissions,
        'main.send_test_step',
        mock_get_service_letter_template,
        None
    ),
    (
        active_user_with_permissions,
        'main.send_one_off_step',
        mock_get_service_template,
        None
    ),
    (
        active_user_with_permissions,
        'main.send_one_off_step',
        mock_get_service_email_template,
        None
    ),
    (
        active_user_with_permissions,
        'main.send_one_off_step',
        mock_get_service_letter_template,
        None
    ),
])
def test_send_test_step_redirects_if_session_not_setup(
    mocker,
    logged_in_client,
    mock_get_service_statistics,
    mock_get_users_by_service,
    fake_uuid,
    endpoint,
    template_mock,
    expected_recipient,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user(fake_uuid))
    template_mock(mocker)
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=99)

    with logged_in_client.session_transaction() as session:
        assert 'recipient' not in session
        assert 'placeholders' not in session

    response = logged_in_client.get(
        url_for(endpoint, service_id=SERVICE_ONE_ID, template_id=fake_uuid, step_index=0),
        follow_redirects=True
    )
    assert response.status_code == 200

    with logged_in_client.session_transaction() as session:
        assert session['recipient'] == expected_recipient


def test_send_one_off_does_not_send_without_the_correct_permissions(
    logged_in_client,
    mock_get_service_template,
    service_one,
    fake_uuid,
):
    template_id = fake_uuid
    service_one['permissions'] = []

    response = logged_in_client.get(url_for(
        '.send_one_off',
        service_id=service_one['id'],
        template_id=template_id),
        follow_redirects=True)
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert response.status_code == 200
    assert page.select('main p')[0].text.strip() == "Sending text messages has been disabled for your service."
    assert page.select(".page-footer-back-link")[0].text == "Back to the template"
    assert page.select(".page-footer-back-link")[0]['href'] == url_for(
        '.view_template',
        service_id=service_one['id'],
        template_id=template_id,
    )


@pytest.mark.parametrize('user', (
    active_user_with_permissions,
    active_caseworking_user,
))
@pytest.mark.parametrize('template_mock, partial_url, expected_h1, tour_shown', [
    (
        mock_get_service_template_with_placeholders,
        partial(url_for, 'main.send_test'),
        'Personalise this message',
        False,
    ),
    (
        mock_get_service_template_with_placeholders,
        partial(url_for, 'main.send_one_off'),
        'Who should this message be sent to?',
        False,
    ),
    (
        mock_get_service_template_with_placeholders,
        partial(url_for, 'main.send_test', help=1),
        'Example text message',
        True,
    ),
    (
        mock_get_service_email_template,
        partial(url_for, 'main.send_test', help=1),
        'Example text message',
        True,
    ),
    (
        mock_get_service_email_template,
        partial(url_for, 'main.send_test'),
        'Personalise this message',
        False,
    ),
    (
        mock_get_service_email_template,
        partial(url_for, 'main.send_one_off'),
        'Who should this message be sent to?',
        False,
    ),
    (
        mock_get_service_letter_template,
        partial(url_for, 'main.send_test'),
        'Print a test letter',
        False,
    ),
    (
        mock_get_service_letter_template,
        partial(url_for, 'main.send_one_off'),
        'Print a test letter',
        False,
    ),
])
def test_send_one_off_or_test_has_correct_page_titles(
    logged_in_client,
    service_one,
    fake_uuid,
    mocker,
    template_mock,
    partial_url,
    expected_h1,
    tour_shown,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user(fake_uuid))
    template_mock(mocker)
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=99)

    response = logged_in_client.get(
        partial_url(service_id=service_one['id'], template_id=fake_uuid, step_index=0),
        follow_redirects=True,
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert response.status_code == 200
    assert page.h1.text.strip() == expected_h1

    assert (len(page.select('.banner-tour')) == 1) == tour_shown


@pytest.mark.parametrize('user, template_mock, expected_link_text, expected_link_url', [
    (
        active_user_with_permissions,
        mock_get_service_template,
        'Use my phone number',
        partial(url_for, 'main.send_test')
    ),
    (
        active_user_with_permissions,
        mock_get_service_email_template,
        'Use my email address',
        partial(url_for, 'main.send_test')
    ),
    (
        active_user_with_permissions,
        mock_get_service_letter_template,
        None, None
    ),
    (
        active_caseworking_user,
        mock_get_service_template,
        None, None
    ),
])
def test_send_one_off_has_skip_link(
    logged_in_client,
    service_one,
    fake_uuid,
    mock_get_service_email_template,
    mocker,
    template_mock,
    expected_link_text,
    expected_link_url,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user(fake_uuid))
    template_mock(mocker)
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=99)

    response = logged_in_client.get(
        url_for('main.send_one_off_step', service_id=service_one['id'], template_id=fake_uuid, step_index=0),
        follow_redirects=True
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    skip_links = page.select('a.top-gutter-4-3')

    assert response.status_code == 200

    if expected_link_text and expected_link_url:
        assert skip_links[0].text.strip() == expected_link_text
        assert skip_links[0]['href'] == expected_link_url(
            service_id=service_one['id'],
            template_id=fake_uuid,
        )
    else:
        assert not skip_links


@pytest.mark.parametrize('user', (
    active_user_with_permissions,
    active_caseworking_user,
))
def test_skip_link_will_not_show_on_sms_one_off_if_service_has_no_mobile_number(
    logged_in_client,
    service_one,
    fake_uuid,
    mock_get_service_template,
    mocker,
    user,
):
    user = user(fake_uuid)
    user.mobile_number = None
    mocker.patch('app.user_api_client.get_user', return_value=user)
    response = logged_in_client.get(
        url_for('main.send_one_off_step', service_id=service_one['id'], template_id=fake_uuid, step_index=0),
        follow_redirects=True
    )
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    skip_links = page.select('a.top-gutter-4-3')
    assert not skip_links


@pytest.mark.parametrize('user', (
    active_user_with_permissions,
    active_caseworking_user,
))
@pytest.mark.parametrize('endpoint, expected_redirect, placeholders', [
    (
        'main.send_test_step',
        'main.send_test',
        {'name': 'foo'},
    ),
    (
        'main.send_one_off_step',
        'main.send_one_off',
        {'name': 'foo', 'phone number': '07900900123'},
    ),
])
def test_send_test_redirects_to_end_if_step_out_of_bounds(
    logged_in_client,
    service_one,
    fake_uuid,
    endpoint,
    placeholders,
    expected_redirect,
    mocker,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user(fake_uuid))

    with logged_in_client.session_transaction() as session:
        session['placeholders'] = placeholders

    response = logged_in_client.get(url_for(
        endpoint,
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=999,
    ))

    assert response.status_code == 302
    expected_url = url_for(
        expected_redirect,
        service_id=service_one['id'],
        template_id=fake_uuid,
        _external=True,
    )
    assert response.location == expected_url


@pytest.mark.parametrize('user', (
    active_user_with_permissions,
    active_caseworking_user,
))
@pytest.mark.parametrize('endpoint, expected_redirect', [
    ('main.send_test_step', 'main.send_test'),
    ('main.send_one_off_step', 'main.send_one_off'),
])
def test_send_test_redirects_to_start_if_you_skip_steps(
    logged_in_platform_admin_client,
    service_one,
    fake_uuid,
    mock_get_service_letter_template,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mocker,
    endpoint,
    expected_redirect,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user(fake_uuid))

    with logged_in_platform_admin_client.session_transaction() as session:
        session['send_test_letter_page_count'] = 1
        session['placeholders'] = {'address_line_1': 'foo'}

    response = logged_in_platform_admin_client.get(url_for(
        endpoint,
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=7,  # letter template has 7 placeholders – we’re at the end
    ))
    assert response.status_code == 302
    assert response.location == url_for(
        expected_redirect,
        service_id=service_one['id'],
        template_id=fake_uuid,
        _external=True,
    )


@pytest.mark.parametrize('user', (
    active_user_with_permissions,
    active_caseworking_user,
))
@pytest.mark.parametrize('endpoint, expected_redirect', [
    ('main.send_test_step', 'main.send_test'),
    ('main.send_one_off_step', 'main.send_one_off'),
])
def test_send_test_redirects_to_start_if_index_out_of_bounds_and_some_placeholders_empty(
    logged_in_client,
    service_one,
    fake_uuid,
    mock_get_service_email_template,
    mock_s3_download,
    mock_get_users_by_service,
    mock_get_service_statistics,
    endpoint,
    expected_redirect,
    mocker,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user(fake_uuid))
    with logged_in_client.session_transaction() as session:
        session['placeholders'] = {'name': 'foo'}

    response = logged_in_client.get(url_for(
        endpoint,
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=999,
    ))

    assert response.status_code == 302
    assert response.location == url_for(
        expected_redirect,
        service_id=service_one['id'],
        template_id=fake_uuid,
        _external=True,
    )


@pytest.mark.parametrize('user', (
    active_user_with_permissions,
    active_caseworking_user,
))
@pytest.mark.parametrize('endpoint, expected_redirect', [
    ('main.send_test', 'main.send_test_step'),
    ('main.send_one_off', 'main.send_one_off_step'),
])
def _redirects_with_help_argument(
    logged_in_client,
    mocker,
    service_one,
    fake_uuid,
    endpoint,
    expected_redirect,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user(fake_uuid))
    template = {'data': {'template_type': 'sms'}}
    mocker.patch('app.service_api_client.get_service_template', return_value=template)

    response = logged_in_client.get(
        url_for(endpoint, service_id=service_one['id'], template_id=fake_uuid, help=1)
    )
    assert response.status_code == 302
    assert response.location == url_for(
        expected_redirect,
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=0,
        help=1,
        _external=True,
    )


@pytest.mark.parametrize('user', (
    active_user_with_permissions,
    active_caseworking_user,
))
def test_send_test_email_message_without_placeholders_redirects_to_check_page(
    logged_in_client,
    mocker,
    service_one,
    mock_get_service_email_template_without_placeholders,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    fake_uuid,
    user,
):
    mocker.patch('app.user_api_client.get_user', return_value=user(fake_uuid))

    with logged_in_client.session_transaction() as session:
        session['recipient'] = 'foo@bar.com'

    response = logged_in_client.get(
        url_for('main.send_test', step_index=0, service_id=service_one['id'], template_id=fake_uuid),
        follow_redirects=True
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.select('h1')[0].text.strip() == 'Preview of Two week reminder'


@pytest.mark.parametrize('user, expected_back_link_endpoint, extra_args', (
    (active_user_with_permissions, 'main.view_template', {'template_id': unchanging_fake_uuid}),
    (active_caseworking_user, 'main.choose_template', {}),
))
def test_send_test_sms_message_with_placeholders_shows_first_field(
    logged_in_client,
    mocker,
    service_one,
    mock_login,
    mock_get_service,
    mock_get_service_template_with_placeholders,
    fake_uuid,
    user,
    expected_back_link_endpoint,
    extra_args,
):
    mocker.patch('app.user_api_client.get_user', return_value=user(fake_uuid))

    with logged_in_client.session_transaction() as session:
        assert 'placeholders' not in session

    response = logged_in_client.get(
        url_for(
            'main.send_test',
            service_id=service_one['id'],
            template_id=unchanging_fake_uuid,
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.select('label')[0].text.strip() == 'name'
    assert page.select('input')[0]['name'] == 'placeholder_value'
    assert page.select('.page-footer-back-link')[0]['href'] == url_for(
        expected_back_link_endpoint,
        service_id=service_one['id'],
        **extra_args
    )
    with logged_in_client.session_transaction() as session:
        assert session['recipient'] == '07700 900762'


def test_send_test_letter_clears_previous_page_cache(
    logged_in_platform_admin_client,
    mocker,
    service_one,
    mock_login,
    mock_get_service,
    mock_get_service_letter_template,
    fake_uuid,
):

    with logged_in_platform_admin_client.session_transaction() as session:
        session['send_test_letter_page_count'] = 'WRONG'

    response = logged_in_platform_admin_client.get(url_for(
        'main.send_test',
        service_id=service_one['id'],
        template_id=fake_uuid,
    ))
    assert response.status_code == 302

    with logged_in_platform_admin_client.session_transaction() as session:
        assert session['send_test_letter_page_count'] is None


def test_send_test_letter_redirects_to_right_url(
    logged_in_platform_admin_client,
    fake_uuid,
    mock_get_service_letter_template,
    mock_s3_upload,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mocker,
):

    with logged_in_platform_admin_client.session_transaction() as session:
        session['send_test_letter_page_count'] = 1
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

    response = logged_in_platform_admin_client.get(url_for(
        'main.send_one_off_step',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        step_index=7,  # letter template has 7 placeholders – we’re at the end
    ))

    assert response.status_code == 302
    assert response.location.startswith(url_for(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        _external=True,
    ))


def test_send_test_populates_field_from_session(
    logged_in_client,
    mocker,
    service_one,
    mock_login,
    mock_get_service,
    mock_get_service_template_with_placeholders,
    fake_uuid,
):

    with logged_in_client.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}
        session['placeholders']['name'] = 'Jo'

    response = logged_in_client.get(url_for(
        'main.send_test_step',
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=0,
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.select('input')[0]['value'] == 'Jo'


def test_send_test_caches_page_count(
    logged_in_client,
    mocker,
    service_one,
    mock_login,
    mock_get_service,
    mock_get_service_letter_template,
    fake_uuid,
):

    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=99)

    logged_in_client.get(
        url_for(
            'main.send_test',
            service_id=service_one['id'],
            template_id=fake_uuid,
        ),
        follow_redirects=True,
    )
    with logged_in_client.session_transaction() as session:
        assert session['send_test_letter_page_count'] == 99


def test_send_test_indicates_optional_address_columns(
    logged_in_client,
    mocker,
    service_one,
    mock_login,
    mock_get_service,
    mock_get_service_letter_template,
    fake_uuid,
):

    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=1)

    with logged_in_client.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}

    response = logged_in_client.get(url_for(
        'main.send_test_step',
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=3,
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert normalize_spaces(page.select('label')[0].text) == (
        'address line 4 '
        'Optional'
    )
    assert page.select('.page-footer-back-link')[0]['href'] == url_for(
        'main.send_one_off_step',
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=2,
    )


def test_send_test_allows_empty_optional_address_columns(
    logged_in_client,
    mocker,
    service_one,
    mock_login,
    mock_get_service,
    mock_get_service_letter_template,
    fake_uuid,
):

    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=1)

    with logged_in_client.session_transaction() as session:
        session['recipient'] = None
        session['placeholders'] = {}

    response = logged_in_client.post(
        url_for(
            'main.send_test_step',
            service_id=service_one['id'],
            template_id=fake_uuid,
            step_index=3,
        ),
        # no data here
    )

    assert response.status_code == 302
    assert response.location == url_for(
        'main.send_test_step',
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=4,
        _external=True,
    )


def test_send_test_sms_message_puts_submitted_data_in_session(
    logged_in_client,
    service_one,
    mock_get_service_template_with_placeholders,
    mock_get_users_by_service,
    mock_get_service_statistics,
    fake_uuid,
):
    with logged_in_client.session_transaction() as session:
        session['recipient'] = '07700 900762'
        session['placeholders'] = {}

    response = logged_in_client.post(
        url_for(
            'main.send_test_step',
            service_id=service_one['id'],
            template_id=fake_uuid,
            step_index=0,
        ),
        data={'placeholder_value': 'Jo'}
    )
    assert response.status_code == 302
    assert response.location == url_for(
        'main.check_notification',
        service_id=service_one['id'],
        template_id=fake_uuid,
        _external=True
    )

    with logged_in_client.session_transaction() as session:
        assert session['recipient'] == '07700 900762'
        assert session['placeholders']['name'] == 'Jo'


@pytest.mark.parametrize('filetype', ['pdf', 'png'])
def test_send_test_works_as_letter_preview(
    filetype,
    logged_in_platform_admin_client,
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
    with logged_in_platform_admin_client.session_transaction() as session:
        session['placeholders'] = {'address_line_1': 'Jo Lastname'}
    response = logged_in_platform_admin_client.get(
        url_for(
            'main.send_test_preview',
            service_id=service_id,
            template_id=template_id,
            filetype=filetype
        )
    )

    mock_get_service_letter_template.assert_called_with(service_id, template_id)

    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'foo'
    assert mocked_preview.call_args[0][0].id == template_id
    assert type(mocked_preview.call_args[0][0]) == LetterImageTemplate
    assert mocked_preview.call_args[0][0].values == {'address_line_1': 'Jo Lastname'}
    assert mocked_preview.call_args[0][1] == filetype


def test_send_test_clears_session(
    logged_in_client,
    mocker,
    service_one,
    fake_uuid,
):
    template = {'data': {'template_type': 'sms'}}
    mocker.patch('app.service_api_client.get_service_template', return_value=template)

    with logged_in_client.session_transaction() as session:
        session['recipient'] = '07700900001'
        session['placeholders'] = {'foo': 'bar'}

    response = logged_in_client.get(
        url_for(
            'main.send_test',
            service_id=service_one['id'],
            template_id=fake_uuid,
        ),
    )
    assert response.status_code == 302

    with logged_in_client.session_transaction() as session:
        assert session['recipient'] is None
        assert session['placeholders'] == {}


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
        data={'file': (BytesIO(''.encode('utf-8')), 'valid.csv')},
        content_type='multipart/form-data',
        follow_redirects=True
    )
    with logged_in_client.session_transaction() as session:
        assert 'file_uploads' not in session

    mock_s3_set_metadata.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        notification_count=53,
        template_id=fake_uuid,
        valid=True,
        original_file_name='valid.csv',
    )

    content = response.get_data(as_text=True)
    assert response.status_code == 200
    assert '07700 900701' in content
    assert '07700 900749' in content
    assert '07700 900750' not in content
    assert 'Only showing the first 50 rows' in content

    mock_get_service_statistics.assert_called_once_with(service_one['id'], today_only=True)


@pytest.mark.parametrize('service_mock, should_allow_international', [
    (mock_get_service, False),
    (mock_get_international_service, True),
])
def test_upload_csvfile_with_international_validates(
    mocker,
    api_user_active,
    logged_in_client,
    mock_get_service_template,
    mock_s3_upload,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    fake_uuid,
    service_mock,
    should_allow_international,
):

    service_mock(mocker, api_user_active)
    mocker.patch('app.main.views.send.s3download', return_value='')
    mock_recipients = mocker.patch(
        'app.main.views.send.RecipientCSV',
        return_value=RecipientCSV("", template_type="sms"),
    )

    response = logged_in_client.post(
        url_for('main.send_messages', service_id=fake_uuid, template_id=fake_uuid),
        data={'file': (BytesIO(''.encode('utf-8')), 'valid.csv')},
        content_type='multipart/form-data',
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert mock_recipients.call_args[1]['international_sms'] == should_allow_international


def test_test_message_can_only_be_sent_now(
    client_request,
    mocker,
    service_one,
    mock_get_service_template,
    mock_s3_download,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
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
    service_one,
    mock_get_service_letter_template,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_s3_set_metadata,
    mock_get_job_doesnt_exist,
    fake_uuid,
):
    mocker.patch('app.main.views.send.s3download', return_value="addressline1, addressline2, postcode\na,b,c")
    mocker.patch('app.main.views.send.set_metadata_on_csv_upload')
    mocker.patch('app.main.views.send.get_page_count_for_letter', return_value=1)

    content = client_request.get(
        'main.check_messages',
        service_id=service_one['id'],
        upload_id=fake_uuid,
        template_id=fake_uuid,
        from_test=True
    )

    assert 'name="scheduled_for"' not in content


@pytest.mark.parametrize('when', [
    '', '2016-08-25T13:04:21.767198'
])
def test_create_job_should_call_api(
    logged_in_client,
    service_one,
    mock_create_job,
    mock_get_job,
    mock_get_notifications,
    mock_get_service_template,
    mocker,
    fake_uuid,
    when
):
    service_id = service_one['id']
    data = mock_get_job(service_one['id'], fake_uuid)['data']
    job_id = data['id']
    original_file_name = data['original_file_name']
    template_id = data['template']
    notification_count = data['notification_count']
    with logged_in_client.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': template_id,
                'notification_count': notification_count,
                'valid': True
            }
        }

    response = logged_in_client.post(
        url_for(
            'main.start_job',
            service_id=service_one['id'],
            upload_id=job_id,
            original_file_name=original_file_name
        ),
        data={'scheduled_for': when},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert original_file_name in response.get_data(as_text=True)
    mock_create_job.assert_called_with(
        job_id,
        service_id,
        scheduled_for=when,
    )


def test_can_start_letters_job(
    logged_in_platform_admin_client,
    mock_create_job,
    service_one,
    fake_uuid
):
    with logged_in_platform_admin_client.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': fake_uuid,
                'notification_count': 123,
                'valid': True
            }
        }

    response = logged_in_platform_admin_client.post(
        url_for('main.start_job', service_id=service_one['id'], upload_id=fake_uuid),
        data={}
    )
    assert response.status_code == 302
    assert 'just_sent=yes' in response.location


@pytest.mark.parametrize('filetype', ['pdf', 'png'])
@pytest.mark.parametrize('extra_args, expected_values', [
    (
        {},
        {'postcode': 'abc123', 'addressline1': '123 street'},
    ),
    (
        {'row_index': 2},
        {'postcode': 'abc123', 'addressline1': '123 street'},
    ),
    (
        {'row_index': 3},
        {'postcode': 'cba321', 'addressline1': '321 avenue'},
    ),
])
def test_should_show_preview_letter_message(
    filetype,
    logged_in_platform_admin_client,
    mock_get_service_letter_template,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    service_one,
    fake_uuid,
    mocker,
    extra_args,
    expected_values,
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
    mocked_preview = mocker.patch(
        'app.main.views.send.TemplatePreview.from_utils_template',
        return_value='foo'
    )

    service_id = service_one['id']
    template_id = fake_uuid
    with logged_in_platform_admin_client.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': fake_uuid,
                'notification_count': 1,
                'valid': True
            }
        }

    response = logged_in_platform_admin_client.get(
        url_for(
            'main.check_messages_preview',
            service_id=service_id,
            template_id=fake_uuid,
            upload_id=fake_uuid,
            filetype=filetype,
            **extra_args
        )
    )

    mock_get_service_letter_template.assert_called_with(service_id, template_id)

    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'foo'
    assert mocked_preview.call_args[0][0].id == template_id
    assert type(mocked_preview.call_args[0][0]) == LetterPreviewTemplate
    assert mocked_preview.call_args[0][1] == filetype
    assert mocked_preview.call_args[0][0].values == expected_values


def test_dont_show_preview_letter_templates_for_bad_filetype(
    logged_in_client,
    mock_get_service_template,
    service_one,
    fake_uuid
):
    resp = logged_in_client.get(
        url_for(
            'main.check_messages_preview',
            service_id=service_one['id'],
            template_id=fake_uuid,
            upload_id=fake_uuid,
            filetype='blah'
        )
    )
    assert resp.status_code == 404
    assert mock_get_service_template.called is False


@pytest.mark.parametrize('route, response_code', [
    ('main.choose_template', 200),
    ('main.send_messages', 200),
    ('main.get_example_csv', 200),
    ('main.send_test', 302)
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


@pytest.mark.parametrize('route', [
    'main.choose_template',
    'main.send_messages',
    'main.get_example_csv',
    'main.send_test'
])
def test_route_invalid_permissions(
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
):
    validate_route_permission(
        mocker,
        app_,
        "GET",
        403,
        url_for(
            route,
            service_id=service_one['id'],
            template_type='sms',
            template_id=fake_uuid),
        ['blah'],
        api_user_active,
        service_one)


@pytest.mark.parametrize(
    'template_mock, extra_args, expected_url',
    [
        (
            mock_get_service_template,
            dict(),
            partial(url_for, '.send_messages')
        ),
        (
            mock_get_service_template_with_placeholders,
            dict(),
            partial(url_for, '.send_messages')
        ),
        (
            mock_get_service_letter_template,  # No placeholders
            dict(from_test=True),
            partial(url_for, '.send_test')
        ),
        (
            mock_get_service_template_with_placeholders,
            dict(from_test=True),
            partial(url_for, '.send_test')
        )
    ]
)
def test_check_messages_back_link(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_user_by_email,
    mock_get_users_by_service,
    mock_get_service,
    mock_has_permissions,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_s3_download,
    mock_s3_set_metadata,
    fake_uuid,
    mocker,
    template_mock,
    extra_args,
    expected_url
):
    template_mock(mocker)
    with logged_in_client.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'original_file_name': 'valid.csv',
                'template_id': fake_uuid,
                'notification_count': 1,
                'valid': True
            }
        }

    response = logged_in_client.get(url_for(
        'main.check_messages',
        service_id=fake_uuid,
        upload_id=fake_uuid,
        template_id=fake_uuid,
        **extra_args
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert (
        page.findAll('a', {'class': 'page-footer-back-link'})[0]['href']
    ) == expected_url(service_id=fake_uuid, template_id=fake_uuid)


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
    (0, '‘valid.csv’ contains 100 phone numbers.'),
    (1, 'You can still send 49 messages today, but ‘valid.csv’ contains 100 phone numbers.')
], ids=['none_sent', 'some_sent'])
def test_check_messages_shows_too_many_messages_errors(
    mocker,
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_users_by_service,
    mock_get_service,
    mock_get_service_template,
    mock_get_job_doesnt_exist,
    mock_has_permissions,
    fake_uuid,
    num_requested,
    expected_msg
):
    # csv with 100 phone numbers
    mocker.patch('app.main.views.send.s3download', return_value=',\n'.join(
        ['phone number'] + ([mock_get_users_by_service(None)[0].mobile_number] * 100)
    ))
    mocker.patch('app.service_api_client.get_service_statistics', return_value={
        'sms': {'requested': num_requested, 'delivered': 0, 'failed': 0},
        'email': {'requested': 0, 'delivered': 0, 'failed': 0}
    })

    with logged_in_client.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': fake_uuid,
                'notification_count': 1,
                'valid': True
            }
        }

    response = logged_in_client.get(url_for(
        'main.check_messages',
        service_id=fake_uuid,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        original_file_name='valid.csv',
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.find('h1').text.strip() == 'Too many recipients'
    assert page.find('div', class_='banner-dangerous').find('a').text.strip() == 'trial mode'

    # remove excess whitespace from element
    details = page.find('div', class_='banner-dangerous').findAll('p')[1]
    details = ' '.join([line.strip() for line in details.text.split('\n') if line.strip() != ''])
    assert details == expected_msg


def test_check_messages_shows_trial_mode_error(
    logged_in_client,
    mock_get_users_by_service,
    mock_get_service,
    mock_get_service_template,
    mock_has_permissions,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    fake_uuid,
    mocker
):
    mocker.patch('app.main.views.send.s3download', return_value=(
        'phone number,\n07900900321'  # Not in team
    ))

    with logged_in_client.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': '',
            }
        }

    response = logged_in_client.get(url_for(
        'main.check_messages',
        service_id=uuid.uuid4(),
        template_id=fake_uuid,
        upload_id=fake_uuid
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert ' '.join(
        page.find('div', class_='banner-dangerous').text.split()
    ) == (
        'You can’t send to this phone number '
        'In trial mode you can only send to yourself and members of your team '
        'Skip to file contents'
    )


@pytest.mark.parametrize('service_mock, error_should_be_shown', [
    (mock_get_service, True),
    (mock_get_live_service, False),
])
@pytest.mark.parametrize('number_of_rows, expected_error_message', [
    (1, 'You can’t send this letter'),
    (11, 'You can’t send these letters'),  # Less than trial mode limit
    (111, 'You can’t send these letters'),  # More than trial mode limit
])
def test_check_messages_shows_trial_mode_error_for_letters(
    client_request,
    api_user_active,
    mock_get_service_letter_template,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_s3_set_metadata,
    fake_uuid,
    mocker,
    service_mock,
    error_should_be_shown,
    number_of_rows,
    expected_error_message,
):
    service_mock(mocker, api_user_active)

    mocker.patch('app.main.views.send.s3download', return_value='\n'.join(
        ['address_line_1,address_line_2,postcode,'] +
        ['First Last,    123 Street,    SW1 1AA'] * number_of_rows
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

    error = page.select('.banner-dangerous')

    if error_should_be_shown:
        assert normalize_spaces(error[0].text) == (
            '{} '
            'In trial mode you can only preview how your letters will look '
            'Skip to file contents'
        ).format(expected_error_message)
    else:
        assert not error

    if number_of_rows > 1:
        assert page.select_one('.table-field-index a').text == '3'


def test_check_messages_shows_data_errors_before_trial_mode_errors_for_letters(
    mocker,
    client_request,
    mock_get_service_letter_template,
    mock_has_permissions,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    fake_uuid,
):

    mocker.patch('app.main.views.send.s3download', return_value='\n'.join(
        ['address_line_1,address_line_2,postcode,'] +
        ['              ,              ,11SW1 1AA'] +
        ['              ,              ,11SW1 1AA']
    ))

    with client_request.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': '',
                'original_file_name': 'example.xlsx',
            }
        }

    page = client_request.get(
        'main.check_messages',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        upload_id=fake_uuid,
        _test_page_title=False,
        original_file_name='example.xlsx',
    )

    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'There is a problem with example.xlsx '
        'You need to enter missing data in 2 rows '
        'Skip to file contents'
    )
    assert not page.select('.table-field-index a')


def test_check_messages_column_error_doesnt_show_optional_columns(
    mocker,
    client_request,
    mock_get_service_letter_template,
    mock_has_permissions,
    fake_uuid,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
):

    mocker.patch('app.main.views.send.s3download', return_value='\n'.join(
        ['address_line_1,address_line_2,foo'] +
        ['First Lastname,1 Example Road,SW1 1AA']
    ))

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
        'Your file needs a column called ‘postcode’ '
        'Right now it has columns called ‘address_line_1’, ‘address_line_2’ and ‘foo’. '
        'Skip to file contents'
    )


def test_generate_test_letter_doesnt_block_in_trial_mode(
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

    mocker.patch('app.main.views.send.s3download', return_value="""
        address_line_1,address_line_2,postcode,
        First Last,    123 Street,    SW1 1AA
    """)

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
        from_test=True,
        _test_page_title=False,
    )

    assert not page.select('.banner-dangerous')

    assert page.select_one('a.button').text == 'Download as a printable PDF'


def test_check_messages_shows_over_max_row_error(
    logged_in_client,
    api_user_active,
    mock_login,
    mock_get_users_by_service,
    mock_get_service,
    mock_get_service_template_with_placeholders,
    mock_has_permissions,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
    mock_s3_download,
    fake_uuid,
    mocker
):
    mock_recipients = mocker.patch('app.main.views.send.RecipientCSV').return_value
    mock_recipients.max_rows = 11111
    mock_recipients.__len__.return_value = 99999
    mock_recipients.too_many_rows.return_value = True

    with logged_in_client.session_transaction() as session:
        session['file_uploads'] = {
            fake_uuid: {
                'template_id': fake_uuid,
            }
        }

    response = logged_in_client.get(url_for(
        'main.check_messages',
        service_id=fake_uuid,
        template_id=fake_uuid,
        upload_id=fake_uuid
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert ' '.join(
        page.find('div', class_='banner-dangerous').text.split()
    ) == (
        'Your file has too many rows '
        'Notify can process up to 11,111 rows at once. '
        'Your file has 99,999 rows. '
        'Skip to file contents'
    )


@pytest.mark.parametrize('existing_session_items', [
    {},
    {'recipient': '07700900001'},
    {'name': 'Jo'}
])
def test_check_notification_redirects_if_session_not_populated(
    logged_in_client,
    service_one,
    fake_uuid,
    existing_session_items,
    mock_get_service_template_with_placeholders
):
    with logged_in_client.session_transaction() as session:
        session.update(existing_session_items)

    resp = logged_in_client.get(url_for(
        'main.check_notification',
        service_id=service_one['id'],
        template_id=fake_uuid
    ))

    assert resp.location == url_for(
        'main.send_one_off_step',
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=1,
        _external=True
    )


@pytest.mark.parametrize('existing_session_items', [
    {},
    {'recipient': '07700900001'},
    {'name': 'Jo'}
])
def test_check_notification_redirects_with_help_if_session_not_populated(
    logged_in_client,
    service_one,
    fake_uuid,
    existing_session_items,
    mock_get_service_template_with_placeholders
):
    with logged_in_client.session_transaction() as session:
        session.update(existing_session_items)

    resp = logged_in_client.get(url_for(
        'main.check_notification',
        service_id=service_one['id'],
        template_id=fake_uuid,
        help='2'
    ))

    assert resp.location == url_for(
        'main.send_test',
        service_id=service_one['id'],
        template_id=fake_uuid,
        help='2',
        _external=True
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

    assert page.h1.text.strip() == 'Preview of Two week reminder'
    assert (
        page.findAll('a', {'class': 'page-footer-back-link'})[0]['href']
    ) == url_for(
        'main.send_one_off_step',
        service_id=service_one['id'],
        template_id=fake_uuid,
        step_index=0,
    )

    # assert tour not visible
    assert not page.select('.banner-tour')
    assert page.form.attrs['action'] == url_for(
        'main.send_notification',
        service_id=service_one['id'],
        template_id=fake_uuid,
        help='0'
    )


def test_check_notification_shows_help(
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
        template_id=fake_uuid,
        help='2'
    )
    assert page.select_one('.banner-tour')
    assert page.form.attrs['action'] == url_for(
        'main.send_notification',
        service_id=service_one['id'],
        template_id=fake_uuid,
        help='3'
    )
    assert page.select_one('.page-footer-back-link')['href'] == url_for(
        'main.send_test',
        service_id=service_one['id'],
        template_id=fake_uuid,
        help='2'
    )


def test_send_notification_submits_data(
    client_request,
    service_one,
    fake_uuid,
    mock_send_notification,
):
    with client_request.session_transaction() as session:
        session['recipient'] = '07700900001'
        session['placeholders'] = {'a': 'b'}

    client_request.post(
        'main.send_notification',
        service_id=service_one['id'],
        template_id=fake_uuid
    )

    mock_send_notification.assert_called_once_with(
        service_one['id'],
        template_id=fake_uuid,
        recipient='07700900001',
        personalisation={'a': 'b'},
        sender_id=None
    )


def test_send_notification_clears_session(
    client_request,
    service_one,
    fake_uuid,
    mock_send_notification,
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
    logged_in_client,
    service_one,
    fake_uuid,
):
    with logged_in_client.session_transaction() as session:
        session['placeholders'] = {'a': 'b'}

    resp = logged_in_client.post(
        url_for('main.send_notification', service_id=service_one['id'], template_id=fake_uuid)
    )

    assert resp.status_code == 302
    assert resp.location == url_for(
        '.send_one_off',
        service_id=service_one['id'],
        template_id=fake_uuid,
        _external=True
    )


@pytest.mark.parametrize('extra_args, extra_redirect_args', [
    ({}, {}),
    ({'help': '3'}, {'help': '3'})
])
def test_send_notification_redirects_to_view_page(
    logged_in_client,
    service_one,
    fake_uuid,
    mock_send_notification,
    extra_args,
    extra_redirect_args
):
    with logged_in_client.session_transaction() as session:
        session['recipient'] = '07700900001'
        session['placeholders'] = {'a': 'b'}

    resp = logged_in_client.post(
        url_for('main.send_notification', service_id=service_one['id'], template_id=fake_uuid, **extra_args)
    )

    assert resp.status_code == 302
    assert resp.location == url_for(
        '.view_notification',
        service_id=service_one['id'],
        notification_id=fake_uuid,
        _external=True,
        **extra_redirect_args
    )


TRIAL_MODE_MSG = (
    'Can’t send to this recipient when service is in trial mode – '
    'see https://www.notifications.service.gov.uk/trial-mode'
)
TOO_LONG_MSG = 'Content for template has a character count greater than the limit of 495'
SERVICE_DAILY_LIMIT_MSG = 'Exceeded send limits (1000) for today'


@pytest.mark.parametrize('exception_msg, expected_h1, expected_err_details', [
    (
        TRIAL_MODE_MSG,
        'You can’t send to this phone number',
        'In trial mode you can only send to yourself and members of your team'
    ),
    (
        TOO_LONG_MSG,
        'Message too long',
        'Text messages can’t be longer than 459 characters. Your message is 554 characters.'
    ),
    (
        SERVICE_DAILY_LIMIT_MSG,
        'Daily limit reached',
        'You can only send 1000 messages per day in trial mode.'
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
        session['placeholders'] = {'name': 'a' * 500}

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
        'You can’t send to this email address'
    )
    assert normalize_spaces(page.select('.banner-dangerous p')[0].text) == (
        'In trial mode you can only send to yourself and members of your team'
    )


@pytest.mark.parametrize('endpoint, extra_args', [
    ('main.check_messages', {
        'template_id': fake_uuid(), 'upload_id': fake_uuid(), 'original_file_name': 'example.csv'
    }),
    ('main.send_one_off_step', {
        'template_id': fake_uuid(), 'step_index': 0
    }),
])
@pytest.mark.parametrize('reply_to_address', [
    None,
    fake_uuid(),
])
def test_reply_to_is_previewed_if_chosen(
    client_request,
    mocker,
    mock_get_service_email_template,
    mock_s3_download,
    mock_s3_set_metadata,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
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
    ('main.check_messages', {'template_id': fake_uuid(), 'upload_id': fake_uuid()}),
    ('main.send_one_off_step', {'template_id': fake_uuid(), 'step_index': 0}),
])
@pytest.mark.parametrize('sms_sender', [
    None,
    fake_uuid(),
])
def test_sms_sender_is_previewed(
    client_request,
    mocker,
    mock_get_service_template,
    mock_s3_download,
    mock_s3_set_metadata,
    mock_get_users_by_service,
    mock_get_service_statistics,
    mock_get_job_doesnt_exist,
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
