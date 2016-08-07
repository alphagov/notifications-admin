import pytest

from app.main.forms import ChooseTimeForm
from freezegun import freeze_time


@freeze_time("2016-01-01 11:09:00.061258")
def test_form_contains_next_24h(app_):

    choices = ChooseTimeForm().scheduled_for.choices

    assert choices[0] == ('', 'Now')
    assert choices[1] == ('2016-01-01T12:00:00.061258', 'Midday')
    assert choices[23] == ('2016-01-02T10:00:00.061258', '10am')

    with pytest.raises(IndexError):
        assert choices[24]


@freeze_time("2016-01-01 11:09:00.061258")
def test_form_defaults_to_now(app_):
    assert ChooseTimeForm().scheduled_for.data == ''
