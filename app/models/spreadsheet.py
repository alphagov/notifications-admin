import csv
from io import StringIO
from os import path

import pyexcel
import pyexcel_xlsx


class Spreadsheet():

    ALLOWED_FILE_EXTENSIONS = ('csv', 'xlsx', 'xls', 'ods', 'xlsm', 'tsv')

    def __init__(self, csv_data=None, rows=None, filename=''):

        self.filename = filename

        if csv_data and rows:
            raise TypeError('Spreadsheet must be created from either rows or CSV data')

        self._csv_data = csv_data or ''
        self._rows = rows or []

    @property
    def as_dict(self):
        return {
            'file_name': self.filename,
            'data': self.as_csv_data
        }

    @property
    def as_csv_data(self):
        if not self._csv_data:
            with StringIO() as converted:
                output = csv.writer(converted)
                for row in self._rows:
                    output.writerow(row)
                self._csv_data = converted.getvalue()
        return self._csv_data

    @classmethod
    def can_handle(cls, filename):
        return cls.get_extension(filename) in cls.ALLOWED_FILE_EXTENSIONS

    @staticmethod
    def get_extension(filename):
        return path.splitext(filename)[1].lower().lstrip('.')

    @staticmethod
    def normalise_newlines(file_content):
        return '\r\n'.join(file_content.read().decode('utf-8').splitlines())

    @classmethod
    def from_rows(cls, rows, filename=''):
        return cls(rows=rows, filename=filename)

    @classmethod
    def from_dict(cls, dictionary, filename=''):
        return cls.from_rows(
            zip(
                *sorted(dictionary.items(), key=lambda pair: pair[0])
            ),
            filename=filename,
        )

    @classmethod
    def from_file(cls, file_content, filename=''):
        extension = cls.get_extension(filename)

        if extension == 'csv':
            return cls(csv_data=Spreadsheet.normalise_newlines(file_content), filename=filename)

        if extension == 'tsv':
            file_content = StringIO(
                Spreadsheet.normalise_newlines(file_content))

        if extension == 'xlsm':
            file_data = pyexcel_xlsx.get_data(file_content)
            instance = cls.from_rows(
                # Get the first sheet from the workbook
                list(file_data.values())[0],
                filename,
            )
            return instance

        instance = cls.from_rows(
            pyexcel.iget_array(
                file_type=extension,
                file_stream=file_content),
            filename)
        pyexcel.free_resources()
        return instance

    @classmethod
    def from_file_form(cls, form):
        return cls.from_file(
            form.file.data,
            filename=form.file.data.filename,
        )
