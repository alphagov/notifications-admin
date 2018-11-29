from collections import OrderedDict
from csv import DictReader
from io import StringIO
from pathlib import Path

import pytest
from freezegun import freeze_time
from notifications_utils.recipients import validate_email_address

from app import format_datetime_relative
from app.utils import (
    AgreementInfo,
    GovernmentEmailDomain,
    Spreadsheet,
    email_safe,
    generate_next_dict,
    generate_notifications_csv,
    generate_previous_dict,
    get_logo_cdn_domain,
)
from tests.conftest import fake_uuid


def _get_notifications_csv(
    row_number=1,
    recipient='foo@bar.com',
    template_name='foo',
    template_type='sms',
    job_name='bar.csv',
    status='Delivered',
    created_at='Thursday 19 April at 12:00',
    rows=1,
    with_links=False,
    job_id=fake_uuid,
    created_by_name=None,
):

    def _get(
        service_id,
        page=1,
        job_id=None,
        template_type=template_type,
    ):
        links = {}
        if with_links:
            links = {
                'prev': '/service/{}/notifications?page=0'.format(service_id),
                'next': '/service/{}/notifications?page=1'.format(service_id),
                'last': '/service/{}/notifications?page=2'.format(service_id)
            }

        data = {
            'notifications': [{
                "row_number": row_number + i,
                "to": recipient,
                "recipient": recipient,
                "template_name": template_name,
                "template_type": template_type,
                "template": {"name": template_name, "template_type": template_type},
                "job_name": job_name,
                "status": status,
                "created_at": created_at,
                "updated_at": None,
                "created_by_name": created_by_name,
            } for i in range(rows)],
            'total': rows,
            'page_size': 50,
            'links': links
        }

        return data

    return _get


@pytest.fixture(scope='function')
def _get_notifications_csv_mock(
    mocker,
    api_user_active,
    job_id=fake_uuid
):
    return mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=_get_notifications_csv()
    )


@pytest.mark.parametrize('service_name, safe_email', [
    ('name with spaces', 'name.with.spaces'),
    ('singleword', 'singleword'),
    ('UPPER CASE', 'upper.case'),
    ('Service - with dash', 'service.with.dash'),
    ('lots      of spaces', 'lots.of.spaces'),
    ('name.with.dots', 'name.with.dots'),
    ('name-with-other-delimiters', 'namewithotherdelimiters'),
    ('.leading', 'leading'),
    ('trailing.', 'trailing'),
    ('üńïçödë wördś', 'unicode.words'),
])
def test_email_safe_return_dot_separated_email_domain(service_name, safe_email):
    assert email_safe(service_name) == safe_email


def test_generate_previous_dict(client):
    ret = generate_previous_dict('main.view_jobs', 'foo', 2, {})
    assert 'page=1' in ret['url']
    assert ret['title'] == 'Previous page'
    assert ret['label'] == 'page 1'


def test_generate_next_dict(client):
    ret = generate_next_dict('main.view_jobs', 'foo', 2, {})
    assert 'page=3' in ret['url']
    assert ret['title'] == 'Next page'
    assert ret['label'] == 'page 3'


def test_generate_previous_next_dict_adds_other_url_args(client):
    ret = generate_next_dict('main.view_notifications', 'foo', 2, {'message_type': 'blah'})
    assert 'notifications/blah' in ret['url']


def test_can_create_spreadsheet_from_large_excel_file():
    with open(str(Path.cwd() / 'tests' / 'spreadsheet_files' / 'excel 2007.xlsx'), 'rb') as xl:
        ret = Spreadsheet.from_file(xl, filename='xl.xlsx')
    assert ret.as_csv_data


def test_can_create_spreadsheet_from_dict():
    assert Spreadsheet.from_dict(OrderedDict(
        foo='bar',
        name='Jane',
    )).as_csv_data == (
        "foo,name\r\n"
        "bar,Jane\r\n"
    )


def test_can_create_spreadsheet_from_dict_with_filename():
    assert Spreadsheet.from_dict({}, filename='empty.csv').as_dict['file_name'] == "empty.csv"


@pytest.mark.parametrize('created_by_name, expected_content', [
    (
        None, [
            'Recipient,Template,Type,Sent by,Job,Status,Time\n',
            'foo@bar.com,foo,sms,,,Delivered,Thursday 19 April at 12:00\r\n',
        ]
    ),
    (
        'Anne Example', [
            'Recipient,Template,Type,Sent by,Job,Status,Time\n',
            'foo@bar.com,foo,sms,Anne Example,,Delivered,Thursday 19 April at 12:00\r\n',
        ]
    ),
])
def test_generate_notifications_csv_without_job(
    app_,
    mocker,
    created_by_name,
    expected_content,
):
    mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=_get_notifications_csv(
            created_by_name=created_by_name,
            job_id=None,
            job_name=None,
        )
    )
    assert list(generate_notifications_csv(service_id=fake_uuid)) == expected_content


@pytest.mark.parametrize('original_file_contents, expected_column_headers, expected_1st_row', [
    (
        """
            phone_number
            07700900123
        """,
        ['Row number', 'phone_number', 'Template', 'Type', 'Job', 'Status', 'Time'],
        ['1', '07700900123', 'foo', 'sms', 'bar.csv', 'Delivered', 'Thursday 19 April at 12:00'],
    ),
    (
        """
            phone_number, a, b, c
            07700900123,  🐜,🐝,🦀
        """,
        ['Row number', 'phone_number', 'a', 'b', 'c', 'Template', 'Type', 'Job', 'Status', 'Time'],
        ['1', '07700900123', '🐜', '🐝', '🦀', 'foo', 'sms', 'bar.csv', 'Delivered', 'Thursday 19 April at 12:00'],
    ),
    (
        """
            "phone_number", "a", "b", "c"
            "07700900123","🐜,🐜","🐝,🐝","🦀"
        """,
        ['Row number', 'phone_number', 'a', 'b', 'c', 'Template', 'Type', 'Job', 'Status', 'Time'],
        ['1', '07700900123', '🐜,🐜', '🐝,🐝', '🦀', 'foo', 'sms', 'bar.csv', 'Delivered', 'Thursday 19 April at 12:00'],
    ),
])
def test_generate_notifications_csv_returns_correct_csv_file(
    app_,
    mocker,
    _get_notifications_csv_mock,
    original_file_contents,
    expected_column_headers,
    expected_1st_row,
):
    mocker.patch(
        'app.main.s3_client.s3download',
        return_value=original_file_contents,
    )
    csv_content = generate_notifications_csv(service_id='1234', job_id=fake_uuid, template_type='sms')
    csv_file = DictReader(StringIO('\n'.join(csv_content)))
    assert csv_file.fieldnames == expected_column_headers
    assert next(csv_file) == dict(zip(expected_column_headers, expected_1st_row))


def test_generate_notifications_csv_only_calls_once_if_no_next_link(
    app_,
    _get_notifications_csv_mock,
):
    list(generate_notifications_csv(service_id='1234'))

    assert _get_notifications_csv_mock.call_count == 1


@pytest.mark.parametrize("job_id", ["some", None])
def test_generate_notifications_csv_calls_twice_if_next_link(
    app_,
    mocker,
    job_id,
):

    mocker.patch(
        'app.main.s3_client.s3download',
        return_value="""
            phone_number
            07700900000
            07700900001
            07700900002
            07700900003
            07700900004
            07700900005
            07700900006
            07700900007
            07700900008
            07700900009
        """
    )

    service_id = '1234'
    response_with_links = _get_notifications_csv(rows=7, with_links=True)
    response_with_no_links = _get_notifications_csv(rows=3, row_number=8, with_links=False)

    mock_get_notifications = mocker.patch(
        'app.notification_api_client.get_notifications_for_service',
        side_effect=[
            response_with_links(service_id),
            response_with_no_links(service_id),
        ]
    )

    csv_content = generate_notifications_csv(
        service_id=service_id,
        job_id=job_id or fake_uuid,
        template_type='sms',
    )
    csv = list(DictReader(StringIO('\n'.join(csv_content))))

    assert len(csv) == 10
    assert csv[0]['phone_number'] == '07700900000'
    assert csv[9]['phone_number'] == '07700900009'
    assert mock_get_notifications.call_count == 2
    # mock_calls[0][2] is the kwargs from first call
    assert mock_get_notifications.mock_calls[0][2]['page'] == 1
    assert mock_get_notifications.mock_calls[1][2]['page'] == 2


def test_get_cdn_domain_on_localhost(client, mocker):
    mocker.patch.dict('app.current_app.config', values={'ADMIN_BASE_URL': 'http://localhost:6012'})
    domain = get_logo_cdn_domain()
    assert domain == 'static-logos.notify.tools'


def test_get_cdn_domain_on_non_localhost(client, mocker):
    mocker.patch.dict('app.current_app.config', values={'ADMIN_BASE_URL': 'https://some.admintest.com'})
    domain = get_logo_cdn_domain()
    assert domain == 'static-logos.admintest.com'


@pytest.mark.parametrize("domain_or_email_address", (
    "test@dclgdatamart.co.uk", "test@communities.gsi.gov.uk", "test@communities.gov.uk",
))
def test_get_valid_agreement_info_known_details(domain_or_email_address):
    agreement_info = AgreementInfo(domain_or_email_address)
    assert agreement_info.crown_status is None
    assert agreement_info.owner == "Ministry of Housing, Communities & Local Government"
    assert agreement_info.agreement_signed is True
    assert agreement_info.as_human_readable == (
        'Yes, on behalf of Ministry of Housing, Communities & Local Government'
    )


@pytest.mark.parametrize("domain_or_email_address, is_canonical", (
    ("test@dclgdatamart.co.uk", False),
    ("test@communities.gsi.gov.uk", False),
    ("test@communities.gov.uk", True),
))
def test_get_canonical_domain(domain_or_email_address, is_canonical):
    assert AgreementInfo(domain_or_email_address).canonical_domain == 'communities.gov.uk'
    assert AgreementInfo(domain_or_email_address).is_canonical == is_canonical


def test_get_canonical_domain_passes_through_unknown_domain():
    assert AgreementInfo('example.com').canonical_domain is None
    assert AgreementInfo('example.com').is_canonical is False


@pytest.mark.parametrize("domain_or_email_address", (
    "test@police.gov.uk", "police.gov.uk",
))
def test_get_valid_agreement_info_unknown_details(domain_or_email_address):
    government_domain = AgreementInfo(domain_or_email_address)
    assert government_domain.crown_status is None
    assert government_domain.owner is None
    assert government_domain.agreement_signed is None
    assert government_domain.as_human_readable == 'Can’t tell (domain is police.gov.uk)'


def test_get_valid_agreement_info_only_org_known():
    agreement_info = AgreementInfo('nhs.net')
    # Some parts of the NHS are Crown, some aren’t
    assert agreement_info.crown_status is None
    assert agreement_info.owner == 'NHS'
    assert agreement_info.agreement_signed is None
    assert agreement_info.as_human_readable == 'Can’t tell (organisation is NHS, crown status unknown)'


def test_get_valid_agreement_info_some_known_details():
    agreement_info = AgreementInfo("marinemanagement.org.uk")
    assert agreement_info.crown_status is None
    assert agreement_info.owner == "Marine Management Organisation"
    assert agreement_info.agreement_signed is True
    assert agreement_info.as_human_readable == (
        'Yes, on behalf of Marine Management Organisation'
    )


def test_get_valid_local_agreement_info_some_known_details():
    agreement_info = AgreementInfo("aberdeenshire.gov.uk")
    assert agreement_info.crown_status is False
    assert agreement_info.owner == "Aberdeenshire Council"
    assert agreement_info.agreement_signed is False
    assert agreement_info.as_human_readable == (
        'No (organisation is Aberdeenshire Council, a non-crown body)'
    )


def test_get_valid_government_domain_gets_most_specific_first():

    generic = AgreementInfo("gov.uk")
    assert generic.crown_status is None
    assert generic.owner is None
    assert generic.agreement_signed is None
    assert generic.as_human_readable == (
        'Can’t tell (domain is gov.uk)'
    )

    specific = AgreementInfo("dacorum.gov.uk")
    assert specific.crown_status is False
    assert specific.owner == 'Dacorum Borough Council'
    assert specific.agreement_signed is True
    assert specific.as_human_readable == (
        'Yes, on behalf of Dacorum Borough Council'
    )


def test_get_domain_info_for_branding_request():

    assert AgreementInfo("gov.uk").as_info_for_branding_request == (
        'Can’t tell (domain is gov.uk)'
    )
    assert AgreementInfo("dacorum.gov.uk").as_info_for_branding_request == (
        'Dacorum Borough Council'
    )


def test_validate_government_domain_data():

    for domain in AgreementInfo.domains.keys():

        validate_email_address('test@{}'.format(domain))

        agreement_info = AgreementInfo(domain)

        assert agreement_info.crown_status in {
            True, False, None
        }

        assert (
            agreement_info.owner is None
        ) or (
            isinstance(agreement_info.owner, str)
        )

        assert agreement_info.agreement_signed in {
            True, False, None
        }


def test_validate_email_domain_data():

    for domain in GovernmentEmailDomain.domains.keys():
        validate_email_address('test@{}'.format(domain))


@pytest.mark.parametrize('time, human_readable_datetime', [
    ('2018-03-14 09:00', '14 March at 9:00am'),
    ('2018-03-14 15:00', '14 March at 3:00pm'),

    ('2018-03-15 09:00', '15 March at 9:00am'),
    ('2018-03-15 15:00', '15 March at 3:00pm'),

    ('2018-03-19 09:00', '19 March at 9:00am'),
    ('2018-03-19 15:00', '19 March at 3:00pm'),
    ('2018-03-19 23:59', '19 March at 11:59pm'),

    ('2018-03-20 00:00', '19 March at midnight'),  # we specifically refer to 00:00 as belonging to the day before.
    ('2018-03-20 00:01', 'yesterday at 12:01am'),
    ('2018-03-20 09:00', 'yesterday at 9:00am'),
    ('2018-03-20 15:00', 'yesterday at 3:00pm'),
    ('2018-03-20 23:59', 'yesterday at 11:59pm'),

    ('2018-03-21 00:00', 'yesterday at midnight'),  # we specifically refer to 00:00 as belonging to the day before.
    ('2018-03-21 00:01', 'today at 12:01am'),
    ('2018-03-21 09:00', 'today at 9:00am'),
    ('2018-03-21 12:00', 'today at midday'),
    ('2018-03-21 15:00', 'today at 3:00pm'),
    ('2018-03-21 23:59', 'today at 11:59pm'),

    ('2018-03-22 00:00', 'today at midnight'),  # we specifically refer to 00:00 as belonging to the day before.
    ('2018-03-22 00:01', 'tomorrow at 12:01am'),
    ('2018-03-22 09:00', 'tomorrow at 9:00am'),
    ('2018-03-22 15:00', 'tomorrow at 3:00pm'),
    ('2018-03-22 23:59', 'tomorrow at 11:59pm'),

    ('2018-03-23 00:01', '23 March at 12:01am'),
    ('2018-03-23 09:00', '23 March at 9:00am'),
    ('2018-03-23 15:00', '23 March at 3:00pm'),

])
def test_format_datetime_relative(time, human_readable_datetime):
    with freeze_time('2018-03-21 12:00'):
        assert format_datetime_relative(time) == human_readable_datetime
