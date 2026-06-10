"""
Week 8 backend submission test.

단순 단위 테스트가 아니라 실제 FastAPI TestClient와 현재 DB 사용.
최종 발표/제출에 필요한 핵심 API와 경로 시나리오 동작 여부를 한 번에 확인.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine, ensure_sqlite_schema
from app.main import app
from app.algorithms.cost_function import build_route_cost_context
from app.algorithms.pathfinding import dijkstra_result, find_indoor_path, find_outdoor_path
from app.models import EntranceLink, IndoorEdge, IndoorMap, OutdoorEdge, Room
from app.services.route_geometry import edge_geometry_points


def main() -> None:
    # --strict는 DB 보완까지 완료된 상태 검증용.
    # 기본 모드는 코드 P0 동작 확인, 현재 DB의 PARTIAL 항목은 보고만 수행.
    parser = argparse.ArgumentParser(description="Run final backend P0 submission checks against the configured database.")
    parser.add_argument("--strict", action="store_true", help="Fail when readiness is PARTIAL as well as BLOCKED.")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()
    failures: list[str] = []

    _check_geometry_direction(failures)
    _check_blocked_edges(failures)
    with SessionLocal() as db:
        scenarios = _build_route_scenarios(db)
        missing_nearest_scenario = _build_missing_nearest_error_scenario(db)
        search_keyword, indoor_map_path = _build_public_api_examples(db)
        _check_pathfinding_wrappers(db, failures)

    with TestClient(app) as client:
        _check_get(client, "/", failures)
        _check_get(client, "/docs", failures)
        _check_get(client, "/api/buildings", failures)
        _check_get(client, "/api/reference-data", failures)
        _check_get(client, "/api/outdoor/map", failures)
        _check_get(client, "/maps/campus-map.png", failures)
        if search_keyword:
            _check_room_search(client, search_keyword, failures)
        if indoor_map_path:
            _check_get(client, indoor_map_path, failures)

        for scenario in scenarios:
            _check_route(client, scenario, failures)

        _check_error_contracts(client, missing_nearest_scenario, failures)

        readiness_response = client.get("/api/status/readiness")
        if readiness_response.status_code != 200:
            failures.append(f"readiness endpoint failed: HTTP {readiness_response.status_code}")
        else:
            readiness = readiness_response.json()
            print(f"readiness: {readiness['overallStatus']}")
            for check in readiness["checks"]:
                print(f"- [{check['status']}] {check['name']}: {check['message']}")
            if readiness["overallStatus"] == "BLOCKED" or args.strict and readiness["overallStatus"] != "READY":
                failures.append(f"readiness is {readiness['overallStatus']}")

    if failures:
        print("\nFAILED")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("\nAll required backend P0 submission checks passed.")


def _build_route_scenarios(db) -> list[dict]:
    # 테스트 대상 방은 하드코딩하지 않음.
    # 현재 DB에서 출입구 그래프와 실제로 연결된 방을 찾아 시연 가능한 경로 자동 구성.
    rooms = (
        db.query(Room)
        .filter(Room.building_id.in_(["DKU_ICT", "DKU_LIB"]), Room.nearest_indoor_node_id.is_not(None))
        .order_by(Room.building_id.asc(), Room.floor_number.asc(), Room.room_id.asc())
        .all()
    )
    by_building: dict[str, list[Room]] = defaultdict(list)
    by_building_floor: dict[tuple[str, int], list[Room]] = defaultdict(list)
    for room in rooms:
        by_building[room.building_id].append(room)
        by_building_floor[(room.building_id, room.floor_number)].append(room)

    routable_by_building = _entrance_reachable_rooms(db, by_building)
    scenarios: list[dict] = []
    for building_id in ("DKU_ICT", "DKU_LIB"):
        same_floor_rooms = next((items for (candidate, _), items in by_building_floor.items() if candidate == building_id and len(items) >= 2), [])
        if same_floor_rooms:
            scenarios.append({
                "name": f"{building_id} same-floor indoor",
                "path": "/api/routes/indoor",
                "payload": {"fromRoomId": same_floor_rooms[0].room_id, "toRoomId": same_floor_rooms[1].room_id, "routeType": "DEFAULT", "preferences": {}},
                "require_vertical": False,
            })

        building_rooms = routable_by_building.get(building_id, [])
        if building_rooms:
            lowest = min(building_rooms, key=lambda room: room.floor_number)
            highest = max(building_rooms, key=lambda room: room.floor_number)
            if lowest.floor_number != highest.floor_number:
                scenarios.append({
                    "name": f"{building_id} multi-floor indoor",
                    "path": "/api/routes/indoor",
                    "payload": {"fromRoomId": lowest.room_id, "toRoomId": highest.room_id, "routeType": "DEFAULT", "preferences": {}},
                    "require_vertical": True,
                })

    ict_room = next(iter(routable_by_building.get("DKU_ICT", [])), None)
    lib_room = next(iter(routable_by_building.get("DKU_LIB", [])), None)
    if ict_room and lib_room:
        for start, destination, label in (
            (ict_room, lib_room, "ICT to LIB integrated"),
            (lib_room, ict_room, "LIB to ICT integrated"),
        ):
            scenarios.append({
                "name": label,
                "path": "/api/routes",
                "payload": {
                    "start": start.room_code,
                    "destination": destination.room_code,
                    "routeTypes": ["DEFAULT", "COMFORTABLE", "RAINY"],
                    "preferences": {},
                },
                "require_outdoor": True,
            })
    return scenarios


def _build_public_api_examples(db) -> tuple[str | None, str | None]:
    room = db.query(Room).order_by(Room.room_id.asc()).first()
    indoor_map = db.query(IndoorMap).order_by(IndoorMap.indoor_map_id.asc()).first()
    search_keyword = room.room_code if room else None
    indoor_map_path = (
        f"/api/buildings/{indoor_map.building_id}/floors/{indoor_map.floor_number}/indoor-map"
        if indoor_map
        else None
    )
    return search_keyword, indoor_map_path


def _entrance_reachable_rooms(db, by_building: dict[str, list[Room]]) -> dict[str, list[Room]]:
    edges = db.query(IndoorEdge).all()
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        adjacency[edge.from_node_id].add(edge.to_node_id)
        if edge.is_bidirectional:
            adjacency[edge.to_node_id].add(edge.from_node_id)

    result: dict[str, list[Room]] = {}
    for building_id, rooms in by_building.items():
        entrance_nodes = {
            link.indoor_node_id
            for link in db.query(EntranceLink).filter(EntranceLink.building_id == building_id).all()
        }
        reachable = _reachable_nodes(entrance_nodes, adjacency)
        result[building_id] = [room for room in rooms if room.nearest_indoor_node_id in reachable]
    return result


def _reachable_nodes(start_nodes: set[str], adjacency: dict[str, set[str]]) -> set[str]:
    seen = set(start_nodes)
    stack = list(start_nodes)
    while stack:
        current = stack.pop()
        for neighbor in adjacency.get(current, set()):
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return seen


def _check_get(client: TestClient, path: str, failures: list[str]) -> None:
    response = client.get(path)
    print(f"GET {path}: {response.status_code}")
    if response.status_code != 200:
        failures.append(f"GET {path} returned HTTP {response.status_code}")


def _check_room_search(client: TestClient, keyword: str, failures: list[str]) -> None:
    response = client.get("/api/rooms/search", params={"keyword": keyword})
    print(f"GET /api/rooms/search?keyword={keyword}: {response.status_code}")
    if response.status_code != 200:
        failures.append(f"room search returned HTTP {response.status_code}")
        return
    payload = response.json()
    if not payload.get("roomId") or not payload.get("indoorMap"):
        failures.append("room search response is missing roomId or indoorMap")


def _check_route(client: TestClient, scenario: dict, failures: list[str]) -> None:
    # HTTP 200뿐 아니라 프론트가 그릴 수 있는 segments/pathPoints 구조인지 함께 확인.
    response = client.post(scenario["path"], json=scenario["payload"])
    print(f"{scenario['name']}: {response.status_code}")
    if response.status_code != 200:
        failures.append(f"{scenario['name']} returned HTTP {response.status_code}: {response.text[:200]}")
        return

    routes = response.json()
    if not isinstance(routes, list):
        routes = [routes]
    for route in routes:
        segments = route.get("segments", [])
        segment_types = [segment.get("type") for segment in segments]
        print(f"  {route.get('routeType')}: {segment_types}")
        if not segments:
            failures.append(f"{scenario['name']} returned no segments")
            continue
        if scenario.get("require_vertical") and "VERTICAL" not in segment_types:
            failures.append(f"{scenario['name']} did not return a VERTICAL segment")
        if scenario.get("require_outdoor") and "OUTDOOR" not in segment_types:
            failures.append(f"{scenario['name']} did not return an OUTDOOR segment")
        for segment in segments:
            points = segment.get("pathPoints", [])
            if not points:
                failures.append(f"{scenario['name']} has an empty {segment.get('type')} pathPoints")
            if segment.get("type") == "INDOOR":
                map_id = segment.get("indoorMapId")
                if any(point.get("indoorMapId") != map_id for point in points):
                    failures.append(f"{scenario['name']} INDOOR segment contains points from another map")
            if segment.get("type") == "VERTICAL" and segment.get("floorNumber") == segment.get("toFloorNumber"):
                failures.append(f"{scenario['name']} VERTICAL segment does not change floors")


def _check_geometry_direction(failures: list[str]) -> None:
    # 같은 outdoor edge를 역방향으로 통과할 때 polyline 좌표도 반전 필요. 실제 이동 방향 일치 확인.
    edge = SimpleNamespace(
        outdoor_edge_id="TEST_EDGE",
        from_node_id="A",
        to_node_id="B",
        polyline_points='[[0,0],[5,4],[10,10]]',
    )
    node_a = SimpleNamespace(outdoor_node_id="A", map_x=0, map_y=0, latitude=None, longitude=None)
    node_b = SimpleNamespace(outdoor_node_id="B", map_x=10, map_y=10, latitude=None, longitude=None)
    forward = edge_geometry_points(edge, node_a, node_b)
    reverse = edge_geometry_points(edge, node_b, node_a)
    if [(point.x, point.y) for point in forward] != list(reversed([(point.x, point.y) for point in reverse])):
        failures.append("polyline_points reverse traversal is incorrect")
    else:
        print("polyline_points direction check: passed")


def _check_blocked_edges(failures: list[str]) -> None:
    # 접근성 모드에서 계단 간선은 단순 고비용이 아니라 탐색 후보에서 제외되어야 함.
    nodes = [SimpleNamespace(node_id=node_id) for node_id in ("A", "B", "C")]
    blocked = SimpleNamespace(
        edge_id="BLOCKED",
        from_node_id="A",
        to_node_id="B",
        is_bidirectional=True,
        distance=1,
        estimated_time=1,
        is_accessible=False,
        has_stairs=True,
    )
    allowed_first = SimpleNamespace(
        edge_id="ALLOWED_1",
        from_node_id="A",
        to_node_id="C",
        is_bidirectional=True,
        distance=5,
        estimated_time=5,
        is_accessible=True,
        has_stairs=False,
    )
    allowed_second = SimpleNamespace(
        edge_id="ALLOWED_2",
        from_node_id="C",
        to_node_id="B",
        is_bidirectional=True,
        distance=5,
        estimated_time=5,
        is_accessible=True,
        has_stairs=False,
    )
    context = build_route_cost_context("COMFORTABLE", {"accessibilityMode": True})
    result = dijkstra_result(nodes, [blocked, allowed_first, allowed_second], "A", "B", context=context)
    if result.node_ids != ["A", "C", "B"]:
        failures.append("accessibility mode did not exclude a blocked stairs edge")
    else:
        print("blocked/accessibility edge exclusion: passed")


def _build_missing_nearest_error_scenario(db) -> dict | None:
    missing_room = (
        db.query(Room)
        .filter(Room.nearest_indoor_node_id.is_(None))
        .order_by(Room.room_id.asc())
        .first()
    )
    if not missing_room:
        return None
    destination = (
        db.query(Room)
        .filter(
            Room.building_id == missing_room.building_id,
            Room.nearest_indoor_node_id.is_not(None),
        )
        .order_by(Room.room_id.asc())
        .first()
    )
    if not destination:
        return None
    return {
        "fromRoomId": missing_room.room_id,
        "toRoomId": destination.room_id,
        "routeType": "DEFAULT",
        "preferences": {},
    }


def _check_pathfinding_wrappers(db, failures: list[str]) -> None:
    indoor_edge = db.query(IndoorEdge).order_by(IndoorEdge.indoor_edge_id.asc()).first()
    if indoor_edge:
        path = find_indoor_path(
            indoor_edge.indoor_map_id,
            indoor_edge.from_node_id,
            indoor_edge.to_node_id,
            db=db,
        )
        if not path or path[0] != indoor_edge.from_node_id or path[-1] != indoor_edge.to_node_id:
            failures.append("DB-backed find_indoor_path compatibility wrapper failed")
        else:
            print("find_indoor_path compatibility wrapper: passed")

    outdoor_edge = db.query(OutdoorEdge).order_by(OutdoorEdge.outdoor_edge_id.asc()).first()
    if outdoor_edge:
        path = find_outdoor_path(outdoor_edge.from_node_id, outdoor_edge.to_node_id, db=db)
        if not path or path[0] != outdoor_edge.from_node_id or path[-1] != outdoor_edge.to_node_id:
            failures.append("DB-backed find_outdoor_path compatibility wrapper failed")
        else:
            print("find_outdoor_path compatibility wrapper: passed")


def _check_error_contracts(client: TestClient, missing_nearest_scenario: dict | None, failures: list[str]) -> None:
    # 프론트 사용자 메시지 표시를 위해 실패 상황도 구조화된 errorCode 반환 필요.
    missing_room = client.post(
        "/api/routes/indoor",
        json={
            "fromRoomId": "__MISSING_ROOM__",
            "toRoomId": "__MISSING_ROOM__",
            "routeType": "DEFAULT",
            "preferences": {},
        },
    )
    _assert_error_code(missing_room, "FROM_ROOM_NOT_FOUND", "missing room error", failures)

    empty_keyword = client.post(
        "/api/routes",
        json={
            "start": "",
            "destination": "",
            "routeTypes": ["DEFAULT"],
            "preferences": {},
        },
    )
    _assert_error_code(empty_keyword, "START_EMPTY_KEYWORD", "empty route keyword error", failures)

    if missing_nearest_scenario:
        missing_nearest = client.post("/api/routes/indoor", json=missing_nearest_scenario)
        _assert_error_code(missing_nearest, "FROM_ROOM_NEAREST_NODE_NOT_FOUND", "missing nearest node error", failures)


def _assert_error_code(response, expected_code: str, label: str, failures: list[str]) -> None:
    print(f"{label}: {response.status_code}")
    if response.status_code != 404:
        failures.append(f"{label} returned HTTP {response.status_code}, expected 404")
        return
    detail = response.json().get("detail", {})
    if "errors" in detail:
        actual_codes = {item.get("errorCode") for item in detail["errors"]}
    else:
        actual_codes = {detail.get("errorCode")}
    if expected_code not in actual_codes:
        failures.append(f"{label} returned {actual_codes}, expected {expected_code}")


if __name__ == "__main__":
    main()
