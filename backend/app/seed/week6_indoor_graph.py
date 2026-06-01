from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.algorithms.cost_function import estimate_static_edge_cost
from app.seed.table_reader import bool_value, find_existing_file, float_value, int_value, optional_str, read_table


INDOOR_NODE_FILES = ("indoor_nodes.csv", "indoor_nodes.xlsx")
INDOOR_EDGE_FILES = ("indoor_edges.csv", "indoor_edges.xlsx")
ROOM_NODE_FILES = ("room_nearest_nodes.csv", "room_nearest_nodes.xlsx", "rooms_master.csv", "rooms_master.xlsx")


@dataclass
class Week6IndoorGraphReport:
    stats: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_week6_indoor_graph(data_dir: Path) -> dict[str, list[dict[str, str]]]:
    node_path = find_existing_file(data_dir, INDOOR_NODE_FILES)
    edge_path = find_existing_file(data_dir, INDOOR_EDGE_FILES)
    if node_path is None:
        raise FileNotFoundError(f"Missing required file: one of {INDOOR_NODE_FILES}")
    if edge_path is None:
        raise FileNotFoundError(f"Missing required file: one of {INDOOR_EDGE_FILES}")
    room_node_path = find_existing_file(data_dir, ROOM_NODE_FILES)
    return {
        "indoor_nodes": read_table(node_path),
        "indoor_edges": read_table(edge_path),
        "room_nodes": read_table(room_node_path) if room_node_path else [],
    }


def validate_week6_indoor_graph(db: Any, data_dir: Path) -> Week6IndoorGraphReport:
    from app.models import Building, IndoorMap, Room

    report = Week6IndoorGraphReport()
    data = load_week6_indoor_graph(data_dir)
    report.stats = {key: len(rows) for key, rows in data.items()}
    _require_columns(report, "indoor_nodes", data["indoor_nodes"], ["indoor_node_id", "building_id", "indoor_map_id", "floor_number", "node_type", "x", "y"])
    _require_columns(report, "indoor_edges", data["indoor_edges"], ["indoor_edge_id", "indoor_map_id", "from_node_id", "to_node_id", "distance", "estimated_time", "edge_type"])
    if report.errors:
        return report

    building_ids = {building_id for (building_id,) in db.query(Building.building_id).all()}
    indoor_map_ids = {map_id for (map_id,) in db.query(IndoorMap.indoor_map_id).all()}
    room_ids = {room_id for (room_id,) in db.query(Room.room_id).all()}
    node_ids = {row.get("indoor_node_id", "") for row in data["indoor_nodes"]}

    for duplicate in _duplicates(row.get("indoor_node_id", "") for row in data["indoor_nodes"]):
        report.errors.append(f"Duplicate indoor_node_id: {duplicate}")
    for duplicate in _duplicates(row.get("indoor_edge_id", "") for row in data["indoor_edges"]):
        report.errors.append(f"Duplicate indoor_edge_id: {duplicate}")

    for row in data["indoor_nodes"]:
        if row.get("building_id") not in building_ids:
            report.errors.append(f"Indoor node references unknown building_id: {row.get('indoor_node_id')} -> {row.get('building_id')}")
        if row.get("indoor_map_id") not in indoor_map_ids:
            report.errors.append(f"Indoor node references unknown indoor_map_id: {row.get('indoor_node_id')} -> {row.get('indoor_map_id')}")

    for row in data["indoor_edges"]:
        if row.get("from_node_id") not in node_ids:
            report.errors.append(f"Indoor edge has unknown from_node_id: {row.get('indoor_edge_id')} -> {row.get('from_node_id')}")
        if row.get("to_node_id") not in node_ids:
            report.errors.append(f"Indoor edge has unknown to_node_id: {row.get('indoor_edge_id')} -> {row.get('to_node_id')}")

    for row in data["room_nodes"]:
        room_id = row.get("room_id", "")
        nearest = row.get("nearest_indoor_node_id", "")
        if room_id and room_id not in room_ids:
            report.errors.append(f"room_nodes references unknown room_id: {room_id}")
        if nearest and nearest not in node_ids:
            report.errors.append(f"room_nodes references unknown nearest_indoor_node_id: {room_id} -> {nearest}")
    if not data["room_nodes"]:
        report.warnings.append("room_nearest_nodes.csv was not provided. Room-to-room routes need nearest_indoor_node_id.")
    return report


def import_week6_indoor_graph(db: Any, data_dir: Path, replace: bool = False) -> Week6IndoorGraphReport:
    from app.models import IndoorEdge, IndoorNode, Room

    report = validate_week6_indoor_graph(db, data_dir)
    if not report.ok:
        return report
    data = load_week6_indoor_graph(data_dir)
    if replace:
        db.query(IndoorEdge).delete()
        db.query(IndoorNode).delete()
        db.commit()

    for row in data["indoor_nodes"]:
        db.merge(IndoorNode(
            indoor_node_id=row["indoor_node_id"],
            building_id=row["building_id"],
            indoor_map_id=row["indoor_map_id"],
            floor_number=int_value(row.get("floor_number")),
            node_type=row["node_type"],
            x=float_value(row.get("x")),
            y=float_value(row.get("y")),
            label=optional_str(row.get("label")),
            vertical_group_id=optional_str(row.get("vertical_group_id")),
            description=optional_str(row.get("description")),
        ))

    for row in data["indoor_edges"]:
        edge_stub = SimpleNamespace(
            distance=float_value(row.get("distance")),
            estimated_time=float_value(row.get("estimated_time")),
            edge_type=row["edge_type"],
            has_stairs=bool_value(row.get("has_stairs")),
            has_slope=bool_value(row.get("has_slope")),
            slope_level=int_value(row.get("slope_level")),
            is_elevator=bool_value(row.get("is_elevator")),
            is_ramp=bool_value(row.get("is_ramp")),
            is_indoor=bool_value(row.get("is_indoor"), True),
            is_covered=bool_value(row.get("is_covered"), True),
            is_accessible=bool_value(row.get("is_accessible"), True),
            complexity_level=int_value(row.get("complexity_level")),
        )
        db.merge(IndoorEdge(
            indoor_edge_id=row["indoor_edge_id"],
            indoor_map_id=row["indoor_map_id"],
            from_node_id=row["from_node_id"],
            to_node_id=row["to_node_id"],
            is_bidirectional=bool_value(row.get("is_bidirectional"), True),
            distance=float_value(row.get("distance")),
            estimated_time=float_value(row.get("estimated_time")),
            edge_type=row["edge_type"],
            has_stairs=bool_value(row.get("has_stairs")),
            has_slope=bool_value(row.get("has_slope")),
            slope_level=int_value(row.get("slope_level")),
            is_elevator=bool_value(row.get("is_elevator")),
            is_ramp=bool_value(row.get("is_ramp")),
            is_indoor=bool_value(row.get("is_indoor"), True),
            is_covered=bool_value(row.get("is_covered"), True),
            is_accessible=bool_value(row.get("is_accessible"), True),
            complexity_level=int_value(row.get("complexity_level")),
            cost_fast=float_value(row.get("cost_fast"), estimate_static_edge_cost(edge_stub, "DEFAULT")),
            cost_comfortable=float_value(row.get("cost_comfortable"), estimate_static_edge_cost(edge_stub, "COMFORTABLE")),
            cost_indoor=float_value(row.get("cost_indoor"), estimate_static_edge_cost(edge_stub, "RAINY")),
            description=optional_str(row.get("description")),
        ))

    for row in data["room_nodes"]:
        room_id = row.get("room_id", "")
        nearest = row.get("nearest_indoor_node_id", "")
        if room_id and nearest:
            room = db.get(Room, room_id)
            if room:
                room.nearest_indoor_node_id = nearest
    db.commit()
    return report


def _require_columns(report: Week6IndoorGraphReport, filename: str, rows: list[dict[str, str]], columns: list[str]) -> None:
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
