"""
Import and validate indoor graph data.

DB 담당자가 만든 indoor_nodes, indoor_edges, room_nearest_nodes 자료 정규화.
경로 계산 전에 치명적인 연결 오류 차단.
"""

from dataclasses import dataclass, field
from math import hypot
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.algorithms.cost_function import estimate_static_edge_cost
from app.seed.table_reader import bool_value, find_existing_file, float_value, int_value, optional_str, read_table


INDOOR_NODE_FILES = ("indoor_nodes.csv", "indoor_nodes.xlsx", "indoor_node.csv", "indoor_node.xlsx", "csv/indoor_nodes.csv", "csv/indoor_node.csv")
INDOOR_EDGE_FILES = ("indoor_edges.csv", "indoor_edges.xlsx", "indoor_edge.csv", "indoor_edge.xlsx", "csv/indoor_edges.csv", "csv/indoor_edge.csv")
ROOM_NODE_FILES = (
    "room_nearest_nodes.csv",
    "room_nearest_nodes.xlsx",
    "csv/room_nearest_nodes.csv",
    "rooms_positions.csv",
    "rooms_positions.xlsx",
    "csv/rooms_positions.csv",
    "room_positions.csv",
    "room_positions.xlsx",
)
BUILDING_LINK_EDGE_TYPES = {"bridge", "skybridge", "covered_bridge", "building_passage"}
VERTICAL_EDGE_TYPES = {"stair", "stairs", "elevator", "ramp", "vertical", *BUILDING_LINK_EDGE_TYPES}


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
        "indoor_nodes": [_normalize_indoor_node(row) for row in read_table(node_path)],
        "indoor_edges": [_normalize_indoor_edge(row) for row in read_table(edge_path)],
        "room_nodes": [_normalize_room_node(row) for row in read_table(room_node_path)] if room_node_path else [],
    }


def validate_week6_indoor_graph(db: Any, data_dir: Path) -> Week6IndoorGraphReport:
    from app.models import Building, IndoorMap, Room

    # import 전에 가능한 오류를 모두 모아 report로 반환.
    # 첫 오류에서 중단하지 않아야 DB 담당자가 한 번에 수정 가능.
    report = Week6IndoorGraphReport()
    data = load_week6_indoor_graph(data_dir)
    _enrich_indoor_graph_rows(db, data, report)
    report.stats = {key: len(rows) for key, rows in data.items()}
    _require_columns(report, "indoor_nodes", data["indoor_nodes"], ["indoor_node_id", "building_id", "indoor_map_id", "floor_number", "node_type", "x", "y"])
    _require_columns(report, "indoor_edges", data["indoor_edges"], ["indoor_edge_id", "indoor_map_id", "from_node_id", "to_node_id", "distance", "estimated_time", "edge_type"])
    if report.errors:
        return report

    building_ids = {building_id for (building_id,) in db.query(Building.building_id).all()}
    indoor_map_ids = {map_id for (map_id,) in db.query(IndoorMap.indoor_map_id).all()}
    room_by_id = {room.room_id: room for room in db.query(Room).all()}
    room_ids = set(room_by_id)
    node_ids = {row.get("indoor_node_id", "") for row in data["indoor_nodes"]}
    node_by_id = {row.get("indoor_node_id", ""): row for row in data["indoor_nodes"]}

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
        from_node = node_by_id.get(row.get("from_node_id", ""))
        to_node = node_by_id.get(row.get("to_node_id", ""))
        if not from_node:
            report.errors.append(f"Indoor edge has unknown from_node_id: {row.get('indoor_edge_id')} -> {row.get('from_node_id')}")
        if not to_node:
            report.errors.append(f"Indoor edge has unknown to_node_id: {row.get('indoor_edge_id')} -> {row.get('to_node_id')}")
        if not from_node or not to_node:
            continue
        edge_type = str(row.get("edge_type", "")).strip().lower()
        if from_node.get("building_id") != to_node.get("building_id") and edge_type not in BUILDING_LINK_EDGE_TYPES:
            # 일반 실내 간선의 건물 간 직접 연결은 차단. 구름다리/건물 통로처럼 명시된 연결만 허용.
            report.errors.append(f"Indoor edge connects different buildings: {row.get('indoor_edge_id')}")
        from_floor = int_value(from_node.get("floor_number"))
        to_floor = int_value(to_node.get("floor_number"))
        if from_floor != to_floor and edge_type not in VERTICAL_EDGE_TYPES:
            # 층이 바뀌는 간선은 계단/엘리베이터/램프/구름다리처럼 의미가 명확해야 함.
            report.errors.append(f"Cross-floor indoor edge must be stair/elevator/ramp: {row.get('indoor_edge_id')}")
        if (
            from_floor == to_floor
            and from_node.get("building_id") == to_node.get("building_id")
            and from_node.get("indoor_map_id") != to_node.get("indoor_map_id")
        ):
            report.errors.append(f"Same-floor indoor edge connects different indoor maps: {row.get('indoor_edge_id')}")

    unknown_room_node_ids = []
    for row in data["room_nodes"]:
        room_id = row.get("room_id", "")
        nearest = row.get("nearest_indoor_node_id", "")
        if room_id and room_id not in room_ids:
            unknown_room_node_ids.append(room_id)
            continue
        if nearest and nearest not in node_ids:
            report.errors.append(f"room_nodes references unknown nearest_indoor_node_id: {room_id} -> {nearest}")
        room = room_by_id.get(room_id)
        nearest_node = node_by_id.get(nearest)
        if room and nearest_node and room.building_id != nearest_node.get("building_id"):
            report.errors.append(f"room_nodes connects room to another building: {room_id} -> {nearest}")
        if room and nearest_node and room.floor_number != int_value(nearest_node.get("floor_number")):
            report.errors.append(f"room_nodes connects room to another floor: {room_id} -> {nearest}")
    if unknown_room_node_ids:
        report.warnings.append(
            "Skipped room_nodes for rooms not present in rooms_master: "
            f"{len(unknown_room_node_ids)} rows, e.g. {', '.join(unknown_room_node_ids[:10])}"
        )
    if not data["room_nodes"]:
        report.warnings.append("room_nearest_nodes.csv was not provided. Room-to-room routes need nearest_indoor_node_id.")
    _warn_isolated_indoor_nodes(report, data["indoor_nodes"], data["indoor_edges"])
    return report


def import_week6_indoor_graph(db: Any, data_dir: Path, replace: bool = False) -> Week6IndoorGraphReport:
    from app.models import IndoorEdge, IndoorNode, Room

    # 검증을 통과한 자료만 DB에 반영. 그래프 자료는 부분 import 시 경로 위험도 증가.
    report = validate_week6_indoor_graph(db, data_dir)
    if not report.ok:
        return report
    data = load_week6_indoor_graph(data_dir)
    _enrich_indoor_graph_rows(db, data, report)
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


def _normalize_indoor_node(row: dict[str, str]) -> dict[str, str]:
    normalized = dict(row)
    _copy_alias(normalized, "indoor_node_id", "node_id")
    _copy_alias(normalized, "floor_number", "floor")
    return normalized


def _normalize_indoor_edge(row: dict[str, str]) -> dict[str, str]:
    normalized = dict(row)
    _copy_alias(normalized, "indoor_edge_id", "edge_id")
    _copy_alias(normalized, "distance", "distance_m")
    _copy_alias(normalized, "estimated_time", "estimated_time_sec")
    edge_type = (normalized.get("edge_type") or "").lower()
    if edge_type == "stair" and not normalized.get("has_stairs"):
        normalized["has_stairs"] = "TRUE"
    if edge_type == "elevator" and not normalized.get("is_elevator"):
        normalized["is_elevator"] = "TRUE"
    if edge_type in BUILDING_LINK_EDGE_TYPES and not normalized.get("is_covered"):
        normalized["is_covered"] = "TRUE"
    return normalized


def _normalize_room_node(row: dict[str, str]) -> dict[str, str]:
    normalized = dict(row)
    _copy_alias(normalized, "nearest_indoor_node_id", "nearest_node_id")
    _copy_alias(normalized, "nearest_indoor_node_id", "node_id")
    return normalized


def _copy_alias(row: dict[str, str], target: str, *aliases: str) -> None:
    if row.get(target):
        return
    for alias in aliases:
        if row.get(alias):
            row[target] = row[alias]
            return


def _warn_isolated_indoor_nodes(
    report: Week6IndoorGraphReport,
    node_rows: list[dict[str, str]],
    edge_rows: list[dict[str, str]],
) -> None:
    # 고립 노드는 import를 막지는 않지만, 최종 readiness에서 PARTIAL 원인.
    connected_node_ids = {
        node_id
        for row in edge_rows
        for node_id in (row.get("from_node_id", ""), row.get("to_node_id", ""))
        if node_id
    }
    isolated = sorted(row.get("indoor_node_id", "") for row in node_rows if row.get("indoor_node_id") not in connected_node_ids)
    if isolated:
        report.warnings.append(f"Isolated indoor nodes: {', '.join(isolated[:10])}")


def _enrich_indoor_graph_rows(db: Any, data: dict[str, list[dict[str, str]]], report: Week6IndoorGraphReport) -> None:
    from app.models import IndoorMap

    # DB 파일이 floor_number만 제공해도 기존 indoor_maps 테이블에서 indoor_map_id 추론.
    map_lookup = {
        (building_id, int(floor_number)): indoor_map_id
        for indoor_map_id, building_id, floor_number in db.query(
            IndoorMap.indoor_map_id,
            IndoorMap.building_id,
            IndoorMap.floor_number,
        ).all()
    }

    for row in data["indoor_nodes"]:
        if not row.get("indoor_map_id") and row.get("building_id") and row.get("floor_number"):
            row["indoor_map_id"] = map_lookup.get((row["building_id"], int_value(row.get("floor_number"))), "")

    node_by_id = {row.get("indoor_node_id", ""): row for row in data["indoor_nodes"] if row.get("indoor_node_id")}
    for row in data["indoor_edges"]:
        from_node = node_by_id.get(row.get("from_node_id", ""))
        to_node = node_by_id.get(row.get("to_node_id", ""))
        if from_node and not row.get("indoor_map_id"):
            row["indoor_map_id"] = from_node.get("indoor_map_id", "")
        if from_node and to_node:
            # distance/estimated_time이 빠진 간선은 DCF 계산 가능하도록 좌표 기반 기본값 보정.
            if not row.get("distance"):
                row["distance"] = str(_estimate_distance(from_node, to_node, row.get("edge_type", "")))
            if not row.get("estimated_time"):
                row["estimated_time"] = str(_estimate_time(float_value(row.get("distance")), row.get("edge_type", "")))

    missing_map_nodes = [row.get("indoor_node_id", "") for row in data["indoor_nodes"] if not row.get("indoor_map_id")]
    if missing_map_nodes:
        report.errors.append(f"Indoor nodes could not infer indoor_map_id: {', '.join(missing_map_nodes[:10])}")


def _estimate_distance(from_node: dict[str, str], to_node: dict[str, str], edge_type: str) -> float:
    # 층간 간선은 같은 좌표에 있어도 실제 이동 거리 0 아님. 층 차이에 따른 최소 거리 적용.
    floor_delta = abs(int_value(to_node.get("floor_number")) - int_value(from_node.get("floor_number")))
    if floor_delta:
        return max(8.0 * floor_delta, hypot(float_value(to_node.get("x")) - float_value(from_node.get("x")), float_value(to_node.get("y")) - float_value(from_node.get("y"))))
    return hypot(float_value(to_node.get("x")) - float_value(from_node.get("x")), float_value(to_node.get("y")) - float_value(from_node.get("y")))


def _estimate_time(distance: float, edge_type: str) -> float:
    normalized = edge_type.lower()
    if normalized == "elevator":
        return max(10.0, distance / 1.0)
    if normalized == "stair":
        return max(6.0, distance / 0.8)
    return distance / 1.2 if distance else 0.0
