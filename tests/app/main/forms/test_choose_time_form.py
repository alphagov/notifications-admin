import pytest
from freezegun import freeze_time

from app.main.forms import ChooseTimeForm


@freeze_time("2016-01-01 11:09:00.061258")
def test_form_contains_next_7_days_in_hour_intervals(notify_admin):
    choices = ChooseTimeForm().scheduled_for.choices

    # Friday
    assert choices[0] == ("", "Now")
    assert choices[1] == ("2016-01-01T12:00:00", "Today at midday")
    assert choices[13] == ("2016-01-02T00:00:00", "Today at midnight")

    # Saturday
    assert choices[14] == ("2016-01-02T01:00:00", "Tomorrow at 1am")
    assert choices[37] == ("2016-01-03T00:00:00", "Tomorrow at midnight")

    # Sunday
    assert choices[38] == ("2016-01-03T01:00:00", "Sunday 3 January at 1am")

    # Monday
    assert choices[84] == ("2016-01-04T23:00:00", "Monday 4 January at 11pm")
    assert choices[85] == ("2016-01-05T00:00:00", "Monday 4 January at midnight")

    # Tuesday
    assert choices[86] == ("2016-01-05T01:00:00", "Tuesday 5 January at 1am")

    # Wednesday
    assert choices[110] == ("2016-01-06T01:00:00", "Wednesday 6 January at 1am")

    # Thursday
    assert choices[134] == ("2016-01-07T01:00:00", "Thursday 7 January at 1am")
    assert choices[-1] == ("2016-01-08T00:00:00", "Thursday 7 January at midnight")

    with pytest.raises(IndexError):
        assert choices[12 + (6 * 24) + 2]  # hours left in the day  # 3 days  # magic number


@freeze_time("2016-07-01 10:59:00.061258")
def test_form_contains_next_7_days_in_hour_intervals_during_summer_time(notify_admin):
    choices = ChooseTimeForm().scheduled_for.choices

    # Friday
    assert choices[0] == ("", "Now")
    assert choices[1] == ("2016-07-01T11:00:00", "Today at midday")
    assert choices[13] == ("2016-07-01T23:00:00", "Today at midnight")

    # Saturday
    assert choices[14] == ("2016-07-02T00:00:00", "Tomorrow at 1am")
    assert choices[37] == ("2016-07-02T23:00:00", "Tomorrow at midnight")

    # Sunday
    assert choices[38] == ("2016-07-03T00:00:00", "Sunday 3 July at 1am")

    # Monday
    assert choices[84] == ("2016-07-04T22:00:00", "Monday 4 July at 11pm")
    assert choices[85] == ("2016-07-04T23:00:00", "Monday 4 July at midnight")

    # Tuesday
    assert choices[86] == ("2016-07-05T00:00:00", "Tuesday 5 July at 1am")

    # Wednesday
    assert choices[110] == ("2016-07-06T00:00:00", "Wednesday 6 July at 1am")

    # Thursday
    assert choices[134] == ("2016-07-07T00:00:00", "Thursday 7 July at 1am")
    assert choices[-1] == ("2016-07-07T23:00:00", "Thursday 7 July at midnight")

    with pytest.raises(IndexError):
        assert choices[12 + (6 * 24) + 2]  # hours left in the day  # 3 days  # magic number


@freeze_time("2016-01-01 11:09:00.061258")
def test_form_defaults_to_now(notify_admin):
    assert ChooseTimeForm().scheduled_for.data == ""


@freeze_time("2016-01-01 11:09:00.061258")
def test_form_contains_next_7_days(notify_admin):
    assert ChooseTimeForm().scheduled_for.days == [
        "Today",
        "Tomorrow",
        "Sunday 3 January",
        "Monday 4 January",
        "Tuesday 5 January",
        "Wednesday 6 January",
        "Thursday 7 January",
    ]
