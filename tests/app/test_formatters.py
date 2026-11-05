from datetime import UTC, datetime

import pytest
from freezegun import freeze_time

from app.formatters import format_delta_as_html_duration, insert_wbr, message_count_label, sentence_case


def test_sentence_case():
    assert sentence_case("domain 1 cannot contain @") == "Domain 1 cannot contain @"
    assert (
        sentence_case("mobile number 2 does not look like a UK mobile number")
        == "Mobile number 2 does not look like a UK mobile number"
    )


def test_message_count_label_for_unsubscribe_requests():
    assert message_count_label(count=1, message_type="unsubscribe request", suffix="") == "unsubscribe request"
    assert message_count_label(count=2, message_type="unsubscribe request", suffix="") == "unsubscribe requests"
    assert message_count_label(count=1, message_type="request", suffix="") == "request"
    assert message_count_label(count=2, message_type="request", suffix="") == "requests"


def test_insert_wbr():
    assert insert_wbr("1,352,456") == "1,<wbr />352,<wbr />456"


@pytest.mark.parametrize(
    "date, expected_duration",
    (
        (datetime(2030, 3, 30, tzinfo=UTC), "527w 2d"),
        (datetime(2010, 2, 20, 2, 2, 2, tzinfo=UTC), "521w 4d 21h 57m 58s"),
        (datetime(2010, 10, 10, tzinfo=UTC), "488w 4d"),
    ),
)
@freeze_time("2020-02-20")
def test_format_delta_as_html_duration(date, expected_duration):
    assert format_delta_as_html_duration(date) == expected_duration
