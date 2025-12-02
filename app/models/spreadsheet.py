import csv
from io import StringIO
from os import path
from time import sleep
from typing import Final, Literal, Self

from pyexcel_io.io import load_data as pyexcel_load_data


class Spreadsheet:
    class TooManyColumnsError(ValueError):
        pass

    class TooManyRowsError(ValueError):
        pass

    AS_CSV_YIELD_LOOP_EVERY: int = 128
    ALLOWED_FILE_EXTENSIONS = ("csv", "xlsx", "xls", "ods", "xlsm", "tsv")

    # a sentinel for use as a kwarg default to avoid early-binding issues that inhibit mocking
    DEFAULT_ARG: Final[object] = object()

    FROM_FILE_ROW_LIMIT_DEFAULT_ARG: int | None = 200_000
    COLUMN_LIMIT_FROM_HEADER_DEFAULT_ARG: bool = True
    ABSOLUTE_COLUMN_LIMIT_DEFAULT_ARG: int = 1_000
    MIN_COLUMN_LIMIT_DEFAULT_ARG: int = 50

    def __init__(self, csv_data=None, rows=None, filename="", row_limit: int | None = None):
        self.filename = filename

        if csv_data and rows:
            raise TypeError("Spreadsheet must be created from either rows or CSV data")

        self._csv_data = csv_data or ""
        self._rows = rows or []
        self._row_limit = row_limit

    @property
    def as_dict(self):
        return {"file_name": self.filename, "data": self.as_csv_data}

    @property
    def as_csv_data(self) -> str:
        if not self._csv_data:
            with StringIO() as converted:
                output = csv.writer(converted)
                for i, row in enumerate(self._rows):
                    if self._row_limit is not None and i > self._row_limit:
                        raise self.TooManyRowsError(f"Exceeded row limit of {self._row_limit}")

                    if not (i + 1) % self.AS_CSV_YIELD_LOOP_EVERY:
                        # all green thread libraries will monkeypatch this to yield to the event loop
                        # and the real implementation should at least drop the GIL
                        sleep(0)

                    output.writerow(row)
                self._csv_data = converted.getvalue()
        return self._csv_data

    @classmethod
    def can_handle(cls, filename):
        return cls.get_extension(filename) in cls.ALLOWED_FILE_EXTENSIONS

    @staticmethod
    def get_extension(filename):
        return path.splitext(filename)[1].lower().lstrip(".")

    @staticmethod
    def normalise_newlines(file_content):
        return "\r\n".join(file_content.read().decode("utf-8").splitlines())

    @classmethod
    def from_rows(cls, rows, filename="", row_limit: int | None = None) -> Self:
        return cls(rows=rows, filename=filename, row_limit=row_limit)

    @classmethod
    def from_dict(cls, dictionary, filename="", row_limit: int | None = None) -> Self:
        return cls.from_rows(
            zip(*sorted(dictionary.items(), key=lambda pair: pair[0]), strict=True),
            filename=filename,
            row_limit=row_limit,
        )

    @classmethod
    def from_file(
        cls,
        file_content,
        filename="",
        row_limit: int | None | Literal[DEFAULT_ARG] = DEFAULT_ARG,
        column_limit_from_header: bool | Literal[DEFAULT_ARG] = DEFAULT_ARG,
        absolute_column_limit: int | Literal[DEFAULT_ARG] = DEFAULT_ARG,
        min_column_limit: int | Literal[DEFAULT_ARG] = DEFAULT_ARG,
    ) -> Self:
        if row_limit is cls.DEFAULT_ARG:
            row_limit = cls.FROM_FILE_ROW_LIMIT_DEFAULT_ARG
        if column_limit_from_header is cls.DEFAULT_ARG:
            column_limit_from_header = cls.COLUMN_LIMIT_FROM_HEADER_DEFAULT_ARG
        if absolute_column_limit is cls.DEFAULT_ARG:
            absolute_column_limit = cls.ABSOLUTE_COLUMN_LIMIT_DEFAULT_ARG
        if min_column_limit is cls.DEFAULT_ARG:
            min_column_limit = cls.MIN_COLUMN_LIMIT_DEFAULT_ARG

        extension = cls.get_extension(filename)

        if extension == "csv":
            return cls(csv_data=Spreadsheet.normalise_newlines(file_content), filename=filename, row_limit=row_limit)

        if extension == "tsv":
            file_content = StringIO(Spreadsheet.normalise_newlines(file_content))

        # why not just use pyexcel.iget_array? this allows us to reuse the same reader
        # from the initial header read for the data reading, which should save some
        # startup cost
        row_iter_dict, reader = pyexcel_load_data(
            file_stream=file_content,
            file_type=extension,
            streaming=True,
            row_limit=(1 if column_limit_from_header else -1),
        )
        row_iter = next(iter(row_iter_dict.values()), iter(()))

        if column_limit_from_header:
            original_offset = file_content.tell()
            last_nonempty_column = next(
                (i for i, x in reversed(tuple(enumerate(next(row_iter, ())))) if str(x).strip()), None
            )

            # some plugins just read things directly from the file each time, so we need to reset
            # the offset for them to have them read from the beginning again
            file_content.seek(original_offset)

            if last_nonempty_column is not None:
                if last_nonempty_column >= absolute_column_limit:
                    raise cls.TooManyColumnsError(
                        f"Last non-empty header column ({last_nonempty_column}) "
                        f"is beyond absolute limit of {absolute_column_limit}"
                    )

                reader.keywords["column_limit"] = max(last_nonempty_column + 1, min_column_limit)
                reader.keywords["row_limit"] = -1
                row_iter = next(iter(reader.read_sheet_by_index(0).values()))

        return cls.from_rows(row_iter, filename, row_limit=row_limit)

    @classmethod
    def from_file_form(
        cls,
        form,
        row_limit: int | Literal[DEFAULT_ARG] = DEFAULT_ARG,
        column_limit_from_header: bool | Literal[DEFAULT_ARG] = DEFAULT_ARG,
        absolute_column_limit: int | Literal[DEFAULT_ARG] = DEFAULT_ARG,
        min_column_limit: int | Literal[DEFAULT_ARG] = DEFAULT_ARG,
    ) -> Self:
        return cls.from_file(
            form.file.data,
            filename=form.file.data.filename,
            row_limit=row_limit,
            column_limit_from_header=column_limit_from_header,
            absolute_column_limit=absolute_column_limit,
            min_column_limit=min_column_limit,
        )
