from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.seed.table_reader import find_existing_file, float_value, optional_str, read_table


OUTDOOR_NODE_FILES = ("outdoor_nodes.csv", "outdoor_nodes.xlsx", "outdoor_node.csv", "outdoor_node.xlsx")
ENTRANCE_LINK_FILES = ("entrance_links.csv", "entrance_links.xlsx", "entrance_link.csv", "entrance_link.xlsx")


@dataclass
class Week6OutdoorStructureReport:
    stats: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_week6_outdoor_structure(data_dir: Path) -> dict[str, list[dict[str, str]]]:
    node_path = find_existing_file(data_dir, OUTDOOR_NODE_FILES)
    entrance_link_path = find_existing_file(data_dir, ENTRANCE_LINK_FILES)
    if node_path is None:
        raise FileNotFoundError(f"Missing required file: one of {OUTDOOR_NODE_FILES}")
    if entrance_link_path is None:
        raise FileNotFoundError(f"Missing required file: one of {ENTRANCE_LINK_FILES}")
    return {
        "outdoor_nodes": [_normalize_outdoor_node(row) for row in read_table(node_path)],
        "entrance_links": [_normalize_entrance_link(row) for row in read_table(entrance_link_path)],
    }


def validate_week6_outdoor_structure(db: Any, data_dir: Path) -> Week6OutdoorStructureReport:
    from app.models import Building, IndoorNode

    report = Week6OutdoorStructureReport()
    data = load_week6_outdoor_structure(data_dir)
    report.stats = {key: len(rows) for key, rows in data.items()}
    _require_columns(report, "outdoor_nodes", data["outdoor_nodes"], ["outdoor_node_id", "x", "y", "node_type"])
    _require_columns(report, "entrance_links", data["entrance_links"], ["building_id", "entrance_id", "indoor_node_id", "outdoor_node_id"])
    if report.errors:
        return report

    building_ids = {building_id for (building_id,) in db.query(Building.building_id).all()}
    indoor_node_ids = {node_id for (node_id,) in db.query(IndoorNode.indoor_node_id).all()}
    outdoor_node_ids = {row.get("outdoor_node_id", "") for row in data["outdoor_nodes"]}

    for duplicate in _duplicates(row.get("outdoor_node_id", "") for row in data["outdoor_nodes"]):
        report.errors.append(f"Duplicate outdoor_node_id: {duplicate}")

    for row in data["entrance_links"]:
        building_id = row.get("building_id", "")
        indoor_node_id = row.get("indoor_node_id", "")
        outdoor_node_id = row.get("outdoor_node_id", "")
        if building_id not in building_ids:
            report.errors.append(f"Entrance link references unknown building_id: {building_id}")
        if indoor_node_id not in indoor_node_ids:
            report.errors.append(f"Entrance link references unknown indoor_node_id: {row.get('entrance_id')} -> {indoor_node_id}")
        if outdoor_node_id not in outdoor_node_ids:
            report.errors.append(f"Entrance link references unknown outdoor_node_id: {row.get('entrance_id')} -> {outdoor_node_id}")

    report.warnings.append("outdoor_edges file is not provided yet. Outdoor route calculation needs outdoor_edges.")
    return report


def import_week6_outdoor_structure(db: Any, data_dir: Path, replace: bool = False) -> Week6OutdoorStructureReport:
    from app.models import EntranceLink, OutdoorNode

    report = validate_week6_outdoor_structure(db, data_dir)
    if not report.ok:
        return report
    data = load_week6_outdoor_structure(data_dir)
    if replace:
        db.query(EntranceLink).delete()
        db.query(OutdoorNode).delete()
        db.commit()

    for row in data["outdoor_nodes"]:
        db.merge(
            OutdoorNode(
                outdoor_node_id=row["outdoor_node_id"],
                node_type=row["node_type"],
                building_id=optional_str(row.get("building_id")),
                latitude=None,
                longitude=None,
                map_x=float_value(row.get("x")),
                map_y=float_value(row.get("y")),
                label=optional_str(row.get("label")),
                description=optional_str(row.get("description")),
            )
        )

    for row in data["entrance_links"]:
        db.merge(
            EntranceLink(
                link_id=row.get("link_id") or f"LINK_{row['building_id']}_{row['entrance_id']}",
                building_id=row["building_id"],
                outdoor_node_id=row["outdoor_node_id"],
                indoor_node_id=row["indoor_node_id"],
                entrance_name=row["entrance_id"],
                is_main=False,
            )
        )

    db.commit()
    return report


def _normalize_outdoor_node(row: dict[str, str]) -> dict[str, str]:
    normalized = dict(row)
    _copy_alias(normalized, "outdoor_node_id", "node_id")
    _copy_alias(normalized, "description", "비고(참고, 사용 시 지울 것)", "비고(참고)")
    return normalized


def _normalize_entrance_link(row: dict[str, str]) -> dict[str, str]:
    normalized = dict(row)
    _copy_alias(normalized, "indoor_node_id", "node_id")
    return normalized


def _copy_alias(row: dict[str, str], target: str, *aliases: str) -> None:
    if row.get(target):
        return
    for alias in aliases:
        if row.get(alias):
            row[target] = row[alias]
            return


def _require_columns(report: Week6OutdoorStructureReport, filename: str, rows: list[dict[str, str]], columns: list[str]) -> None:
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
        if value and value in seen:
            duplicated.add(value)
        seen.add(value)
    return sorted(duplicated)
