from datetime import UTC, datetime
from functools import partial

import pytest
from flask import url_for
from freezegun import freeze_time

from app.formatters import (
    format_datetime_relative,
    format_notification_status_as_url,
    format_pennies_as_currency,
    format_pounds_as_currency,
    message_finished_processing_notification,
    sentence_case,
)


@pytest.mark.parametrize(
    "status, notification_type, expected",
    (
        # Successful statuses aren’t linked
        ("created", "email", lambda: None),
        ("sending", "email", lambda: None),
        ("delivered", "email", lambda: None),
        # Failures are linked to the channel-specific page
        ("temporary-failure", "email", partial(url_for, "main.guidance_message_status", notification_type="email")),
        ("permanent-failure", "email", partial(url_for, "main.guidance_message_status", notification_type="email")),
        ("technical-failure", "email", partial(url_for, "main.guidance_message_status", notification_type="email")),
        ("temporary-failure", "sms", partial(url_for, "main.guidance_message_status", notification_type="sms")),
        ("permanent-failure", "sms", partial(url_for, "main.guidance_message_status", notification_type="sms")),
        ("technical-failure", "sms", partial(url_for, "main.guidance_message_status", notification_type="sms")),
        # Letter statuses are never linked
        ("technical-failure", "letter", lambda: None),
        ("cancelled", "letter", lambda: None),
        ("accepted", "letter", lambda: None),
        ("received", "letter", lambda: None),
    ),
)
def test_format_notification_status_as_url(
    client_request,
    status,
    notification_type,
    expected,
):
    assert format_notification_status_as_url(status, notification_type) == expected()


@pytest.mark.parametrize(
    "input_number, formatted_number",
    [
        (0, "0p"),
        (0.01, "1p"),
        (0.5, "50p"),
        (1, "£1.00"),
        (1.01, "£1.01"),
        (1.006, "£1.01"),
        (5.25, "£5.25"),
        (5.7, "£5.70"),
        (381, "£381.00"),
        (144820, "£144,820.00"),
    ],
)
def test_format_pounds_as_currency(input_number, formatted_number):
    assert format_pounds_as_currency(input_number) == formatted_number


@pytest.mark.parametrize(
    "input_number, long, formatted_number",
    [
        (0, False, "0p"),
        (0, True, "0 pence"),
        (1, False, "1p"),
        (1.97, False, "1.97p"),
        (1.97, True, "1.97 pence"),
        (50, False, "50p"),
        (50, True, "50 pence"),
        (100, False, "£1.00"),
        (100, True, "£1.00"),
        (101, False, "£1.01"),
        (100.6, False, "£1.01"),
        (100.6, True, "£1.01"),
        (525, False, "£5.25"),
        (570, False, "£5.70"),
        (38100, False, "£381.00"),
        (14482000, False, "£144,820.00"),
    ],
)
def test_format_pennies_as_currency(input_number, long, formatted_number):
    assert format_pennies_as_currency(input_number, long=long) == formatted_number


@pytest.mark.parametrize(
    "time, human_readable_datetime",
    [
        ("2018-03-14 09:00", "14 March at 9:00am"),
        ("2018-03-14 15:00", "14 March at 3:00pm"),
        ("2018-03-15 09:00", "15 March at 9:00am"),
        ("2018-03-15 15:00", "15 March at 3:00pm"),
        ("2018-03-19 09:00", "19 March at 9:00am"),
        ("2018-03-19 15:00", "19 March at 3:00pm"),
        ("2018-03-19 23:59", "19 March at 11:59pm"),
        ("2018-03-20 00:00", "19 March at midnight"),  # we specifically refer to 00:00 as belonging to the day before.
        ("2018-03-20 00:01", "yesterday at 12:01am"),
        ("2018-03-20 09:00", "yesterday at 9:00am"),
        ("2018-03-20 15:00", "yesterday at 3:00pm"),
        ("2018-03-20 23:59", "yesterday at 11:59pm"),
        ("2018-03-21 00:00", "yesterday at midnight"),  # we specifically refer to 00:00 as belonging to the day before.
        ("2018-03-21 00:01", "today at 12:01am"),
        ("2018-03-21 09:00", "today at 9:00am"),
        ("2018-03-21 12:00", "today at midday"),
        ("2018-03-21 15:00", "today at 3:00pm"),
        ("2018-03-21 23:59", "today at 11:59pm"),
        ("2018-03-22 00:00", "today at midnight"),  # we specifically refer to 00:00 as belonging to the day before.
        ("2018-03-22 00:01", "tomorrow at 12:01am"),
        ("2018-03-22 09:00", "tomorrow at 9:00am"),
        ("2018-03-22 15:00", "tomorrow at 3:00pm"),
        ("2018-03-22 23:59", "tomorrow at 11:59pm"),
        ("2018-03-23 00:01", "23 March at 12:01am"),
        ("2018-03-23 09:00", "23 March at 9:00am"),
        ("2018-03-23 15:00", "23 March at 3:00pm"),
    ],
)
def test_format_datetime_relative(time, human_readable_datetime):
    with freeze_time("2018-03-21 12:00"):
        assert format_datetime_relative(time) == human_readable_datetime


@pytest.mark.parametrize(
    "sentence, sentence_case_sentence",
    [
        ("", ""),
        ("a", "A"),
        ("foo", "Foo"),
        ("foo bar", "Foo bar"),
        ("Foo bar", "Foo bar"),
        ("FOO BAR", "Foo BAR"),
        ("fOO BAR", "Foo BAR"),
        ("2numeral", "2Numeral"),
        (".punctuation", ".Punctuation"),
        ("üńïçödë wördś", "Üńïçödë wördś"),
        # Only one sentence per string is supported
        ("multiple. sentences in one. string", "Multiple. sentences in one. string"),
        # Naïve around camelcase words
        ("eMail", "Email"),
    ],
)
def test_sentence_case(sentence, sentence_case_sentence):
    assert sentence_case(sentence) == sentence_case_sentence


@freeze_time("2020-01-10 1:0:0")
@pytest.mark.parametrize(
    "processing_started, data_retention_period, expected_message",
    [
        (
            datetime(2020, 1, 4, 1, 0, 0, tzinfo=UTC),
            7,
            "No messages to show",
        ),
        (
            datetime(2020, 1, 2, 1, 0, 0, tzinfo=UTC),
            7,
            "These messages have been deleted because they were sent more than 7 days ago",
        ),
    ],
)
def test_message_finished_processing_notification(processing_started, data_retention_period, expected_message):
    message = message_finished_processing_notification(processing_started, data_retention_period)
    assert message == expected_message
