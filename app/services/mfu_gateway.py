from __future__ import annotations

import csv
import re
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import PurePosixPath
from typing import Protocol
from xml.etree import ElementTree

from app.schemas.members import normalize_can_number

TEMPLATE_COLUMNS = (
    "FamilyCode",
    "FamilyHeadName",
    "PrimaryRMEmail",
    "PrimaryRMName",
    "FamilyRemarks",
    "MemberName",
    "CANNumber",
    "PAN",
    "DateOfBirth",
    "KYCStatus",
    "Mobile",
    "MobileStatus",
    "Email",
    "EmailStatus",
    "NomineeStatus",
    "BankName",
    "AccountNumber",
    "IFSC",
    "PayEezzStatus",
    "PayEezzAmount",
    "PayEezzStartDate",
    "Remarks",
)

REQUIRED_TEMPLATE_COLUMNS = frozenset(column for column in TEMPLATE_COLUMNS if column != "FamilyCode")


class TemplateParseError(ValueError):
    pass


@dataclass(frozen=True)
class MfuMemberRecord:
    row_number: int
    raw_data: dict[str, str]


class MfuGateway(Protocol):
    def fetch_members_since(self, timestamp: datetime | None) -> Iterable[MfuMemberRecord]: ...

    def fetch_member_by_can(self, can_number: str) -> MfuMemberRecord | None: ...


class TemplateMfuGateway:
    def __init__(
        self,
        records: Iterable[MfuMemberRecord],
        *,
        headers: Iterable[str],
        warnings: Iterable[str] = (),
    ) -> None:
        self._records = list(records)
        self.headers = list(headers)
        self.warnings = list(warnings)

    @classmethod
    def from_file(cls, file_name: str, content: bytes) -> TemplateMfuGateway:
        headers, records = parse_template_file(file_name, content)
        extra_headers = [header for header in headers if header and header not in TEMPLATE_COLUMNS]
        warnings = []
        if extra_headers:
            warnings.append(f"Extra columns ignored: {', '.join(extra_headers)}")
        return cls(records, headers=headers, warnings=warnings)

    def fetch_members_since(self, timestamp: datetime | None) -> Iterable[MfuMemberRecord]:
        _ = timestamp
        return list(self._records)

    def fetch_member_by_can(self, can_number: str) -> MfuMemberRecord | None:
        normalized_can = normalize_can_number(can_number)
        for record in self._records:
            candidate = record.raw_data.get("CANNumber")
            if candidate and normalize_can_number(candidate) == normalized_can:
                return record
        return None


def parse_template_file(file_name: str, content: bytes) -> tuple[list[str], list[MfuMemberRecord]]:
    lower_name = file_name.lower()
    if lower_name.endswith(".csv"):
        return _parse_csv(content)
    if lower_name.endswith(".xlsx"):
        return _parse_xlsx(content)
    raise TemplateParseError("Only CSV and XLSX MFU template files are supported.")


def _parse_csv(content: bytes) -> tuple[list[str], list[MfuMemberRecord]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise TemplateParseError("CSV file must be UTF-8 encoded.") from exc

    reader = csv.reader(StringIO(text))
    try:
        headers = [_clean_header(cell) for cell in next(reader)]
    except StopIteration:
        return [], []

    records: list[MfuMemberRecord] = []
    for row_number, values in enumerate(reader, start=2):
        if not any(_cell_to_text(value).strip() for value in values):
            continue
        raw_data = {
            header: _cell_to_text(values[index]) if index < len(values) else ""
            for index, header in enumerate(headers)
            if header
        }
        records.append(MfuMemberRecord(row_number=row_number, raw_data=raw_data))
    return headers, records


def _parse_xlsx(content: bytes) -> tuple[list[str], list[MfuMemberRecord]]:
    try:
        workbook = zipfile.ZipFile(BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise TemplateParseError("XLSX file is not a valid workbook.") from exc

    with workbook:
        shared_strings = _read_shared_strings(workbook)
        sheet_path = _first_sheet_path(workbook)
        try:
            sheet_xml = workbook.read(sheet_path)
        except KeyError as exc:
            raise TemplateParseError("XLSX workbook does not contain a readable first sheet.") from exc

    rows = _read_sheet_rows(sheet_xml, shared_strings)
    if not rows:
        return [], []

    header_row_number = min(rows)
    headers = [_clean_header(cell) for cell in rows[header_row_number]]
    records: list[MfuMemberRecord] = []
    for row_number in sorted(row for row in rows if row > header_row_number):
        values = rows[row_number]
        if not any(cell.strip() for cell in values):
            continue
        raw_data = {
            header: values[index] if index < len(values) else "" for index, header in enumerate(headers) if header
        }
        records.append(MfuMemberRecord(row_number=row_number, raw_data=raw_data))
    return headers, records


def _read_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    try:
        xml_bytes = workbook.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ElementTree.fromstring(xml_bytes)
    values: list[str] = []
    for si in root.findall(".//{*}si"):
        values.append("".join(text.text or "" for text in si.findall(".//{*}t")))
    return values


def _first_sheet_path(workbook: zipfile.ZipFile) -> str:
    try:
        workbook_xml = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
        rels_xml = ElementTree.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    except (KeyError, ElementTree.ParseError) as exc:
        raise TemplateParseError("XLSX workbook metadata is missing or invalid.") from exc

    first_sheet = workbook_xml.find(".//{*}sheet")
    if first_sheet is None:
        raise TemplateParseError("XLSX workbook has no sheets.")
    relationship_id = first_sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    if relationship_id is None:
        raise TemplateParseError("XLSX first sheet relationship is missing.")

    targets = {rel.attrib.get("Id"): rel.attrib.get("Target") for rel in rels_xml.findall(".//{*}Relationship")}
    target = targets.get(relationship_id)
    if target is None:
        raise TemplateParseError("XLSX first sheet target is missing.")
    if target.startswith("/"):
        return target.lstrip("/")
    return str(PurePosixPath("xl") / target)


def _read_sheet_rows(sheet_xml: bytes, shared_strings: list[str]) -> dict[int, list[str]]:
    root = ElementTree.fromstring(sheet_xml)
    row_values: dict[int, dict[int, str]] = {}
    max_column = 0
    for row in root.findall(".//{*}sheetData/{*}row"):
        row_number = int(row.attrib.get("r", "0") or "0")
        if row_number <= 0:
            continue
        cells: dict[int, str] = {}
        for cell in row.findall("{*}c"):
            ref = cell.attrib.get("r", "")
            column_index = _column_index(ref)
            if column_index is None:
                continue
            max_column = max(max_column, column_index)
            cells[column_index] = _xlsx_cell_text(cell, shared_strings)
        row_values[row_number] = cells

    return {
        row_number: [cells.get(index, "") for index in range(max_column + 1)]
        for row_number, cells in row_values.items()
    }


def _xlsx_cell_text(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//{*}is/{*}t"))

    value_node = cell.find("{*}v")
    if value_node is None or value_node.text is None:
        return ""
    value = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (IndexError, ValueError):
            return ""
    if cell_type == "b":
        return "TRUE" if value == "1" else "FALSE"
    return _cell_to_text(value)


def _column_index(cell_ref: str) -> int | None:
    match = re.match(r"([A-Z]+)", cell_ref.upper())
    if match is None:
        return None
    value = 0
    for char in match.group(1):
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value - 1


def _cell_to_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def _clean_header(value: object | None) -> str:
    return _cell_to_text(value).strip()
