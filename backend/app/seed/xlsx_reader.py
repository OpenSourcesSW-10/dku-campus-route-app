from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET


MAIN_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def read_first_sheet(path: Path) -> list[dict[str, str]]:
    # openpyxl 없이 xlsx 첫 번째 시트를 dict row 목록으로 읽기.
    with ZipFile(path) as workbook:
        shared_strings = _read_shared_strings(workbook)
        sheet_path = _first_sheet_path(workbook)
        rows = _read_rows(workbook, sheet_path, shared_strings)

    header_index = _find_header_index(rows)
    if header_index is None:
        return []

    headers = [_normalize_header(value) for value in rows[header_index]]
    records = []
    for row in rows[header_index + 1 :]:
        record = {}
        for index, header in enumerate(headers):
            if not header:
                continue
            record[header] = row[index].strip() if index < len(row) else ""
        if any(record.values()):
            records.append(record)
    return records


def _read_shared_strings(workbook: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join(text.text or "" for text in item.findall(".//main:t", MAIN_NS))
        for item in root.findall("main:si", MAIN_NS)
    ]


def _first_sheet_path(workbook: ZipFile) -> str:
    workbook_root = ET.fromstring(workbook.read("xl/workbook.xml"))
    rels_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_root}
    first_sheet = workbook_root.find("main:sheets/main:sheet", MAIN_NS)
    # Some spreadsheet writers store workbook relationship targets as
    # "/xl/worksheets/sheet1.xml"; normalize them before reading from zip.
    target = rel_map[first_sheet.attrib[REL_ID]].lstrip("/")
    return target if target.startswith("xl/") else f"xl/{target}"


def _read_rows(workbook: ZipFile, sheet_path: str, shared_strings: list[str]) -> list[list[str]]:
    root = ET.fromstring(workbook.read(sheet_path))
    rows = []
    for row in root.findall("main:sheetData/main:row", MAIN_NS):
        values = []
        for cell in row.findall("main:c", MAIN_NS):
            index = _cell_column_index(cell.attrib.get("r", "A1"))
            while len(values) <= index:
                values.append("")
            values[index] = _cell_value(cell, shared_strings)
        if any(value != "" for value in values):
            rows.append(values)
    return rows


def _cell_column_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref if char.isalpha())
    number = 0
    for char in letters:
        number = number * 26 + ord(char.upper()) - 64
    return number - 1


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    value = cell.find("main:v", MAIN_NS)
    if value is None:
        inline = cell.find("main:is", MAIN_NS)
        if inline is None:
            return ""
        return "".join(text.text or "" for text in inline.findall(".//main:t", MAIN_NS))

    text = value.text or ""
    if cell.attrib.get("t") == "s":
        return shared_strings[int(text)]
    return text


def _find_header_index(rows: list[list[str]]) -> int | None:
    header_markers = {
        "building_id",
        "candidate_id",
        "edge_id",
        "edge_type",
        "entrance_id",
        "from_node_id",
        "indoor_edge_id",
        "indoor_node_id",
        "node_id",
        "node_type",
        "outdoor_node_id",
        "pdf_id",
        "room_id",
        "room_type",
    }
    for index, row in enumerate(rows):
        lowered = {_normalize_header(value) for value in row}
        if lowered & header_markers:
            return index
    return None


def _normalize_header(value: str) -> str:
    return value.strip().lower()
