"""
Week 8 readiness checks.

이 모듈은 서버가 실행되는지만 확인하는 health check가 아니라,
최종 시연에 필요한 DB 연결 상태를 사람이 판단할 수 있는 형태로 진단.
READY/PARTIAL/BLOCKED 분리로 코드 문제와 DB 자료 보완 문제 구분.
"""

from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    Building,
    EdgeType,
    EmailVerification,
    EntranceLink,
    EntranceMaster,
    IndoorEdge,
    IndoorMap,
    IndoorNode,
    IndoorNodeType,
    OutdoorEdge,
    OutdoorNode,
    Report,
    Room,
    RoomCategory,
    RoomPosition,
    TmiLocation,
    User,
)


@dataclass
class ReadinessCheck:
    name: str
    status: str
    message: str
    requiredAction: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


def build_week8_readiness_report(db: Session) -> dict:
    # 각 check는 독립 실행. 하나가 PARTIAL이어도 나머지 READY 항목은 그대로 노출해 원인 분리 가능.
    checks = [
        _check_master_data(db),
        _check_reference_tables(db),
        _check_room_positions(db),
        _check_room_nearest_nodes(db),
        _check_indoor_graph(db),
        _check_outdoor_graph(db),
        _check_entrance_links(db),
        _check_submission_route_coverage(db),
        _check_auth_tables(db),
        _check_tmi_report_tables(db),
    ]
    statuses = {check.status for check in checks}
    if "BLOCKED" in statuses:
        overall_status = "BLOCKED"
    elif "PARTIAL" in statuses:
        overall_status = "PARTIAL"
    else:
        overall_status = "READY"
    return {"overallStatus": overall_status, "checks": [asdict(check) for check in checks]}


def _check_master_data(db: Session) -> ReadinessCheck:
    building_count = db.query(Building).count()
    room_count = db.query(Room).count()
    indoor_map_count = db.query(IndoorMap).count()
    if building_count and room_count and indoor_map_count:
        return ReadinessCheck("기본 건물/강의실/층별 지도 데이터", "READY", "기본 데이터가 존재합니다.", details={"buildings": building_count, "rooms": room_count, "indoorMaps": indoor_map_count})
    return ReadinessCheck("기본 건물/강의실/층별 지도 데이터", "BLOCKED", "건물, 강의실, 층별 지도 중 일부 데이터가 없습니다.", "Building_Master, rooms_master, floor_pdf_inventory 자료를 import해야 합니다.", {"buildings": building_count, "rooms": room_count, "indoorMaps": indoor_map_count})


def _check_reference_tables(db: Session) -> ReadinessCheck:
    # GitHub DB 브랜치의 분류/참조 CSV import 여부 확인.
    counts = {
        "edgeTypes": db.query(EdgeType).count(),
        "indoorNodeTypes": db.query(IndoorNodeType).count(),
        "roomCategories": db.query(RoomCategory).count(),
        "entranceMaster": db.query(EntranceMaster).count(),
    }
    missing = [name for name, count in counts.items() if count == 0]
    if not missing:
        return ReadinessCheck("DB 참조 테이블", "READY", "간선, 실내 노드, 공간 분류, 출입구 참조 데이터가 준비되어 있습니다.", details=counts)
    return ReadinessCheck(
        "DB 참조 테이블",
        "PARTIAL",
        "일부 참조 테이블이 비어 있습니다.",
        "edge_types, indoor_node_types, room_categories, entrance_master 자료를 import하면 분류/출입구 표시 품질을 높일 수 있습니다.",
        {"counts": counts, "missing": missing},
    )


def _check_room_positions(db: Session) -> ReadinessCheck:
    room_ids = {room_id for (room_id,) in db.query(Room.room_id).all()}
    positioned_room_ids = {room_id for (room_id,) in db.query(RoomPosition.room_id).all()}
    missing = sorted(room_ids - positioned_room_ids)
    if not room_ids:
        return ReadinessCheck("강의실 좌표 데이터", "BLOCKED", "강의실 데이터가 없어 좌표 연결을 확인할 수 없습니다.", "rooms_master를 먼저 import해야 합니다.")
    if not missing:
        return ReadinessCheck("강의실 좌표 데이터", "READY", "모든 강의실에 좌표가 연결되어 있습니다.", details={"rooms": len(room_ids), "missingRoomPositions": 0})
    return ReadinessCheck("강의실 좌표 데이터", "PARTIAL", "일부 강의실에 지도 위 좌표가 없습니다.", "room_positions 자료를 보완해야 합니다.", {"rooms": len(room_ids), "missingRoomPositions": len(missing), "examples": missing[:10]})


def _check_room_nearest_nodes(db: Session) -> ReadinessCheck:
    # nearest_indoor_node_id는 강의실 위치 데이터와 실제 경로 그래프를 잇는 핵심 연결점.
    # 값이 없거나 다른 건물/층 노드를 가리키면 해당 강의실은 길찾기 사용 불가.
    rooms = db.query(Room).all()
    node_by_id = {node.indoor_node_id: node for node in db.query(IndoorNode).all()}
    missing = sorted(room.room_id for room in rooms if not room.nearest_indoor_node_id)
    unknown = sorted(room.room_id for room in rooms if room.nearest_indoor_node_id and room.nearest_indoor_node_id not in node_by_id)
    wrong_building = sorted(
        room.room_id
        for room in rooms
        if room.nearest_indoor_node_id in node_by_id and node_by_id[room.nearest_indoor_node_id].building_id != room.building_id
    )
    wrong_floor = sorted(
        room.room_id
        for room in rooms
        if room.nearest_indoor_node_id in node_by_id and node_by_id[room.nearest_indoor_node_id].floor_number != room.floor_number
    )
    if not rooms:
        return ReadinessCheck("강의실-실내 노드 연결", "BLOCKED", "강의실 데이터가 없습니다.", "rooms_master를 먼저 import해야 합니다.")
    if unknown or wrong_building or wrong_floor:
        return ReadinessCheck(
            "강의실-실내 노드 연결",
            "BLOCKED",
            "잘못된 nearest_indoor_node_id 연결이 있습니다.",
            "room_nearest_nodes의 노드 ID, 건물, 층 연결을 수정해야 합니다.",
            {
                "rooms": len(rooms),
                "unknownNearestNodes": len(unknown),
                "wrongBuildingLinks": len(wrong_building),
                "wrongFloorLinks": len(wrong_floor),
                "examples": (unknown + wrong_building + wrong_floor)[:10],
            },
        )
    if not missing:
        return ReadinessCheck("강의실-실내 노드 연결", "READY", "모든 강의실이 실내 노드와 연결되어 있습니다.", details={"rooms": len(rooms), "missingNearestNodes": 0})
    return ReadinessCheck("강의실-실내 노드 연결", "PARTIAL", "일부 강의실에 nearest_indoor_node_id가 없습니다.", "room_nearest_nodes 자료를 보완해야 합니다.", {"rooms": len(rooms), "missingNearestNodes": len(missing), "examples": missing[:10]})


def _check_indoor_graph(db: Session) -> ReadinessCheck:
    # 실내 그래프는 건물 안에서 복도, 계단, 엘리베이터가 모두 연결되어 있어야 함.
    # 고립 노드가 있으면 특정 강의실이나 출입구로 이동 불가.
    nodes = db.query(IndoorNode).all()
    edges = db.query(IndoorEdge).all()
    node_ids = {node.indoor_node_id for node in nodes}
    bad_edges = [edge.indoor_edge_id for edge in edges if edge.from_node_id not in node_ids or edge.to_node_id not in node_ids]
    if not nodes or not edges:
        return ReadinessCheck("실내 경로 그래프", "BLOCKED", "실내 노드 또는 간선 데이터가 부족합니다.", "indoor_nodes, indoor_edges 자료를 import해야 합니다.", {"indoorNodes": len(nodes), "indoorEdges": len(edges)})
    if bad_edges:
        return ReadinessCheck("실내 경로 그래프", "BLOCKED", "존재하지 않는 실내 노드를 참조하는 간선이 있습니다.", "indoor_edges의 from_node_id/to_node_id를 수정해야 합니다.", {"badEdgeExamples": bad_edges[:10]})
    adjacency = _adjacency(edges)
    isolated = sorted(node_id for node_id in node_ids if not adjacency.get(node_id))
    components_by_building = {
        building_id: _component_count(
            {node.indoor_node_id for node in nodes if node.building_id == building_id},
            adjacency,
        )
        for building_id in sorted({node.building_id for node in nodes})
    }
    disconnected_buildings = {building_id: count for building_id, count in components_by_building.items() if count > 1}
    if isolated or disconnected_buildings:
        return ReadinessCheck(
            "실내 경로 그래프",
            "PARTIAL",
            "실내 그래프에 고립 노드 또는 분리된 연결 요소가 있습니다.",
            "indoor_nodes/indoor_edges 연결을 검수해야 합니다.",
            {
                "indoorNodes": len(nodes),
                "indoorEdges": len(edges),
                "isolatedNodes": len(isolated),
                "isolatedExamples": isolated[:10],
                "componentsByBuilding": components_by_building,
            },
        )
    return ReadinessCheck("실내 경로 그래프", "READY", "실내 노드와 간선 연결 상태가 정상입니다.", details={"indoorNodes": len(nodes), "indoorEdges": len(edges), "componentsByBuilding": components_by_building})


def _check_outdoor_graph(db: Session) -> ReadinessCheck:
    # 연결성은 경로 계산 가능 여부, polyline coverage는 지도 표시 품질 의미.
    # 그래프가 끊기면 BLOCKED, 상세 좌표만 부족하면 PARTIAL로 분리.
    nodes = db.query(OutdoorNode).all()
    edges = db.query(OutdoorEdge).all()
    node_ids = {node.outdoor_node_id for node in nodes}
    bad_edges = [edge.outdoor_edge_id for edge in edges if edge.from_node_id not in node_ids or edge.to_node_id not in node_ids]
    if not nodes or not edges:
        return ReadinessCheck("외부 경로 그래프", "BLOCKED", "외부 노드 또는 간선 데이터가 부족합니다.", "outdoor_nodes, outdoor_edges 자료를 import해야 합니다.", {"outdoorNodes": len(nodes), "outdoorEdges": len(edges)})
    if bad_edges:
        return ReadinessCheck("외부 경로 그래프", "BLOCKED", "존재하지 않는 외부 노드를 참조하는 간선이 있습니다.", "outdoor_edges의 from_node_id/to_node_id를 수정해야 합니다.", {"badEdgeExamples": bad_edges[:10]})
    adjacency = _adjacency(edges)
    isolated = sorted(node_id for node_id in node_ids if not adjacency.get(node_id))
    components = _component_count(node_ids, adjacency)
    polyline_edges = sum(1 for edge in edges if edge.polyline_points)
    details = {
        "outdoorNodes": len(nodes),
        "outdoorEdges": len(edges),
        "isolatedNodes": len(isolated),
        "isolatedExamples": isolated[:10],
        "connectedComponents": components,
        "polylineEdges": polyline_edges,
        "polylineCoveragePercent": round(polyline_edges / len(edges) * 100, 1) if edges else 0,
    }
    if isolated or components > 1:
        return ReadinessCheck(
            "외부 경로 그래프",
            "BLOCKED",
            "외부 그래프에 고립 노드 또는 분리된 경로가 있습니다.",
            "outdoor_nodes/outdoor_edges 연결을 수정해야 합니다.",
            details,
        )
    if polyline_edges < len(edges):
        return ReadinessCheck(
            "외부 경로 그래프",
            "PARTIAL",
            "외부 경로 계산은 가능하지만 일부 간선에 상세 곡선 좌표가 없습니다.",
            "곡선 보행로 간선에 polyline_points를 추가하면 실제 길 형태로 표시할 수 있습니다.",
            details,
        )
    return ReadinessCheck("외부 경로 그래프", "READY", "외부 그래프와 상세 경로 좌표가 정상입니다.", details=details)


def _check_entrance_links(db: Session) -> ReadinessCheck:
    # entrance_links는 실내 그래프와 외부 그래프를 연결하는 bridge table.
    # 이 값이 틀리면 통합 경로가 실제 건물 출입 층과 불일치.
    links = db.query(EntranceLink).all()
    building_ids = {building_id for (building_id,) in db.query(Building.building_id).all()}
    indoor_node_ids = {node_id for (node_id,) in db.query(IndoorNode.indoor_node_id).all()}
    outdoor_node_ids = {node_id for (node_id,) in db.query(OutdoorNode.outdoor_node_id).all()}
    indoor_node_by_id = {node.indoor_node_id: node for node in db.query(IndoorNode).all()}
    outdoor_edges = db.query(OutdoorEdge).all()
    indoor_edges = db.query(IndoorEdge).all()
    outdoor_adjacency = _adjacency(outdoor_edges)
    indoor_adjacency = _adjacency(indoor_edges)
    bad_links = [link.link_id for link in links if link.building_id not in building_ids or link.indoor_node_id not in indoor_node_ids or link.outdoor_node_id not in outdoor_node_ids]
    wrong_building = [
        link.link_id
        for link in links
        if link.indoor_node_id in indoor_node_by_id and indoor_node_by_id[link.indoor_node_id].building_id != link.building_id
    ]
    wrong_floor = [
        link.link_id
        for link in links
        if link.floor_number is not None
        and link.indoor_node_id in indoor_node_by_id
        and indoor_node_by_id[link.indoor_node_id].floor_number != link.floor_number
    ]
    isolated_links = [
        link.link_id
        for link in links
        if not outdoor_adjacency.get(link.outdoor_node_id) or not indoor_adjacency.get(link.indoor_node_id)
    ]
    if not links:
        return ReadinessCheck("건물 출입구 연결", "BLOCKED", "실내 출입구와 외부 노드 연결 데이터가 없습니다.", "entrance_links 자료를 import해야 합니다.")
    if bad_links or wrong_building or wrong_floor or isolated_links:
        return ReadinessCheck(
            "건물 출입구 연결",
            "BLOCKED",
            "잘못되거나 경로 그래프에서 고립된 출입구 연결이 있습니다.",
            "entrance_links의 건물, 층, 실내·외부 노드 연결을 수정해야 합니다.",
            {
                "badReferences": bad_links[:10],
                "wrongBuildingLinks": wrong_building[:10],
                "wrongFloorLinks": wrong_floor[:10],
                "isolatedLinks": isolated_links[:10],
            },
        )
    return ReadinessCheck("건물 출입구 연결", "READY", "건물 출입구 연결 참조가 정상입니다.", details={"entranceLinks": len(links)})


def _check_submission_route_coverage(db: Session) -> ReadinessCheck:
    # 최종 시연 범위가 ICT관/도서관으로 좁혀져 있으므로 두 건물의 실사용 가능성 별도 점검.
    supported_buildings = {"DKU_ICT", "DKU_LIB"}
    existing_buildings = {building_id for (building_id,) in db.query(Building.building_id).all()}
    missing_buildings = sorted(supported_buildings - existing_buildings)
    routable_rooms = {
        building_id: db.query(Room).filter(Room.building_id == building_id, Room.nearest_indoor_node_id.is_not(None)).count()
        for building_id in supported_buildings
    }
    entrance_counts = {
        building_id: db.query(EntranceLink).filter(EntranceLink.building_id == building_id).count()
        for building_id in supported_buildings
    }
    indoor_adjacency = _adjacency(db.query(IndoorEdge).all())
    unreachable_rooms: dict[str, list[str]] = {}
    for building_id in supported_buildings:
        entrance_nodes = {
            link.indoor_node_id
            for link in db.query(EntranceLink).filter(EntranceLink.building_id == building_id).all()
        }
        reachable_nodes = _reachable_nodes(entrance_nodes, indoor_adjacency)
        unreachable_rooms[building_id] = sorted(
            room.room_id
            for room in db.query(Room).filter(Room.building_id == building_id, Room.nearest_indoor_node_id.is_not(None)).all()
            if room.nearest_indoor_node_id not in reachable_nodes
        )
    if missing_buildings or any(count == 0 for count in routable_rooms.values()) or any(count == 0 for count in entrance_counts.values()):
        return ReadinessCheck(
            "최종 시연 경로 범위",
            "BLOCKED",
            "ICT관·도서관 시연에 필요한 건물, 강의실 노드 또는 출입구 자료가 부족합니다.",
            "ICT관·도서관의 room_nearest_nodes와 entrance_links를 보완해야 합니다.",
            {"missingBuildings": missing_buildings, "routableRooms": routable_rooms, "entranceLinks": entrance_counts},
        )
    if any(unreachable_rooms.values()):
        return ReadinessCheck(
            "최종 시연 경로 범위",
            "PARTIAL",
            "일부 강의실이 건물 출입구와 연결된 실내 그래프에 포함되지 않습니다.",
            "해당 층의 계단·엘리베이터 간선 또는 출입구 연결을 보완해야 합니다.",
            {
                "routableRooms": routable_rooms,
                "entranceLinks": entrance_counts,
                "unreachableRoomCounts": {building_id: len(room_ids) for building_id, room_ids in unreachable_rooms.items()},
                "examples": {building_id: room_ids[:10] for building_id, room_ids in unreachable_rooms.items() if room_ids},
            },
        )
    return ReadinessCheck(
        "최종 시연 경로 범위",
        "READY",
        "ICT관·도서관 통합 경로 계산에 필요한 기본 자료가 존재합니다.",
        details={"routableRooms": routable_rooms, "entranceLinks": entrance_counts},
    )


def _check_auth_tables(db: Session) -> ReadinessCheck:
    return ReadinessCheck(
        "사용자 인증 테이블",
        "READY",
        "회원가입, 로그인, JWT, 이메일 인증 테이블이 준비되어 있습니다.",
        details={"users": db.query(User).count(), "emailVerifications": db.query(EmailVerification).count()},
    )


def _check_tmi_report_tables(db: Session) -> ReadinessCheck:
    return ReadinessCheck(
        "TMI/제보 테이블",
        "READY",
        "TMI 위치와 사용자 제보 테이블이 준비되어 있습니다.",
        details={"tmiLocations": db.query(TmiLocation).count(), "reports": db.query(Report).count()},
    )


def _adjacency(edges: list[Any]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        from_node_id = str(edge.from_node_id)
        to_node_id = str(edge.to_node_id)
        adjacency.setdefault(from_node_id, set()).add(to_node_id)
        if getattr(edge, "is_bidirectional", True):
            adjacency.setdefault(to_node_id, set()).add(from_node_id)
        else:
            adjacency.setdefault(to_node_id, set())
    return adjacency


def _component_count(node_ids: set[str], adjacency: dict[str, set[str]]) -> int:
    # 연결 요소 개수는 그래프가 몇 덩어리로 끊어져 있는지 확인용.
    remaining = set(node_ids)
    count = 0
    while remaining:
        count += 1
        stack = [remaining.pop()]
        while stack:
            current = stack.pop()
            for neighbor in adjacency.get(current, set()):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
    return count


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
