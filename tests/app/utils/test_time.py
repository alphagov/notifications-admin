import pytest
from freezegun import freeze_time

from app.utils.time import get_current_financial_year, is_less_than_days_ago


@pytest.mark.parametrize("date_from_db, expected_result", [
    ('2019-11-17T11:35:21.726132Z', True),
    ('2019-11-16T11:35:21.726132Z', False),
    ('2019-11-16T11:35:21+0000', False),
])
@freeze_time('2020-02-14T12:00:00')
def test_is_less_than_days_ago(date_from_db, expected_result):
    assert is_less_than_days_ago(date_from_db, 90) == expected_result


@pytest.mark.parametrize('datetime_string, financial_year', (
    ('2021-01-01T00:00:00+00:00', 2020),  # Start of 2021
    ('2021-03-31T22:59:59+00:00', 2020),  # One minute before midnight (BST)
    ('2021-03-31T23:00:00+00:00', 2021),  # Midnight (BST)
    ('2021-12-12T12:12:12+01:00', 2021),  # Later in the year
))
def test_get_financial_year(datetime_string, financial_year):
    with freeze_time(datetime_string):
        assert get_current_financial_year() == financial_year
