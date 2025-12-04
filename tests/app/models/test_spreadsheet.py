from pathlib import Path

import pytest

from app.models.spreadsheet import Spreadsheet

conversion_original_files = tuple(
    (Path.cwd() / "tests" / "spreadsheet_files" / "conversions" / "originals").glob("[!.]*.*")
)


def test_can_create_spreadsheet_from_large_excel_file():
    with open(str(Path.cwd() / "tests" / "spreadsheet_files" / "equivalents" / "excel 2007.xlsx"), "rb") as xl:
        ret = Spreadsheet.from_file(xl, filename="xl.xlsx")
    assert ret.as_csv_data


@pytest.mark.parametrize(
    "args, kwargs",
    (
        (
            ("hello", ["hello"]),
            {},
        ),
        ((), {"csv_data": "hello", "rows": ["hello"]}),
    ),
)
def test_spreadsheet_checks_for_bad_arguments(args, kwargs):
    with pytest.raises(TypeError) as exception:
        Spreadsheet(*args, **kwargs)
    assert str(exception.value) == "Spreadsheet must be created from either rows or CSV data"


@pytest.mark.parametrize("original_file", conversion_original_files, ids=[p.name for p in conversion_original_files])
def test_conversion(original_file):
    # these are just the "expected" results - we haven't necessarily declared that these are the
    # exact "desired" results. it's more a documentation of the quirks allowing us to be aware of
    # behaviour changes.
    expected_file = original_file.parent / ".." / "expected_converted" / f"{original_file.stem}.csv"

    with original_file.open("rb") as f_orig, expected_file.open("rb") as f_exp:
        # comparison done in binary mode to avoid universal newlines complicating things
        assert Spreadsheet.from_file(f_orig, filename=original_file.name).as_csv_data.encode("utf-8") == f_exp.read()
