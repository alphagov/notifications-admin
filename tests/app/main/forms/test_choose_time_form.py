import pytest
from freezegun import freeze_time

from app.main.forms import ChooseTimeForm


@freeze_time("2016-01-01 11:09:00.061258")
def test_form_contains_next_24h(notify_admin):

    choices = ChooseTimeForm().scheduled_for.choices

    # Friday
    assert choices[0] == ("", "Now")
    assert choices[1] == ("2016-01-01T12:00:00", "Today at midday")
    assert choices[13] == ("2016-01-02T00:00:00", "Today at midnight")

    # Saturday
    assert choices[14] == ("2016-01-02T01:00:00", "Tomorrow at 1am")
    assert choices[37] == ("2016-01-03T00:00:00", "Tomorrow at midnight")

    # Sunday
    assert choices[38] == ("2016-01-03T01:00:00", "Sunday at 1am")

    # Monday
    assert choices[84] == ("2016-01-04T23:00:00", "Monday at 11pm")
    assert choices[85] == ("2016-01-05T00:00:00", "Monday at midnight")

    # Tuesday
    assert choices[86] == ("2016-01-05T01:00:00", "Tuesday at 1am")

    # Wednesday
    assert choices[110] == ("2016-01-06T01:00:00", "Wednesday at 1am")

    # Thursday
    assert choices[134] == ("2016-01-07T01:00:00", "Thursday at 1am")
    assert choices[-1] == ("2016-01-08T00:00:00", "Thursday at midnight")

    with pytest.raises(IndexError):
        assert choices[12 + (6 * 24) + 2]  # hours left in the day  # 3 days  # magic number


@freeze_time("2016-01-01 11:09:00.061258")
def test_form_defaults_to_now(notify_admin):
    assert ChooseTimeForm().scheduled_for.data == ""


@freeze_time("2016-01-01 11:09:00.061258")
def test_form_contains_next_three_days(notify_admin):
    assert ChooseTimeForm().scheduled_for.days == [
        "Today",
        "Tomorrow",
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
    ]
