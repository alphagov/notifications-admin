from pathlib import Path
from unittest.mock import call

import pytest
from notifications_utils.interruptible_io import InterruptibleIOZipFile

from app.models.spreadsheet import Spreadsheet

conversion_original_files = tuple(
    (Path.cwd() / "tests" / "spreadsheet_files" / "conversions" / "originals").glob("[!.]*.*")
)


def test_can_create_spreadsheet_from_large_excel_file():
    with (Path.cwd() / "tests" / "spreadsheet_files" / "equivalents" / "excel 2007.xlsx").open("rb") as xl:
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


def test_openpyxl_zipfile_monkeypatch(mocker):
    open_method_mock = mocker.patch.object(
        InterruptibleIOZipFile, "open", autospec=True, wraps=InterruptibleIOZipFile.open
    )
    with (Path.cwd() / "tests" / "spreadsheet_files" / "equivalents" / "excel 2007.xlsx").open("rb") as xl:
        assert Spreadsheet.from_file(xl, filename=xl.name).as_csv_data

    assert mocker.call(mocker.ANY, "xl/worksheets/sheet1.xml") in open_method_mock.mock_calls


@pytest.mark.parametrize(
    "csv_data, too_many_email_addresses",
    (
        (
            # More than 5 email addresses in one column
            """
            name, email address
            Anne, anne+1@example.com
            Anne, anne+2@example.com
            Not an email address, foo
            Anne, anne+3@example.com

            Anne, anne+4@example.com
            Anne, anne+5@example.com
            Anne, anne+6@example.com
            Not an email address, foo
            """,
            True,
        ),
        (
            # Only 5 email addresses in one column
            """
            Anne, anne+1@example.com
            Anne, anne+2@example.com
            Anne, anne+3@example.com
            Anne, anne+4@example.com
            Anne, anne+5@example.com
            anne+6@example.com, Anne
            """,
            False,
        ),
        (
            # More than 5 email addresses but across multiple columns
            """
            1@gov.uk, 2@gov.uk, 3@gov.uk, 4@gov.uk, 5@gov.uk, 6@gov.uk
            """,
            False,
        ),
        (
            # Lots of email addresses just inside the first 100 rows
            ("foo\n" * 94) + ("anne@example.com\n" * 6),
            True,
        ),
        (
            # Lots of email addresses but only 5 in the first 100 rows
            ("foo\n" * 95) + ("anne@example.com\n" * 10),
            False,
        ),
    ),
)
def test_lots_of_email_addresses(csv_data, too_many_email_addresses):
    assert Spreadsheet(csv_data=csv_data).contains_many_email_addresses() is too_many_email_addresses


def test_spreadsheet_contains_many_email_addresses_is_efficient(mocker):
    mock_validate_email_address = mocker.patch(
        "app.models.spreadsheet.validate_email_address",
        return_value="anything@example.com",
    )
    csv_data = "Foo, Bar, Baz\n" * 6

    assert Spreadsheet(csv_data).contains_many_email_addresses() is True
    assert mock_validate_email_address.call_args_list == [
        # One call with the value from the first column, subsenquent calls with the same value are cached
        call("Foo"),
        # No calls from the second or third columns because we found enough email addresses in the first
    ]
