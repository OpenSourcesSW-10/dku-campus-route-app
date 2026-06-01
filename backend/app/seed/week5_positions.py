import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.seed.xlsx_reader import read_first_sheet


POSITION_FILES = ("room_positions.csv", "room_positions.xlsx", "rooms_positions.csv", "rooms_positions.xlsx")


@dataclass
class Week5PositionReport:
    # 5주차 강의실 좌표 데이터 검증/import 결과를 담는다.
    stats: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_room_positions(data_dir: Path) -> list[dict[str, str]]:
    # room_positions/rooms_positions CSV 또는 XLSX를 읽어 dict row 목록으로 반환한다.
    path = _find_existing_file(data_dir, POSITION_FILES)
    if path is None:
        candidates = ", ".join(str(data_dir / filename) for filename in POSITION_FILES)
        raise FileNotFoundError(f"Missing required file. Expected one of: {candidates}")
    return _read_table(path)


def validate_room_positions(db: Any, data_dir: Path) -> Week5PositionReport:
    # 좌표 파일의 필수 컬럼, 숫자 좌표, Room/IndoorMap 연결 상태를 검증한다.
    from app.models import IndoorMap, Room

    report = Week5PositionReport()
    rows = load_room_positions(data_dir)
    report.stats = {"room_positions": len(rows), "valid_room_positions": 0, "skipped_room_positions": 0}

    _require_columns(report, "room_positions", rows, ["room_id", "x", "y", "width", "height"])
    if report.errors:
        return report

    room_ids = {room_id for (room_id,) in db.query(Room.room_id).all()}
    indoor_map_ids = {map_id for (map_id,) in db.query(IndoorMap.indoor_map_id).all()}
    duplicate_position_ids = _duplicates(_position_id(row) for row in rows)
    duplicate_room_ids = _duplicates(row.get("room_id", "") for row in rows)

    for duplicate in duplicate_position_ids:
        report.errors.append(f"Duplicate room_position_id: {duplicate}")

    for duplicate in duplicate_room_ids:
        report.warnings.append(f"Room has more than one position row: {duplicate}")

    for index, row in enumerate(rows, start=2):
        room_id = row.get("room_id", "")
        if room_id not in room_ids:
            report.warnings.append(f"Row {index}: skipped unknown room_id: {room_id}")
            report.stats["skipped_room_positions"] += 1
            continue

        room = db.get(Room, room_id)
        indoor_map_id = _indoor_map_id(row, room)
        if indoor_map_id not in indoor_map_ids:
            report.warnings.append(f"Row {index}: skipped unknown indoor_map_id: {indoor_map_id}")
            report.stats["skipped_room_positions"] += 1
            continue
        if room and indoor_map_id != room.indoor_map_id:
            report.warnings.append(
                f"Row {index}: indoor_map_id {indoor_map_id} differs from room.indoor_map_id {room.indoor_map_id}"
            )

        row_has_invalid_coordinates = False
        for column in ("x", "y", "width", "height"):
            value = _float_or_none(row.get(column))
            if value is None:
                report.warnings.append(f"Row {index}: skipped because {column} must be a number")
                row_has_invalid_coordinates = True
            elif column in {"width", "height"} and value <= 0:
                report.warnings.append(f"Row {index}: skipped because {column} must be greater than 0")
                row_has_invalid_coordinates = True

        if row_has_invalid_coordinates:
            report.stats["skipped_room_positions"] += 1
            continue

        report.stats["valid_room_positions"] += 1

    if not rows:
        report.warnings.append("room_positions has no data rows.")
    elif report.stats["valid_room_positions"] == 0:
        report.errors.append("room_positions has no valid rows to import.")

    return report


def import_room_positions(db: Any, data_dir: Path, replace: bool = False) -> Week5PositionReport:
    # 검증을 통과한 강의실 좌표를 RoomPosition 테이블에 저장한다.
    from app.models import Room, RoomPosition

    report = validate_room_positions(db, data_dir)
    if not report.ok:
        return report

    rows = load_room_positions(data_dir)
    if replace:
        db.query(RoomPosition).delete()
        db.commit()

    for row in rows:
        room = db.get(Room, row["room_id"])
        if room is None:
            continue
        if not _is_valid_position_row(row, room):
            continue

        x = _float(row.get("x"), 0.0)
        y = _float(row.get("y"), 0.0)
        width = _float(row.get("width"), 0.0)
        height = _float(row.get("height"), 0.0)
        db.merge(
            RoomPosition(
                position_id=_position_id(row),
                room_id=row["room_id"],
                indoor_map_id=_indoor_map_id(row, room),
                x=x,
                y=y,
                width=width,
                height=height,
                polygon_points=row.get("polygon_points") or None,
                center_x=_float_or_none(row.get("center_x") or row.get("label_x")) or x + width / 2,
                center_y=_float_or_none(row.get("center_y") or row.get("label_y")) or y + height / 2,
            )
        )

        nearest_indoor_node_id = _optional_text(row.get("nearest_indoor_node_id"))
        if nearest_indoor_node_id:
            room.nearest_indoor_node_id = nearest_indoor_node_id

    db.commit()
    return report


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


def _require_columns(report: Week5PositionReport, filename: str, rows: list[dict[str, str]], columns: list[str]) -> None:
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


def _position_id(row: dict[str, str]) -> str:
    return row.get("position_id") or row.get("room_position_id") or f"POS_{row.get('room_id', '')}"


def _indoor_map_id(row: dict[str, str], room: Any) -> str:
    return row.get("indoor_map_id") or room.indoor_map_id


def _is_valid_position_row(row: dict[str, str], room: Any) -> bool:
    if not row.get("room_id"):
        return False
    if not _indoor_map_id(row, room):
        return False
    for column in ("x", "y", "width", "height"):
        value = _float_or_none(row.get(column))
        if value is None:
            return False
        if column in {"width", "height"} and value <= 0:
            return False
    return True


def _normalize_header(value: str) -> str:
    return value.strip().lower()


def _optional_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    if text.lower() in {"", "nan", "none", "null"}:
        return None
    return text


def _float_or_none(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _float(value: str | None, default: float) -> float:
    parsed = _float_or_none(value)
    return default if parsed is None else parsed
