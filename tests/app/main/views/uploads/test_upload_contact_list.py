import uuid
from io import BytesIO
from unittest.mock import ANY

import pytest
from flask import url_for
from freezegun import freeze_time

from app.formatters import normalize_spaces
from tests import contact_list_json
from tests.conftest import SERVICE_ONE_ID


def test_upload_contact_list_page(client_request):
    page = client_request.get(
        'main.upload_contact_list',
        service_id=SERVICE_ONE_ID,
    )
    assert 'action' not in page.select_one('form')
    assert page.select_one('form input')['name'] == 'file'
    assert page.select_one('form input')['type'] == 'file'
    assert page.select_one('form input')['accept'] == '.csv,.xlsx,.xls,.ods,.xlsm,.tsv'

    assert normalize_spaces(page.select('.spreadsheet')[0].text) == (
        'Example A '
        '1 email address '
        '2 test@example.gov.uk'
    )
    assert normalize_spaces(page.select('.spreadsheet')[1].text) == (
        'Example A '
        '1 phone number '
        '2 07700 900123'
    )


@pytest.mark.parametrize('file_contents, expected_error, expected_thead, expected_tbody,', [
    (
        """
            telephone,name
            +447700900986
        """,
        (
            'Your file has too many columns '
            'It needs to have 1 column, called ‘email address’ or ‘phone number’. '
            'Right now it has 2 columns called ‘telephone’ and ‘name’.'
        ),
        'Row in file 1 telephone name',
        '2 +447700900986',
    ),
    (
        """
            phone number, email address
            +447700900986, test@example.com
        """,
        (
            'Your file has too many columns '
            'It needs to have 1 column, called ‘email address’ or ‘phone number’. '
            'Right now it has 2 columns called ‘phone number’ and ‘email address’.'
        ),
        'Row in file 1 phone number email address',
        '2 +447700900986 test@example.com',
    ),
    (
        """
            email address
            +447700900986
        """,
        (
            'There’s a problem with invalid.csv '
            'You need to fix 1 email address.'
        ),
        'Row in file 1 email address',
        '2 Not a valid email address +447700900986',
    ),
    (
        """
            phone number
            test@example.com
        """,
        (
            'There’s a problem with invalid.csv '
            'You need to fix 1 phone number.'
        ),
        'Row in file 1 phone number',
        '2 Must not contain letters or symbols test@example.com',
    ),
    (
        """
            phone number, phone number, PHONE_NUMBER
            +447700900111,+447700900222,+447700900333,
        """,
        (
            'Your file has too many columns '
            'It needs to have 1 column, called ‘email address’ or ‘phone number’. '
            'Right now it has 3 columns called ‘phone number’, ‘phone number’ and ‘PHONE_NUMBER’.'
        ),
        'Row in file 1 phone number phone number PHONE_NUMBER',
        '2 +447700900333 +447700900333 +447700900333',
    ),
    (
        """
            phone number
        """,
        (
            'Your file is missing some rows '
            'It needs at least one row of data.'
        ),
        'Row in file 1 phone number',
        '',
    ),
    (
        "+447700900986",
        (
            'Your file is missing some rows '
            'It needs at least one row of data, in a column called '
            '‘email address’ or ‘phone number’.'
        ),
        'Row in file 1 +447700900986',
        '',
    ),
    (
        "",
        (
            'Your file is missing some rows '
            'It needs at least one row of data, in a column called '
            '‘email address’ or ‘phone number’.'
        ),
        'Row in file 1',
        '',
    ),
    (
        """
            phone number
            +447700900986

            +447700900986
        """,
        (
            'There’s a problem with invalid.csv '
            'You need to enter missing data in 1 row.'
        ),
        'Row in file 1 phone number',
        (
            '3 Missing'
        )
    ),
    (
        """
            phone number
            +447700900
        """,
        (
            'There’s a problem with invalid.csv '
            'You need to fix 1 phone number.'
        ),
        'Row in file 1 phone number',
        '2 Not enough digits +447700900',
    ),
    (
        """
            email address
            ok@example.com
            bad@example1
            bad@example2
        """,
        (
            'There’s a problem with invalid.csv '
            'You need to fix 2 email addresses.'
        ),
        'Row in file 1 email address',
        (
            '3 Not a valid email address bad@example1 '
            '4 Not a valid email address bad@example2'
        ),
    ),
])
def test_upload_csv_file_shows_error_banner(
    client_request,
    mocker,
    mock_s3_upload,
    mock_get_job_doesnt_exist,
    mock_get_users_by_service,
    fake_uuid,
    file_contents,
    expected_error,
    expected_thead,
    expected_tbody,
):
    mock_upload = mocker.patch(
        'app.models.contact_list.s3upload',
        return_value=fake_uuid,
    )
    mock_download = mocker.patch(
        'app.models.contact_list.s3download',
        return_value=file_contents,
    )
    mock_set_metadata = mocker.patch('app.models.contact_list.set_metadata_on_csv_upload')
    mock_get_metadata = mocker.patch(
        'app.models.contact_list.get_csv_metadata',
        return_value={'original_file_name': 'invalid.csv'},
    )

    page = client_request.post(
        'main.upload_contact_list',
        service_id=SERVICE_ONE_ID,
        _data={'file': (BytesIO(''.encode('utf-8')), 'invalid.csv')},
        _follow_redirects=True,
    )
    mock_upload.assert_called_once_with(
        SERVICE_ONE_ID,
        {'data': '', 'file_name': 'invalid.csv'},
        ANY,
        bucket='test-contact-list',
    )
    mock_set_metadata.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        bucket='test-contact-list',
        original_file_name='invalid.csv'
    )
    mock_download.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        bucket='test-contact-list',
    )
    mock_get_metadata.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        bucket='test-contact-list',
    )

    assert normalize_spaces(page.select_one('.banner-dangerous').text) == expected_error

    assert page.select_one('form')['action'] == url_for(
        'main.upload_contact_list',
        service_id=SERVICE_ONE_ID,
    )
    assert page.select_one('form input')['type'] == 'file'
    assert page.select_one('form input')['accept'] == '.csv,.xlsx,.xls,.ods,.xlsm,.tsv'

    assert normalize_spaces(page.select_one('thead').text) == expected_thead
    assert normalize_spaces(page.select_one('tbody').text) == expected_tbody


def test_upload_csv_file_shows_error_banner_for_too_many_rows(
    client_request,
    mocker,
    mock_s3_upload,
    mock_get_job_doesnt_exist,
    mock_get_users_by_service,
    fake_uuid,
):
    mocker.patch('app.models.contact_list.s3upload', return_value=fake_uuid)
    mocker.patch('app.models.contact_list.set_metadata_on_csv_upload')
    mocker.patch('app.models.contact_list.s3download', return_value='\n'.join(
        ['phone number'] + (['07700900986'] * 100_001)
    ))
    mocker.patch('app.models.contact_list.get_csv_metadata',
                 return_value={'original_file_name': 'invalid.csv'})

    page = client_request.post(
        'main.upload_contact_list',
        service_id=SERVICE_ONE_ID,
        _data={'file': (BytesIO(''.encode('utf-8')), 'invalid.csv')},
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'Your file has too many rows '
        'Notify can store files up to 100,000 rows in size. '
        'Your file has 100,001 rows.'
    )
    assert len(page.select('tbody tr')) == 50
    assert normalize_spaces(page.select_one('.table-show-more-link').text) == (
        'Only showing the first 50 rows'
    )


def test_upload_csv_file_sanitises_and_truncates_file_name_in_metadata(
    client_request,
    mocker,
    mock_s3_upload,
    mock_get_job_doesnt_exist,
    mock_get_users_by_service,
    fake_uuid,
):
    mocker.patch('app.models.contact_list.s3upload', return_value=fake_uuid)
    mock_set_metadata = mocker.patch('app.models.contact_list.set_metadata_on_csv_upload')
    mocker.patch('app.models.contact_list.s3download', return_value='\n'.join(
        ['phone number'] + (['07700900986'] * 100_001)
    ))

    filename = f"😁{'a' * 2000}.csv"
    mocker.patch('app.models.contact_list.get_csv_metadata',
                 return_value={'original_file_name': filename})
    client_request.post(
        'main.upload_contact_list',
        service_id=SERVICE_ONE_ID,
        _data={'file': (BytesIO(''.encode('utf-8')), filename)},
        _follow_redirects=False
    )

    assert len(
        mock_set_metadata.call_args_list[0][1]['original_file_name']
    ) < len(filename)

    assert mock_set_metadata.call_args_list[0][1]['original_file_name'].startswith('?')


def test_upload_csv_shows_trial_mode_error(
    client_request,
    mock_get_users_by_service,
    mock_get_job_doesnt_exist,
    fake_uuid,
    mocker
):
    mocker.patch('app.models.contact_list.s3upload', return_value=fake_uuid)
    mocker.patch('app.models.contact_list.s3download', return_value=(
        'phone number\n'
        '07900900321'  # Not in team
    ))
    mocker.patch('app.models.contact_list.get_csv_metadata',
                 return_value={'original_file_name': 'invalid.csv'})

    page = client_request.get(
        'main.check_contact_list',
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'You cannot save this phone number '
        'In trial mode you can only send to yourself and members of your team'
    )
    assert page.select_one('.banner-dangerous a')['href'] == url_for(
        'main.trial_mode_new'
    )


def test_upload_csv_shows_ok_page(
    client_request,
    mock_get_live_service,
    mock_get_users_by_service,
    mock_get_job_doesnt_exist,
    fake_uuid,
    mocker
):
    mocker.patch('app.models.contact_list.s3download', return_value='\n'.join(
        ['email address'] + ['test@example.com'] * 51
    ))
    mocker.patch('app.models.contact_list.get_csv_metadata',
                 return_value={'original_file_name': 'good times.xlsx'})
    mock_metadata_set = mocker.patch('app.models.contact_list.set_metadata_on_csv_upload')

    page = client_request.get(
        'main.check_contact_list',
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
        _test_page_title=False,
    )

    mock_metadata_set.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        bucket='test-contact-list',
        row_count=51,
        original_file_name='good times.xlsx',
        template_type='email',
        valid=True,
    )

    assert normalize_spaces(page.select_one('h1').text) == (
        'good times.xlsx'
    )
    assert normalize_spaces(page.select_one('main p').text) == (
        '51 email addresses found'
    )
    assert page.select_one('form')['action'] == url_for(
        'main.save_contact_list',
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
    )

    assert normalize_spaces(page.select_one('form [type=submit]').text) == (
        'Save contact list'
    )
    assert normalize_spaces(page.select_one('thead').text) == (
        'Row in file 1 email address'
    )
    assert len(page.select('tbody tr')) == 50
    assert normalize_spaces(page.select_one('tbody tr').text) == (
        '2 test@example.com'
    )
    assert normalize_spaces(page.select_one('.table-show-more-link').text) == (
        'Only showing the first 50 rows'
    )


def test_save_contact_list(
    mocker,
    client_request,
    fake_uuid,
    mock_create_contact_list,
):
    mock_get_metadata = mocker.patch('app.models.contact_list.get_csv_metadata', return_value={
        'row_count': 999,
        'valid': True,
        'original_file_name': 'example.csv',
        'template_type': 'email'
    })
    client_request.post(
        'main.save_contact_list',
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
        _expected_status=302,
        _expected_redirect=url_for(
            'main.uploads',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_get_metadata.assert_called_once_with(
        SERVICE_ONE_ID,
        fake_uuid,
        bucket='test-contact-list',
    )
    mock_create_contact_list.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
        original_file_name='example.csv',
        row_count=999,
        template_type='email',
    )


def test_cant_save_bad_contact_list(
    mocker,
    client_request,
    fake_uuid,
    mock_create_contact_list,
):
    mocker.patch('app.models.contact_list.get_csv_metadata', return_value={
        'row_count': 999,
        'valid': False,
        'original_file_name': 'example.csv',
        'template_type': 'email'
    })
    client_request.post(
        'main.save_contact_list',
        service_id=SERVICE_ONE_ID,
        upload_id=fake_uuid,
        _expected_status=403,
    )
    assert mock_create_contact_list.called is False


@pytest.mark.parametrize('has_jobs, expected_empty_message', [
    (False, 'Not used yet.'),
    (True, 'Not used in the last 7 days.'),
])
@freeze_time('2020-06-13 16:51:56')
def test_view_contact_list(
    mocker,
    client_request,
    mock_get_contact_list,
    mock_get_no_jobs,
    mock_get_service_data_retention,
    fake_uuid,
    has_jobs,
    expected_empty_message,
):
    mocker.patch(
        'app.models.contact_list.contact_list_api_client.get_contact_list',
        return_value=contact_list_json(
            created_at='2020-03-03T12:12:12.000000Z',
            service_id=SERVICE_ONE_ID,
            has_jobs=has_jobs
        )
    )
    mocker.patch('app.models.contact_list.s3download', return_value='\n'.join(
        ['email address'] + [
            f'test-{i}@example.com' for i in range(51)
        ]
    ))
    page = client_request.get(
        'main.contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
    )
    mock_get_no_jobs.assert_called_once_with(
        SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
        limit_days=7,
        statuses={
            'finished',
            'in progress',
            'pending',
            'ready to send',
            'scheduled',
            'sending limits exceeded',
            'sent to dvla',
        },
        page=1,
    )
    assert normalize_spaces(page.select_one('h1').text) == (
        'EmergencyContactList.xls'
    )
    assert normalize_spaces(page.select('main p')[0].text) == (
        'Uploaded by Test User on 3 March at 12:12pm.'
    )
    assert normalize_spaces(page.select('main p')[1].text) == (
        expected_empty_message
    )
    assert normalize_spaces(page.select_one('main h2').text) == (
        '51 saved email addresses'
    )
    assert page.select_one('.js-stick-at-bottom-when-scrolling a[download]')['href'] == url_for(
        'main.download_contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
    )
    assert len(page.select('tbody tr')) == 50
    assert [
        normalize_spaces(page.select('tbody tr')[0].text),
        normalize_spaces(page.select('tbody tr')[1].text),

        normalize_spaces(page.select('tbody tr')[48].text),
        normalize_spaces(page.select('tbody tr')[49].text),
    ] == [
        'test-0@example.com',
        'test-1@example.com',

        'test-48@example.com',
        'test-49@example.com',
    ]
    assert 'test-50@example.com' not in page.select_one('tbody').text
    assert normalize_spaces(page.select_one('.table-show-more-link').text) == (
        'Only showing the first 50 rows'
    )


@freeze_time('2015-12-31 16:51:56')
def test_view_jobs_for_contact_list(
    mocker,
    client_request,
    mock_get_jobs,
    mock_get_service_data_retention,
    fake_uuid,
):
    mocker.patch(
        'app.models.contact_list.contact_list_api_client.get_contact_list',
        return_value={
            'created_at': '2015-12-31 12:12:12',
            'created_by': 'Test User',
            'id': fake_uuid,
            'original_file_name': 'EmergencyContactList.xls',
            'row_count': 100,
            'recent_job_count': 0,
            'has_jobs': True,
            'service_id': SERVICE_ONE_ID,
            'template_type': 'email',
        },
    )
    mocker.patch('app.models.contact_list.s3download', return_value='\n'.join(
        ['email address'] + ['test@example.com'] * 51
    ))
    page = client_request.get(
        'main.contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
    )
    assert normalize_spaces(page.select_one('h1').text) == (
        'EmergencyContactList.xls'
    )
    assert normalize_spaces(page.select('main p')[0].text) == (
        'Uploaded by Test User today at 12:12pm.'
    )
    assert normalize_spaces(page.select('main p')[1].text) == (
        'Used 6 times in the last 7 days.'
    )
    assert [
        normalize_spaces(row.text)
        for row in page.select_one('table').select('tr')
    ] == [
        'Template Status',
        (
            'Template Y '
            'Sending tomorrow at 11:09pm '
            '1 text message waiting to send'
        ),
        (
            'Template Z '
            'Sending tomorrow at 11:09am '
            '1 text message waiting to send'
        ),
        (
            'Template A '
            'Sent today at 4:51pm '
            '1 sending 0 delivered 0 failed'
        ),
        (
            'Template B '
            'Sent today at 4:51pm '
            '1 sending 0 delivered 0 failed'
        ),
        (
            'Template C '
            'Sent today at 4:51pm '
            '1 sending 0 delivered 0 failed'
        ),
        (
            'Template D '
            'Sent today at 4:51pm '
            '1 sending 0 delivered 0 failed'
        ),
    ]
    assert page.select_one('table a')['href'] == url_for(
        'main.view_job',
        service_id=SERVICE_ONE_ID,
        job_id=fake_uuid,
    )


def test_view_contact_list_404s_for_non_existing_list(
    client_request,
    mock_get_no_contact_list,
    fake_uuid,
):
    client_request.get(
        'main.contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id=uuid.uuid4(),
        _expected_status=404,
    )


def test_download_contact_list(
    mocker,
    logged_in_client,
    fake_uuid,
    mock_get_contact_list,
):
    mocker.patch(
        'app.models.contact_list.s3download',
        return_value='phone number\n07900900321'
    )
    response = logged_in_client.get(url_for(
        'main.download_contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
    ))
    assert response.status_code == 200
    assert response.headers['Content-Type'] == (
        'text/csv; '
        'charset=utf-8'
    )
    assert response.headers['Content-Disposition'] == (
        'attachment; '
        'filename=EmergencyContactList.csv'
    )
    assert response.get_data(as_text=True) == (
        'phone number\n'
        '07900900321'
    )


def test_confirm_delete_contact_list(
    mocker,
    client_request,
    fake_uuid,
    mock_get_jobs,
    mock_get_service_data_retention,
    mock_get_contact_list,
):
    mocker.patch(
        'app.models.contact_list.s3download',
        return_value='phone number\n07900900321'
    )
    page = client_request.get(
        'main.delete_contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
    )
    assert normalize_spaces(page.select_one('.banner-dangerous').text) == (
        'Are you sure you want to delete ‘EmergencyContactList.xls’? '
        'Yes, delete'
    )
    assert 'action' not in page.select_one('form')
    assert page.select_one('form')['method'] == 'post'
    assert page.select_one('form button')['type'] == 'submit'


def test_delete_contact_list(
    mocker,
    client_request,
    fake_uuid,
    mock_get_contact_list,
):
    mock_delete = mocker.patch(
        'app.models.contact_list.contact_list_api_client.delete_contact_list'
    )
    client_request.post(
        'main.delete_contact_list',
        service_id=SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
        _expected_redirect=url_for(
            'main.uploads',
            service_id=SERVICE_ONE_ID,
            _external=True,
        )
    )
    mock_delete.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        contact_list_id=fake_uuid,
    )
