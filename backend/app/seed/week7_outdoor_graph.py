from dataclasses import dataclass, field
from math import hypot
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.algorithms.cost_function import estimate_static_edge_cost
from app.seed.table_reader import bool_value, find_existing_file, float_value, int_value, optional_str, read_table


OUTDOOR_NODE_FILES = ("outdoor_nodes.csv", "outdoor_nodes.xlsx", "outdoor_node.csv", "outdoor_node.xlsx")
OUTDOOR_EDGE_FILES = ("outdoor_edges.csv", "outdoor_edges.xlsx", "outdoor_edge.csv", "outdoor_edge.xlsx")
ENTRANCE_LINK_FILES = ("entrance_links.csv", "entrance_links.xlsx", "entrance_link.csv", "entrance_link.xlsx")
DEFAULT_WALKING_SPEED_MPS = 1.2
MIN_EDGE_DISTANCE = 1.0


@dataclass
class Week7OutdoorGraphReport:
    stats: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_week7_outdoor_graph(data_dir: Path) -> dict[str, list[dict[str, str]]]:
    node_path = find_existing_file(data_dir, OUTDOOR_NODE_FILES)
    edge_path = find_existing_file(data_dir, OUTDOOR_EDGE_FILES)
    entrance_path = find_existing_file(data_dir, ENTRANCE_LINK_FILES)
    if node_path is None:
        raise FileNotFoundError(f"Missing required file: one of {OUTDOOR_NODE_FILES}")
    if entrance_path is None:
        raise FileNotFoundError(f"Missing required file: one of {ENTRANCE_LINK_FILES}")
    return {
        "outdoor_nodes": [_normalize_outdoor_node(row) for row in read_table(node_path)],
        "outdoor_edges": [_normalize_outdoor_edge(row) for row in read_table(edge_path)] if edge_path else [],
        "entrance_links": [_normalize_entrance_link(row) for row in read_table(entrance_path)],
    }


def validate_week7_outdoor_graph(db: Any, data_dir: Path) -> Week7OutdoorGraphReport:
    from app.models import Building, IndoorNode

    report = Week7OutdoorGraphReport()
    data = load_week7_outdoor_graph(data_dir)
    report.stats = {key: len(rows) for key, rows in data.items()}
    _require_columns(report, "outdoor_nodes", data["outdoor_nodes"], ["outdoor_node_id", "node_type"])
    if data["outdoor_edges"]:
        _require_columns(report, "outdoor_edges", data["outdoor_edges"], ["outdoor_edge_id", "from_node_id", "to_node_id"])
    else:
        report.warnings.append("outdoor_edges file is not provided. Integrated route API will use a temporary straight outdoor segment.")
    _require_columns(report, "entrance_links", data["entrance_links"], ["building_id", "outdoor_node_id", "indoor_node_id", "entrance_name"])
    if report.errors:
        return report

    building_ids = {building_id for (building_id,) in db.query(Building.building_id).all()}
    indoor_node_ids = {node_id for (node_id,) in db.query(IndoorNode.indoor_node_id).all()}
    outdoor_node_ids = {row.get("outdoor_node_id", "") for row in data["outdoor_nodes"]}
    edge_node_ids = set()

    for duplicate in _duplicates(row.get("outdoor_node_id", "") for row in data["outdoor_nodes"]):
        report.errors.append(f"Duplicate outdoor_node_id: {duplicate}")
    for duplicate in _duplicates(row.get("outdoor_edge_id", "") for row in data["outdoor_edges"]):
        report.errors.append(f"Duplicate outdoor_edge_id: {duplicate}")
    for duplicate in _duplicates(_entrance_link_id(row) for row in data["entrance_links"]):
        report.errors.append(f"Duplicate entrance link_id: {duplicate}")

    for row in data["outdoor_nodes"]:
        building_id = row.get("building_id")
        if building_id and building_id not in building_ids:
            report.errors.append(f"Outdoor node references unknown building_id: {row.get('outdoor_node_id')} -> {building_id}")

    for row in data["outdoor_edges"]:
        from_node_id = row.get("from_node_id")
        to_node_id = row.get("to_node_id")
        if from_node_id not in outdoor_node_ids:
            report.errors.append(f"Outdoor edge has unknown from_node_id: {row.get('outdoor_edge_id')} -> {from_node_id}")
        if to_node_id not in outdoor_node_ids:
            report.errors.append(f"Outdoor edge has unknown to_node_id: {row.get('outdoor_edge_id')} -> {to_node_id}")
        edge_node_ids.update(node_id for node_id in (from_node_id, to_node_id) if node_id)

    for row in data["entrance_links"]:
        if row.get("building_id") not in building_ids:
            report.errors.append(f"Entrance link references unknown building_id: {row.get('link_id')} -> {row.get('building_id')}")
        if row.get("outdoor_node_id") not in outdoor_node_ids:
            report.errors.append(f"Entrance link references unknown outdoor_node_id: {row.get('link_id')} -> {row.get('outdoor_node_id')}")
        if row.get("indoor_node_id") not in indoor_node_ids:
            report.errors.append(f"Entrance link references unknown indoor_node_id: {row.get('link_id')} -> {row.get('indoor_node_id')}")
        if data["outdoor_edges"] and row.get("outdoor_node_id") not in edge_node_ids:
            report.errors.append(f"Entrance outdoor node is isolated from outdoor_edges: {row.get('entrance_name')} -> {row.get('outdoor_node_id')}")

    if not report.errors and data["outdoor_edges"]:
        _validate_entrance_connectivity(report, data["outdoor_edges"], data["entrance_links"])
    return report


def import_week7_outdoor_graph(db: Any, data_dir: Path, replace: bool = False) -> Week7OutdoorGraphReport:
    from app.models import EntranceLink, IndoorNode, OutdoorEdge, OutdoorNode

    report = validate_week7_outdoor_graph(db, data_dir)
    if not report.ok:
        return report
    data = load_week7_outdoor_graph(data_dir)
    if replace:
        db.query(EntranceLink).delete()
        db.query(OutdoorEdge).delete()
        db.query(OutdoorNode).delete()
        db.commit()

    node_by_id = {row["outdoor_node_id"]: row for row in data["outdoor_nodes"]}
    indoor_floor_by_id = {node_id: floor for node_id, floor in db.query(IndoorNode.indoor_node_id, IndoorNode.floor_number).all()}
    node_altitudes: dict[str, float | None] = {}
    for row in data["outdoor_nodes"]:
        altitude_m = _optional_float(row.get("altitude_m"))
        node_altitudes[row["outdoor_node_id"]] = altitude_m
        db.merge(OutdoorNode(
            outdoor_node_id=row["outdoor_node_id"],
            node_type=row["node_type"],
            building_id=optional_str(row.get("building_id")),
            latitude=_optional_float(row.get("latitude")),
            longitude=_optional_float(row.get("longitude")),
            map_x=_optional_float(row.get("map_x") or row.get("x")),
            map_y=_optional_float(row.get("map_y") or row.get("y")),
            outdoor_level=optional_str(row.get("outdoor_level")),
            altitude_m=altitude_m,
            label=optional_str(row.get("label")) or row["outdoor_node_id"],
            description=optional_str(row.get("description")),
        ))

    auto_distance_count = 0
    auto_time_count = 0
    has_ramp_alias_count = 0
    for row in data["outdoor_edges"]:
        distance, distance_was_auto = _resolve_distance(row, node_by_id)
        estimated_time, time_was_auto = _resolve_estimated_time(row, distance)
        edge_type = _resolve_edge_type(row, node_by_id)
        altitude_gain = _resolve_altitude_gain(row, node_altitudes)
        has_stairs = bool_value(row.get("has_stairs"), edge_type in {"stair", "stairs"})
        has_slope = _resolve_has_slope(row, edge_type)
        slope_level = _resolve_slope_level(row, distance, altitude_gain, has_slope)
        if distance_was_auto:
            auto_distance_count += 1
        if time_was_auto:
            auto_time_count += 1
        if row.get("_has_ramp_alias") == "true":
            has_ramp_alias_count += 1

        is_covered = bool_value(row.get("is_covered"), edge_type in {"bridge", "covered_bridge", "covered_walkway", "building_passage"})
        is_indoor = bool_value(row.get("is_indoor"), edge_type == "building_passage")
        complexity_level = int_value(row.get("complexity_level"), 1 if has_stairs or has_slope else 0)
        accessibility_level = int_value(row.get("accessibility_level"), 0 if has_stairs else 1)
        is_shortcut = bool_value(row.get("is_shortcut"))
        edge_stub = SimpleNamespace(
            distance=distance,
            estimated_time=estimated_time,
            edge_type=edge_type,
            is_covered=is_covered,
            is_indoor=is_indoor,
            has_stairs=has_stairs,
            has_slope=has_slope,
            slope_level=slope_level,
            complexity_level=complexity_level,
            accessibility_level=accessibility_level,
            is_shortcut=is_shortcut,
        )
        db.merge(OutdoorEdge(
            outdoor_edge_id=row["outdoor_edge_id"],
            from_node_id=row["from_node_id"],
            to_node_id=row["to_node_id"],
            is_bidirectional=bool_value(row.get("is_bidirectional"), True),
            distance=distance,
            estimated_time=estimated_time,
            edge_type=edge_type,
            is_covered=is_covered,
            is_indoor=is_indoor,
            has_stairs=has_stairs,
            has_slope=has_slope,
            slope_level=slope_level,
            altitude_gain=altitude_gain,
            complexity_level=complexity_level,
            accessibility_level=accessibility_level,
            is_shortcut=is_shortcut,
            cost_fast=float_value(row.get("cost_fast"), estimate_static_edge_cost(edge_stub, "FAST")),
            cost_comfortable=float_value(row.get("cost_comfortable"), estimate_static_edge_cost(edge_stub, "COMFORTABLE")),
            cost_indoor=float_value(row.get("cost_indoor"), estimate_static_edge_cost(edge_stub, "INDOOR_FOCUSED")),
            description=optional_str(row.get("description")),
        ))

    for row in data["entrance_links"]:
        indoor_node_id = row["indoor_node_id"]
        floor_number = _optional_int(row.get("floor_number"))
        if floor_number is None:
            floor_number = indoor_floor_by_id.get(indoor_node_id)
        db.merge(EntranceLink(
            link_id=_entrance_link_id(row),
            building_id=row["building_id"],
            outdoor_node_id=row["outdoor_node_id"],
            indoor_node_id=indoor_node_id,
            entrance_name=row["entrance_name"],
            floor_number=floor_number,
            is_main=bool_value(row.get("is_main")),
        ))
    db.commit()

    report.stats["auto_distance_edges"] = auto_distance_count
    report.stats["auto_estimated_time_edges"] = auto_time_count
    report.stats["has_ramp_alias_edges"] = has_ramp_alias_count
    return report


def estimate_slope_level(distance: float, altitude_gain: float | None) -> int:
    if not altitude_gain or distance <= 0:
        return 0
    grade = abs(altitude_gain) / distance * 100
    if grade < 3:
        return 0
    if grade < 6:
        return 1
    if grade < 10:
        return 2
    if grade < 15:
        return 3
    return 4


def _resolve_distance(row: dict[str, str], node_by_id: dict[str, dict[str, str]]) -> tuple[float, bool]:
    explicit_distance = _optional_float(row.get("distance"))
    if explicit_distance is not None and explicit_distance > 0:
        return explicit_distance, False

    from_node = node_by_id.get(row.get("from_node_id", ""))
    to_node = node_by_id.get(row.get("to_node_id", ""))
    coordinate_distance = _coordinate_distance(from_node, to_node)
    if coordinate_distance is not None:
        return max(coordinate_distance, MIN_EDGE_DISTANCE), True
    return MIN_EDGE_DISTANCE, True


def _resolve_estimated_time(row: dict[str, str], distance: float) -> tuple[float, bool]:
    explicit_time = _optional_float(row.get("estimated_time"))
    if explicit_time is not None and explicit_time > 0:
        return explicit_time, False

    walking_speed = _optional_float(row.get("walking_speed_mps")) or DEFAULT_WALKING_SPEED_MPS
    return max(distance / walking_speed, 1.0), True


def _resolve_edge_type(row: dict[str, str], node_by_id: dict[str, dict[str, str]]) -> str:
    explicit_edge_type = optional_str(row.get("edge_type"))
    if explicit_edge_type:
        return explicit_edge_type.strip().lower()

    if bool_value(row.get("has_stairs")):
        return "stairs"
    if bool_value(row.get("has_slope"), bool_value(row.get("has_ramp"))) or _edge_touches_node_type(row, node_by_id, "ramp"):
        return "ramp"
    return "walkway"


def _resolve_has_slope(row: dict[str, str], edge_type: str) -> bool:
    return bool_value(row.get("has_slope"), bool_value(row.get("has_ramp"), edge_type == "ramp"))


def _resolve_slope_level(row: dict[str, str], distance: float, altitude_gain: float | None, has_slope: bool) -> int:
    explicit_slope_level = _optional_int(row.get("slope_level"))
    if explicit_slope_level is not None:
        return explicit_slope_level
    estimated_level = estimate_slope_level(distance, altitude_gain)
    if estimated_level > 0:
        return estimated_level
    return 1 if has_slope else 0


def _resolve_altitude_gain(row: dict[str, str], node_altitudes: dict[str, float | None]) -> float | None:
    explicit_gain = _optional_float(row.get("altitude_gain"))
    if explicit_gain is not None:
        return explicit_gain
    from_altitude = node_altitudes.get(row.get("from_node_id", ""))
    to_altitude = node_altitudes.get(row.get("to_node_id", ""))
    if from_altitude is None or to_altitude is None:
        return None
    return to_altitude - from_altitude


def _coordinate_distance(from_node: dict[str, str] | None, to_node: dict[str, str] | None) -> float | None:
    if not from_node or not to_node:
        return None
    from_x = _optional_float(from_node.get("map_x") or from_node.get("x"))
    from_y = _optional_float(from_node.get("map_y") or from_node.get("y"))
    to_x = _optional_float(to_node.get("map_x") or to_node.get("x"))
    to_y = _optional_float(to_node.get("map_y") or to_node.get("y"))
    if None not in (from_x, from_y, to_x, to_y):
        return hypot(to_x - from_x, to_y - from_y)

    from_lat = _optional_float(from_node.get("latitude"))
    from_lng = _optional_float(from_node.get("longitude"))
    to_lat = _optional_float(to_node.get("latitude"))
    to_lng = _optional_float(to_node.get("longitude"))
    if None not in (from_lat, from_lng, to_lat, to_lng):
        return hypot(to_lat - from_lat, to_lng - from_lng) * 111_000
    return None


def _edge_touches_node_type(row: dict[str, str], node_by_id: dict[str, dict[str, str]], node_type: str) -> bool:
    target = node_type.lower()
    for key in ("from_node_id", "to_node_id"):
        node = node_by_id.get(row.get(key, ""))
        if node and str(node.get("node_type", "")).strip().lower() == target:
            return True
    return False


def _validate_entrance_connectivity(
    report: Week7OutdoorGraphReport,
    edge_rows: list[dict[str, str]],
    entrance_rows: list[dict[str, str]],
) -> None:
    entrance_node_ids = {row.get("outdoor_node_id", "") for row in entrance_rows if row.get("outdoor_node_id")}
    if len(entrance_node_ids) <= 1:
        return
    reachable = _reachable_nodes(next(iter(entrance_node_ids)), edge_rows)
    unreachable = sorted(node_id for node_id in entrance_node_ids if node_id not in reachable)
    for node_id in unreachable:
        report.errors.append(f"Entrance outdoor node is not connected to the main outdoor graph: {node_id}")


def _reachable_nodes(start_node_id: str, edge_rows: list[dict[str, str]]) -> set[str]:
    graph: dict[str, list[str]] = {}
    for row in edge_rows:
        from_node_id = row.get("from_node_id")
        to_node_id = row.get("to_node_id")
        if not from_node_id or not to_node_id:
            continue
        graph.setdefault(from_node_id, []).append(to_node_id)
        if bool_value(row.get("is_bidirectional"), True):
            graph.setdefault(to_node_id, []).append(from_node_id)

    seen = {start_node_id}
    stack = [start_node_id]
    while stack:
        current = stack.pop()
        for next_node in graph.get(current, []):
            if next_node not in seen:
                seen.add(next_node)
                stack.append(next_node)
    return seen


def _optional_float(value: str | None) -> float | None:
    if not _has_value(value):
        return None
    return float_value(value)


def _optional_int(value: str | None) -> int | None:
    if not _has_value(value):
        return None
    return int_value(value)


def _has_value(value: str | None) -> bool:
    return value is not None and str(value).strip().lower() not in {"", "null", "none", "nan"}


def _require_columns(report: Week7OutdoorGraphReport, filename: str, rows: list[dict[str, str]], columns: list[str]) -> None:
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


def _entrance_link_id(row: dict[str, str]) -> str:
    return row.get("link_id") or f"LINK_{row['building_id']}_{row['entrance_name']}"


def _normalize_outdoor_node(row: dict[str, str]) -> dict[str, str]:
    normalized = dict(row)
    _copy_alias(normalized, "outdoor_node_id", "node_id")
    _copy_alias(normalized, "map_x", "x")
    _copy_alias(normalized, "map_y", "y")
    _copy_alias(normalized, "description", "비고(참고, 사용 시 지울 것)", "비고(참고)")
    return normalized


def _normalize_outdoor_edge(row: dict[str, str]) -> dict[str, str]:
    normalized = dict(row)
    _copy_alias(normalized, "outdoor_edge_id", "edge_id")
    _copy_alias(normalized, "distance", "distance_m")
    _copy_alias(normalized, "estimated_time", "estimated_time_sec")
    if not normalized.get("has_slope") and normalized.get("has_ramp"):
        normalized["_has_ramp_alias"] = "true"
    _copy_alias(normalized, "has_slope", "has_ramp")
    return normalized


def _normalize_entrance_link(row: dict[str, str]) -> dict[str, str]:
    normalized = dict(row)
    _copy_alias(normalized, "indoor_node_id", "node_id")
    _copy_alias(normalized, "entrance_name", "entrance_id")
    return normalized


def _copy_alias(row: dict[str, str], target: str, *aliases: str) -> None:
    if row.get(target):
        return
    for alias in aliases:
        if row.get(alias):
            row[target] = row[alias]
            return
