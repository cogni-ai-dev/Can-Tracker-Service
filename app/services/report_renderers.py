from __future__ import annotations

import csv
import io
import math
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID
from xml.sax.saxutils import escape as xml_escape

from fastapi import status

from app.api.errors import raise_api_error
from app.domain.enums import ReportExportFormat
from app.domain.reports import ReportDefinition
from app.models.user import User

PDF_MAX_ROWS = 500


@dataclass(frozen=True)
class RenderedReport:
    format: ReportExportFormat
    filename: str
    media_type: str
    content: bytes


def _value_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, datetime):
        return (
            value.astimezone(timezone.utc).isoformat()
            if value.tzinfo
            else value.replace(tzinfo=timezone.utc).isoformat()
        )
    if isinstance(value, date | Decimal | UUID):
        return str(value)
    return str(value)


def _row_values(definition: ReportDefinition, row: dict[str, Any]) -> list[str]:
    return [_value_text(row.get(column.key)) for column in definition.columns]


def render_csv(definition: ReportDefinition, rows: list[dict[str, Any]], filename: str) -> RenderedReport:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([column.label for column in definition.columns])
    for row in rows:
        writer.writerow(_row_values(definition, row))
    return RenderedReport(
        format=ReportExportFormat.CSV,
        filename=filename,
        media_type="text/csv; charset=utf-8",
        content=("\ufeff" + output.getvalue()).encode("utf-8"),
    )


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _sheet_name(title: str) -> str:
    safe = "".join(char if char not in '[]:*?/\\"' else " " for char in title).strip()
    return (safe or "Report")[:31]


def _xlsx_cell(reference: str, value: Any, *, style: int | None = None) -> str:
    text = _value_text(value)
    style_attr = f' s="{style}"' if style is not None else ""
    if text == "":
        return f'<c r="{reference}"{style_attr}/>'
    return f'<c r="{reference}" t="inlineStr"{style_attr}><is><t>{xml_escape(text)}</t></is></c>'


def _xlsx_row(row_index: int, values: list[Any], *, header: bool = False) -> str:
    style = 1 if header else None
    cells = "".join(
        _xlsx_cell(f"{_column_name(index)}{row_index}", value, style=style) for index, value in enumerate(values, 1)
    )
    return f'<row r="{row_index}">{cells}</row>'


def render_xlsx(definition: ReportDefinition, rows: list[dict[str, Any]], filename: str) -> RenderedReport:
    table = [[column.label for column in definition.columns], *[_row_values(definition, row) for row in rows]]
    column_widths = []
    for column_index in range(len(definition.columns)):
        max_width = max((len(row[column_index]) for row in table), default=10)
        column_widths.append(min(max(max_width + 2, 10), 40))

    cols_xml = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(column_widths, 1)
    )
    sheet_data = "".join(_xlsx_row(index, row, header=index == 1) for index, row in enumerate(table, 1))
    dimension = f"A1:{_column_name(max(len(definition.columns), 1))}{max(len(table), 1)}"
    worksheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"\n'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n'
        f'  <dimension ref="{dimension}"/>\n'
        '  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" '
        'topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        "</sheetView></sheetViews>\n"
        '  <sheetFormatPr defaultRowHeight="15"/>\n'
        f"  <cols>{cols_xml}</cols>\n"
        f"  <sheetData>{sheet_data}</sheetData>\n"
        "</worksheet>"
    )

    workbook_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="{xml_escape(_sheet_name(definition.title))}" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '  <Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>\n'
        '  <Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>\n'
        "</Relationships>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '  <Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
        'officeDocument" Target="xl/workbook.xml"/>\n'
        '  <Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/'
        'metadata/core-properties" Target="docProps/core.xml"/>\n'
        '  <Relationship Id="rId3" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
        'extended-properties" Target="docProps/app.xml"/>\n'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '  <Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '  <Default Extension="xml" ContentType="application/xml"/>\n'
        '  <Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.'
        'sheet.main+xml"/>\n'
        '  <Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.'
        'worksheet+xml"/>\n'
        '  <Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.'
        'styles+xml"/>\n'
        '  <Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>\n'
        '  <Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>\n'
        "</Types>"
    )
    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n'
        '  <fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>\n'
        '  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>\n'
        '  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>\n'
        '  <cellStyleXfs count="1">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>\n'
        '  <cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" '
        'borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" '
        'borderId="0" xfId="0" applyFont="1"/></cellXfs>\n'
        '  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>\n'
        "</styleSheet>"
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    core_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{xml_escape(definition.title)}</dc:title>
  <dcterms:created xsi:type="dcterms:W3CDTF">{generated_at}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{generated_at}</dcterms:modified>
</cp:coreProperties>"""
    app_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"\n'
        ' xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/'
        'docPropsVTypes"><Application>CAN Tracker Service</Application></Properties>'
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)
        archive.writestr("xl/styles.xml", styles_xml)
        archive.writestr("docProps/core.xml", core_xml)
        archive.writestr("docProps/app.xml", app_xml)

    return RenderedReport(
        format=ReportExportFormat.XLSX,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content=buffer.getvalue(),
    )


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max(max_chars - 1, 0)] + "~"


def _pdf_text_line(x: int, y: int, text: str, *, size: int = 8) -> str:
    return f"BT /F1 {size} Tf {x} {y} Td ({_pdf_escape(text)}) Tj ET"


def _pdf_page_stream(lines: list[tuple[int, int, str, int]]) -> bytes:
    commands = ["q"]
    commands.extend(_pdf_text_line(x, y, text, size=size) for x, y, text, size in lines)
    commands.append("Q")
    return "\n".join(commands).encode("latin-1", errors="replace")


def _paginate_pdf_lines(
    definition: ReportDefinition,
    rows: list[dict[str, Any]],
    generated_at: datetime,
    filters: dict[str, Any],
    actor: User,
) -> list[bytes]:
    headers = [column.label for column in definition.columns]
    table_lines = [" | ".join(headers)]
    for row in rows:
        table_lines.append(" | ".join(_truncate(value, 20) for value in _row_values(definition, row)))

    filter_parts = [f"{key}={value}" for key, value in filters.items() if value is not None]
    metadata_lines = [
        definition.title,
        f"Generated: {generated_at.isoformat()}",
        f"Generated by: {actor.name} <{actor.email}>",
        f"Filters: {', '.join(filter_parts) if filter_parts else 'none'}",
        "",
    ]
    all_lines = metadata_lines + table_lines
    pages: list[bytes] = []
    lines_per_page = 44
    page_count = max(math.ceil(len(all_lines) / lines_per_page), 1)
    for page_index in range(page_count):
        chunk = all_lines[page_index * lines_per_page : (page_index + 1) * lines_per_page]
        positioned: list[tuple[int, int, str, int]] = []
        y = 570
        for line_index, line in enumerate(chunk):
            size = 14 if page_index == 0 and line_index == 0 else 8
            positioned.append((32, y, _truncate(line, 150), size))
            y -= 12 if size == 8 else 18
        positioned.append((720, 20, f"{page_index + 1}/{page_count}", 8))
        pages.append(_pdf_page_stream(positioned))
    return pages


def _build_pdf(objects: list[bytes], *, info_object: bytes) -> bytes:
    all_objects = [*objects, info_object]
    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(all_objects, 1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode("ascii"))
        output.write(body)
        output.write(b"\nendobj\n")
    xref_offset = output.tell()
    output.write(f"xref\n0 {len(all_objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    info_index = len(all_objects)
    output.write(
        f"trailer\n<< /Size {len(all_objects) + 1} /Root 1 0 R /Info {info_index} 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return output.getvalue()


def render_pdf(
    definition: ReportDefinition,
    rows: list[dict[str, Any]],
    filename: str,
    *,
    generated_at: datetime,
    filters: dict[str, Any],
    actor: User,
) -> RenderedReport:
    if len(rows) > PDF_MAX_ROWS:
        raise_api_error(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "pdf_row_limit_exceeded",
            f"PDF exports are limited to {PDF_MAX_ROWS} rows. Use CSV or XLSX for larger reports.",
        )

    page_streams = _paginate_pdf_lines(definition, rows, generated_at, filters, actor)
    page_count = len(page_streams)
    font_object_id = 3 + (page_count * 2)
    objects: list[bytes] = []
    page_ids = [3 + (index * 2) for index in range(page_count)]
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii"))

    stream_object_id = 4
    for stream in page_streams:
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 792 612] "
                f"/Resources << /Font << /F1 {font_object_id} 0 R >> >> "
                f"/Contents {stream_object_id} 0 R >>"
            ).encode("ascii")
        )
        objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
        stream_object_id += 2

    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    info = (
        f"<< /Title ({_pdf_escape(definition.title)}) "
        f"/Producer (CAN Tracker Service) "
        f"/CreationDate (D:{generated_at:%Y%m%d%H%M%S}+00'00') >>"
    ).encode("latin-1", errors="replace")
    return RenderedReport(
        format=ReportExportFormat.PDF,
        filename=filename,
        media_type="application/pdf",
        content=_build_pdf(objects, info_object=info),
    )


def render_report(
    definition: ReportDefinition,
    rows: list[dict[str, Any]],
    export_format: ReportExportFormat,
    *,
    filename: str,
    generated_at: datetime,
    filters: dict[str, Any],
    actor: User,
) -> RenderedReport:
    if export_format == ReportExportFormat.CSV:
        return render_csv(definition, rows, filename)
    if export_format == ReportExportFormat.XLSX:
        return render_xlsx(definition, rows, filename)
    return render_pdf(definition, rows, filename, generated_at=generated_at, filters=filters, actor=actor)
