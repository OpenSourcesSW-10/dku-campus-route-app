import csv
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.seed.xlsx_reader import read_first_sheet


REQUIRED_FILES = {
    "buildings": ("Building_Master.xlsx", "Building_Master.csv"),
    "aliases": ("Building_aliases.xlsx", "Building_aliases.csv"),
    "rooms": ("rooms_master.xlsx", "rooms_master.csv"),
    "indoor_maps": ("floor_pdf_inventory.xlsx", "floor_pdf_inventory.csv"),
}


@dataclass
class Week4DataReport:
    # 4주차 엑셀 데이터 검증/import 결과를 한 번에 담는다.
    stats: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_week4_excel(data_dir: Path) -> dict[str, list[dict[str, str]]]:
    # DB 담당자가 준 4개 xlsx/csv 파일을 테이블별 row 목록으로 읽는다.
    data = {}
    for key, filenames in REQUIRED_FILES.items():
        path = _find_existing_file(data_dir, filenames)
        if path is None:
            candidates = ", ".join(str(data_dir / filename) for filename in filenames)
            raise FileNotFoundError(f"Missing required file. Expected one of: {candidates}")
        data[key] = _read_table(path)
    return data


def validate_week4_excel(data_dir: Path) -> Week4DataReport:
    # 엑셀 파일끼리 ID가 서로 연결되는지 확인한다.
    report = Week4DataReport()
    data = load_week4_excel(data_dir)
    report.stats = {key: len(rows) for key, rows in data.items()}

    building_ids = {row.get("building_id", "") for row in data["buildings"]}
    alias_building_ids = {row.get("building_id", "") for row in data["aliases"]}
    room_building_ids = {row.get("building_id", "") for row in data["rooms"]}
    map_keys = {
        _map_key(row.get("building_id", ""), row.get("floor_label", ""))
        for row in data["indoor_maps"]
    }

    _require_columns(report, "Building_Master.xlsx", data["buildings"], ["building_id", "building_name"])
    _require_columns(report, "Building_aliases.xlsx", data["aliases"], ["alias", "building_id"])
    _require_columns(report, "rooms_master.xlsx", data["rooms"], ["room_id", "building_id", "floor_number", "floor_label", "room_code"])
    _require_columns(report, "floor_pdf_inventory.xlsx", data["indoor_maps"], ["building_id", "floor_number", "floor_label", "pdf_file"])

    for building_id in sorted(alias_building_ids - building_ids):
        report.errors.append(f"Alias references unknown building_id: {building_id}")

    for building_id in sorted(room_building_ids - building_ids):
        report.errors.append(f"Room references unknown building_id: {building_id}")

    for row in data["rooms"]:
        key = _map_key(row.get("building_id", ""), row.get("floor_label", ""))
        if key not in map_keys:
            report.errors.append(f"Room {row.get('room_id')} has no matching indoor map: {key}")

    duplicate_aliases = _duplicates(
        f"{row.get('building_id')}::{row.get('alias')}" for row in data["aliases"]
    )
    for duplicate in duplicate_aliases:
        report.warnings.append(f"Duplicate building alias: {duplicate}")

    duplicate_rooms = _duplicates(row.get("room_id", "") for row in data["rooms"])
    for duplicate in duplicate_rooms:
        report.errors.append(f"Duplicate room_id: {duplicate}")

    duplicate_room_numbers = _duplicates(
        f"{row.get('building_id')}::{row.get('room_code')}" for row in data["rooms"]
    )
    for duplicate in duplicate_room_numbers:
        report.warnings.append(
            f"Repeated room number across floors: {duplicate}. Import will make room_code unique with floor_label."
        )

    if data["rooms"]:
        report.warnings.append(
            "Import room_positions/rooms_positions separately to include room highlight coordinates in indoor-map API responses."
        )

    return report


def import_week4_excel(db: Any, data_dir: Path, replace: bool = False) -> Week4DataReport:
    # 검증을 통과한 엑셀 데이터를 현재 DB에 upsert한다.
    from app.models import Building, BuildingAlias, IndoorMap, Room

    report = validate_week4_excel(data_dir)
    if not report.ok:
        return report

    data = load_week4_excel(data_dir)
    if replace:
        _clear_imported_data(db)

    building_code_by_id = {}
    for row in data["buildings"]:
        building_id = row["building_id"]
        building_code = row.get("building_code") or building_id
        building_code_by_id[building_id] = building_code
        db.merge(
            Building(
                building_id=building_id,
                name=row.get("building_name") or building_id,
                short_code=building_code,
                latitude=_float_or_none(row.get("latitude")),
                longitude=_float_or_none(row.get("longitude")),
                main_outdoor_node_id=None,
                description=f"category={row.get('category', '')}; has_indoor_map={row.get('has_indoor_map', '')}",
            )
        )

    for index, row in enumerate(data["aliases"], start=1):
        db.merge(
            BuildingAlias(
                alias_id=_int(row.get("alias_id"), index),
                building_id=row["building_id"],
                alias=row["alias"],
                priority=_int(row.get("alias_id"), 100),
            )
        )

    for row in data["indoor_maps"]:
        map_id = _indoor_map_id(row["building_id"], row["floor_label"])
        source_pdf = row.get("pdf_file") or ""
        db.merge(
            IndoorMap(
                indoor_map_id=map_id,
                building_id=row["building_id"],
                floor_number=_int(row.get("floor_number"), 0),
                floor_label=row["floor_label"],
                source_pdf_name=source_pdf,
                map_file_url=_map_file_url(source_pdf),
                canvas_width=_canvas_width(data_dir, source_pdf, row),
                canvas_height=_canvas_height(data_dir, source_pdf, row),
                version="week4-excel",
                status="converted" if _truthy(row.get("has_map_data")) else "draft",
                created_at=None,
            )
        )

    for row in data["rooms"]:
        building_id = row["building_id"]
        room_number = row["room_code"]
        db.merge(
            Room(
                room_id=row["room_id"],
                building_id=building_id,
                indoor_map_id=_indoor_map_id(building_id, row["floor_label"]),
                room_code=f"{building_code_by_id.get(building_id, building_id)}-{row['floor_label']}-{room_number}",
                room_number=room_number,
                floor_number=_int(row.get("floor_number"), 1),
                room_type=row.get("room_type") or "OTHER",
                nearest_indoor_node_id=None,
                description=row.get("room_name") or None,
            )
        )

    db.commit()
    return report


def _clear_imported_data(db: Any) -> None:
    # 엑셀에서 다시 넣는 기본 테이블만 정리한다.
    from app.models import (
        Building,
        BuildingAlias,
        EntranceLink,
        IndoorEdge,
        IndoorMap,
        IndoorNode,
        OutdoorNode,
        Room,
        RoomPosition,
    )

    db.query(EntranceLink).delete()
    db.query(OutdoorNode).delete()
    db.query(IndoorEdge).delete()
    db.query(IndoorNode).delete()
    db.query(RoomPosition).delete()
    db.query(Room).delete()
    db.query(IndoorMap).delete()
    db.query(BuildingAlias).delete()
    db.query(Building).delete()
    db.commit()


def _find_existing_file(data_dir: Path, filenames: tuple[str, ...]) -> Path | None:
    for filename in filenames:
        path = data_dir / filename
        if path.exists():
            return path
    return None


def _read_table(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            return [
                {_normalize_header(key): (value or "").strip() for key, value in row.items() if key}
                for row in csv.DictReader(csv_file)
                if any((value or "").strip() for value in row.values())
            ]
    return read_first_sheet(path)


def _normalize_header(value: str) -> str:
    return value.strip().lower()


def _require_columns(report: Week4DataReport, filename: str, rows: list[dict[str, str]], columns: list[str]) -> None:
    if not rows:
        report.errors.append(f"{filename} has no data rows")
        return
    existing = set(rows[0])
    for column in columns:
        if column not in existing:
            report.errors.append(f"{filename} is missing required column: {column}")


def _duplicates(values) -> list[str]:
    seen = set()
    duplicated = set()
    for value in values:
        if not value:
            continue
        if value in seen:
            duplicated.add(value)
        seen.add(value)
    return sorted(duplicated)


def _indoor_map_id(building_id: str, floor_label: str) -> str:
    return f"MAP_{building_id}_{floor_label}"


def _map_key(building_id: str, floor_label: str) -> str:
    return f"{building_id}::{floor_label}"


def _map_file_url(source_pdf: str) -> str:
    if not source_pdf:
        return "/maps/not-ready.svg"
    return f"/maps/{Path(source_pdf).stem}.svg"


def _canvas_width(data_dir: Path, source_pdf: str, row: dict[str, str]) -> int:
    width, _ = _canvas_size(data_dir, source_pdf, row)
    return width


def _canvas_height(data_dir: Path, source_pdf: str, row: dict[str, str]) -> int:
    _, height = _canvas_size(data_dir, source_pdf, row)
    return height


def _canvas_size(data_dir: Path, source_pdf: str, row: dict[str, str]) -> tuple[int, int]:
    # DB가 제공한 ICT/LIB 좌표는 1000x707 PNG 기준이므로, 실제 PNG가 있으면 그 크기를 우선 사용한다.
    explicit_width = _int_or_none(row.get("canvas_width") or row.get("page_width"))
    explicit_height = _int_or_none(row.get("canvas_height") or row.get("page_height"))
    if explicit_width and explicit_height:
        return explicit_width, explicit_height

    png_size = _find_png_size(data_dir, source_pdf)
    if png_size is not None:
        return png_size

    return 1000, 707


def _find_png_size(data_dir: Path, source_pdf: str) -> tuple[int, int] | None:
    if not source_pdf:
        return None

    stem = Path(source_pdf).stem
    candidates = [
        data_dir / "PNG(1000X707)" / "ICT(1000X707)" / f"{stem}-1.png",
        data_dir / "PNG(1000X707)" / "LIB(1000X707)" / f"{stem}-1.png",
        data_dir / "PNG" / "ICT" / f"{stem}-1.png",
        data_dir / "PNG" / "LIB" / f"{stem}-1.png",
    ]
    for candidate in candidates:
        size = _read_png_size(candidate)
        if size is not None:
            return size
    return None


def _read_png_size(path: Path) -> tuple[int, int] | None:
    if not path.exists():
        return None
    with path.open("rb") as png_file:
        header = png_file.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", header[16:24])


def _int(value: str | None, default: int) -> int:
    if value in (None, ""):
        return default
    return int(float(value))


def _int_or_none(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(float(value))


def _float_or_none(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}
