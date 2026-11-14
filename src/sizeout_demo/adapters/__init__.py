"""Adapters: the file formats and the files themselves."""

from sizeout_demo.adapters.csv_reflections import CsvReflectionReader
from sizeout_demo.adapters.csv_table import CsvResultTable
from sizeout_demo.adapters.files import FileTextStore
from sizeout_demo.adapters.text_report import PlainTextReport

__all__ = ["CsvReflectionReader", "CsvResultTable", "FileTextStore", "PlainTextReport"]
