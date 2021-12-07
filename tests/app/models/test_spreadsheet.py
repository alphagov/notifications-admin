from collections import OrderedDict
from pathlib import Path

import pytest

from app.models.spreadsheet import Spreadsheet


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


@pytest.mark.parametrize('args, kwargs', (
    (
        ('hello', ['hello']),
        {},
    ),
    (
        (),
        {'csv_data': 'hello', 'rows': ['hello']}
    ),
))
def test_spreadsheet_checks_for_bad_arguments(args, kwargs):
    with pytest.raises(TypeError) as exception:
        Spreadsheet(*args, **kwargs)
    assert str(exception.value) == 'Spreadsheet must be created from either rows or CSV data'
