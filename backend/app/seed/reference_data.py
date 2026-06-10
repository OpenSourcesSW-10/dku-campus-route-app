from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.seed.table_reader import find_existing_file, int_value, optional_str, read_table


REFERENCE_FILES = {
    "edge_types": ("edge_types.csv", "edge_types.xlsx"),
    "indoor_node_types": ("indoor_node_types.csv", "indoor_node_types.xlsx"),
    "room_categories": ("room_categories.csv", "room_categories.xlsx"),
    "entrance_master": ("entrance_master.csv", "entrance_master.xlsx"),
}


@dataclass
class ReferenceDataReport:
    # DB 참조 테이블 검증/import 결과 보관.
    stats: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_reference_data(data_dir: Path) -> dict[str, list[dict[str, str]]]:
    # GitHub DB 브랜치의 참조 CSV가 있으면 읽고, 없으면 빈 목록으로 유지.
    data: dict[str, list[dict[str, str]]] = {}
    for key, filenames in REFERENCE_FILES.items():
        path = find_existing_file(data_dir, filenames)
        data[key] = read_table(path) if path else []
    return data


def validate_reference_data(db: Any, data_dir: Path) -> ReferenceDataReport:
    # 참조 테이블은 경로 계산 차단 요소는 아니지만, 있으면 ID/중복/건물 참조를 검증.
    from app.models import Building

    report = ReferenceDataReport()
    data = load_reference_data(data_dir)
    report.stats = {key: len(rows) for key, rows in data.items()}

    _require_optional_columns(report, "edge_types", data["edge_types"], ["edge_type", "display_name"])
    _require_optional_columns(report, "indoor_node_types", data["indoor_node_types"], ["node_type", "display_name"])
    _require_optional_columns(report, "room_categories", data["room_categories"], ["room_type", "display_name"])
    _require_optional_columns(
        report,
        "entrance_master",
        data["entrance_master"],
        ["entrance_id", "building_id", "floor_number", "entrance_name", "entrance_type"],
    )
    if report.errors:
        return report

    for key, rows in data.items():
        if not rows:
            report.warnings.append(f"{key} file is not provided. Reference table import skipped.")

    for duplicate in _duplicates(row.get("edge_type", "") for row in data["edge_types"]):
        report.errors.append(f"Duplicate edge_type: {duplicate}")
    for duplicate in _duplicates(row.get("node_type", "") for row in data["indoor_node_types"]):
        report.errors.append(f"Duplicate indoor node_type: {duplicate}")
    for duplicate in _duplicates(row.get("room_type", "") for row in data["room_categories"]):
        report.errors.append(f"Duplicate room_type: {duplicate}")
    for duplicate in _duplicates(row.get("entrance_id", "") for row in data["entrance_master"]):
        report.errors.append(f"Duplicate entrance_id: {duplicate}")

    building_ids = {building_id for (building_id,) in db.query(Building.building_id).all()}
    for row in data["entrance_master"]:
        building_id = row.get("building_id", "")
        if building_ids and building_id not in building_ids:
            report.errors.append(f"Entrance master references unknown building_id: {row.get('entrance_id')} -> {building_id}")
        if not _is_int(row.get("floor_number")):
            report.errors.append(f"Entrance master has invalid floor_number: {row.get('entrance_id')} -> {row.get('floor_number')}")

    return report


def import_reference_data(db: Any, data_dir: Path, replace: bool = False) -> ReferenceDataReport:
    from app.models import EdgeType, EntranceMaster, IndoorNodeType, RoomCategory

    report = validate_reference_data(db, data_dir)
    if not report.ok:
        return report

    data = load_reference_data(data_dir)
    if replace:
        db.query(EntranceMaster).delete()
        db.query(RoomCategory).delete()
        db.query(IndoorNodeType).delete()
        db.query(EdgeType).delete()
        db.commit()

    for row in data["edge_types"]:
        db.merge(
            EdgeType(
                edge_type=row["edge_type"],
                display_name=row.get("display_name") or row["edge_type"],
                description=optional_str(row.get("description")),
            )
        )

    for row in data["indoor_node_types"]:
        db.merge(
            IndoorNodeType(
                node_type=row["node_type"],
                display_name=row.get("display_name") or row["node_type"],
                description=optional_str(row.get("description")),
            )
        )

    for row in data["room_categories"]:
        db.merge(
            RoomCategory(
                room_type=row["room_type"],
                display_name=row.get("display_name") or row["room_type"],
                description=optional_str(row.get("description")),
            )
        )

    for row in data["entrance_master"]:
        db.merge(
            EntranceMaster(
                entrance_id=row["entrance_id"],
                building_id=row["building_id"],
                floor_number=int_value(row.get("floor_number")),
                entrance_name=row["entrance_name"],
                entrance_type=row["entrance_type"],
                description=optional_str(row.get("description")),
            )
        )

    db.commit()
    return report


def _require_optional_columns(report: ReferenceDataReport, name: str, rows: list[dict[str, str]], columns: list[str]) -> None:
    if not rows:
        return
    existing = set(rows[0])
    for column in columns:
        if column not in existing:
            report.errors.append(f"{name} is missing required column: {column}")


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


def _is_int(value: str | None) -> bool:
    if optional_str(value) is None:
        return False
    try:
        int_value(value)
    except (TypeError, ValueError):
        return False
    return True
