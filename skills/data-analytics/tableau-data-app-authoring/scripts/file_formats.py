"""
description: The data file formats that wire_datasource.py can embed in a data app.
last_updated: 2026-11-22

File formats `wire_datasource.py` can embed. To add one, write a class like
these and list it in `FILE_FORMATS`.
"""

NO_PASSWORD = ""  # nosec B105  # Tableau writes it empty for file connections


def bracket(name):
    return "[" + name.replace("]", "]]") + "]"


class ExcelFile:
    extensions = (".xls", ".xlsx", ".xlsm")
    connection_class = "excel-direct"

    def __init__(self, path, table):
        if not isinstance(table, str) or not table:
            raise ValueError(
                'Excel datasources need "table": the name of the sheet to query.'
            )
        self.path = path
        self.relation_name = table
        self.relation_table = bracket(f"{table}$")

    def connection_attrs(self):
        return {
            "cleaning": "no",
            "compat": "no",
            "dataRefreshTime": "",
            "filename": self.path,
            "interpretationMode": "0",
            "password": NO_PASSWORD,
            "server": "",
            "validate": "no",
        }


class TextFile:
    extensions = (".csv",)
    connection_class = "textscan"

    def __init__(self, path, table):
        if table is not None:
            raise ValueError(
                '"table" applies only to Excel files; a CSV file is its own table.'
            )
        self.directory, self.filename = path.rsplit("/", 1)
        stem, extension = self.filename.rsplit(".", 1)
        self.relation_name = self.filename
        self.relation_table = bracket(f"{stem}#{extension}")

    def connection_attrs(self):
        return {
            "directory": self.directory,
            "filename": self.filename,
            "password": NO_PASSWORD,
            "server": "",
        }


FILE_FORMATS = (ExcelFile, TextFile)

FORMAT_BY_EXTENSION = {
    extension: file_format
    for file_format in FILE_FORMATS
    for extension in file_format.extensions
}
