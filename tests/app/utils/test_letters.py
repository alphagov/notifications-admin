import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time

from app.utils.letters import (
    get_letter_printing_statement,
    get_letter_validation_error,
    printing_today_or_tomorrow,
)


@pytest.mark.parametrize('utc_datetime', [
    '2018-08-01T23:00:00+00:00',
    '2018-08-01T16:29:00+00:00',
    '2018-11-01T00:00:00+00:00',
    '2018-11-01T10:00:00+00:00',
    '2018-11-01T17:29:00+00:00',
])
def test_printing_today_or_tomorrow_returns_today(utc_datetime):
    with freeze_time(utc_datetime):
        assert printing_today_or_tomorrow(utc_datetime) == 'today'


@pytest.mark.parametrize('utc_datetime', [
    '2018-08-01T22:59:00+00:00',
    '2018-08-01T16:30:00+00:00',
    '2018-11-01T17:30:00+00:00',
    '2018-11-01T21:00:00+00:00',
    '2018-11-01T23:59:00+00:00',
])
def test_printing_today_or_tomorrow_returns_tomorrow(utc_datetime):
    with freeze_time(utc_datetime):
        assert printing_today_or_tomorrow(utc_datetime) == 'tomorrow'


@pytest.mark.parametrize('created_at, current_datetime', [
    ('2017-07-07T12:00:00+00:00', '2017-07-07 16:29:00'),  # created today, summer
    ('2017-07-06T23:30:00+00:00', '2017-07-07 16:29:00'),  # created just after midnight, summer
    ('2017-12-12T12:00:00+00:00', '2017-12-12 17:29:00'),  # created today, winter
    ('2017-12-12T21:30:00+00:00', '2017-12-13 17:29:00'),  # created after 5:30 yesterday
    ('2017-03-25T17:31:00+00:00', '2017-03-26 16:29:00'),  # over clock change period on 2017-03-26
])
def test_get_letter_printing_statement_when_letter_prints_today(created_at, current_datetime):
    with freeze_time(current_datetime):
        statement = get_letter_printing_statement('created', created_at)

    assert statement == 'Printing starts today at 5:30pm'


@pytest.mark.parametrize('created_at, current_datetime', [
    ('2017-07-07T16:31:00+00:00', '2017-07-07 22:59:00'),  # created today, summer
    ('2017-12-12T17:31:00+00:00', '2017-12-12 23:59:00'),  # created today, winter
])
def test_get_letter_printing_statement_when_letter_prints_tomorrow(created_at, current_datetime):
    with freeze_time(current_datetime):
        statement = get_letter_printing_statement('created', created_at)

    assert statement == 'Printing starts tomorrow at 5:30pm'


@pytest.mark.parametrize('created_at, print_day', [
    ('2017-07-06T16:29:00+00:00', 'yesterday'),
    ('2017-12-01T00:00:00+00:00', 'on 1 December'),
    ('2017-03-26T12:00:00+00:00', 'on 26 March'),
])
@freeze_time('2017-07-07 12:00:00')
def test_get_letter_printing_statement_for_letter_that_has_been_sent(created_at, print_day):
    statement = get_letter_printing_statement('delivered', created_at)

    assert statement == 'Printed {} at 5:30pm'.format(print_day)


def test_get_letter_validation_error_for_unknown_error():
    assert get_letter_validation_error('Unknown error') == {
        'title': 'Validation failed'
    }


@pytest.mark.parametrize('error_message, invalid_pages, expected_title, expected_content, expected_summary', [
    (
        'letter-not-a4-portrait-oriented',
        [2],
        'Your letter is not A4 portrait size',
        (
            'You need to change the size or orientation of page 2. '
            'Files must meet our letter specification.'
        ),
        (
            'Validation failed because page 2 is not A4 portrait size.'
            'Files must meet our letter specification.'
        ),
    ),
    (
        'letter-not-a4-portrait-oriented',
        [2, 3, 4],
        'Your letter is not A4 portrait size',
        (
            'You need to change the size or orientation of pages 2, 3 and 4. '
            'Files must meet our letter specification.'
        ),
        (
            'Validation failed because pages 2, 3 and 4 are not A4 portrait size.'
            'Files must meet our letter specification.'
        ),
    ),
    (
        'content-outside-printable-area',
        [2],
        'Your content is outside the printable area',
        (
            'You need to edit page 2.'
            'Files must meet our letter specification.'
        ),
        (
            'Validation failed because content is outside the printable area '
            'on page 2.'
            'Files must meet our letter specification.'
        ),
    ),
    (
        'letter-too-long',
        None,
        'Your letter is too long',
        (
            'Letters must be 10 pages or less (5 double-sided sheets of paper). '
            'Your letter is 13 pages long.'
        ),
        (
            'Validation failed because this letter is 13 pages long.'
            'Letters must be 10 pages or less (5 double-sided sheets of paper).'
        ),
    ),
    (
        'unable-to-read-the-file',
        None,
        'There’s a problem with your file',
        (
            'Notify cannot read this PDF.'
            'Save a new copy of your file and try again.'
        ),
        (
            'Validation failed because Notify cannot read this PDF.'
            'Save a new copy of your file and try again.'
        ),
    ),
    (
        'address-is-empty',
        None,
        'The address block is empty',
        (
            'You need to add a recipient address.'
            'Files must meet our letter specification.'
        ),
        (
            'Validation failed because the address block is empty.'
            'Files must meet our letter specification.'
        ),
    ),
    (
        'not-a-real-uk-postcode',
        None,
        'There’s a problem with the address for this letter',
        (
            'The last line of the address must be a real UK postcode.'
        ),
        (
            'Validation failed because the last line of the address is not a real UK postcode.'
        ),
    ),
    (
        'cant-send-international-letters',
        None,
        'There’s a problem with the address for this letter',
        (
            'You do not have permission to send letters to other countries.'
        ),
        (
            'Validation failed because your service cannot send letters to other countries.'
        ),
    ),
    (
        'not-a-real-uk-postcode-or-country',
        None,
        'There’s a problem with the address for this letter',
        (
            'The last line of the address must be a UK postcode or '
            'another country.'
        ),
        (
            'Validation failed because the last line of the address is '
            'not a UK postcode or another country.'
        ),
    ),
    (
        'not-enough-address-lines',
        None,
        'There’s a problem with the address for this letter',
        (
            'The address must be at least 3 lines long.'
        ),
        (
            'Validation failed because the address must be at least 3 lines long.'
        ),
    ),
    (
        'too-many-address-lines',
        None,
        'There’s a problem with the address for this letter',
        (
            'The address must be no more than 7 lines long.'
        ),
        (
            'Validation failed because the address must be no more than 7 lines long.'
        ),
    ),
    (
        'invalid-char-in-address',
        None,
        'There’s a problem with the address for this letter',
        (
            'Address lines must not start with any of the following characters: @ ( ) = [ ] ” \\ / , < > ~'
        ),
        (
            'Validation failed because address lines must not start with any of the following '
            'characters: @ ( ) = [ ] ” \\ / , < > ~'
        ),
    ),
])
def test_get_letter_validation_error_for_known_errors(
    client_request,
    error_message,
    invalid_pages,
    expected_title,
    expected_content,
    expected_summary,
):
    error = get_letter_validation_error(error_message, invalid_pages=invalid_pages, page_count=13)
    detail = BeautifulSoup(error['detail'], 'html.parser')
    summary = BeautifulSoup(error['summary'], 'html.parser')

    assert error['title'] == expected_title

    assert detail.text == expected_content
    if detail.select_one('a'):
        assert detail.select_one('a')['href'] == url_for('.letter_specification')

    assert summary.text == expected_summary
    if summary.select_one('a'):
        assert summary.select_one('a')['href'] == url_for('.letter_specification')
