from sqlalchemy.orm import Session

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
    RouteWeightProfile,
)


def seed_database(db: Session) -> None:
    """Seed only the week 3 pilot data.

    The pilot verifies this flow:
    소프트305 -> SOFT_ICT -> 3F indoor map -> room position highlight.
    """
    # 이미 데이터가 있으면 중복 입력을 막기 위해 seed를 건너뛴다.
    if db.query(Building).first():
        return

    # 3주차 검증에 필요한 대표 건물과 출발지 샘플을 만든다.
    soft = Building(
        building_id="SOFT_ICT",
        name="소프트웨어 ICT관",
        short_code="소프트",
        latitude=37.3211,
        longitude=127.1265,
        main_outdoor_node_id="OUT_SOFT_ICT_ENTRANCE_MAIN",
        description="3주차 파일럿 대상 건물",
    )
    library = Building(
        building_id="LIBRARY",
        name="퇴계기념중앙도서관",
        short_code="도서관",
        latitude=37.3221,
        longitude=127.1261,
        main_outdoor_node_id="OUT_LIBRARY_ENTRANCE_MAIN",
        description="대표 출발지 샘플",
    )
    db.add_all([soft, library])

    # resolver.py가 건물 약칭을 정식 건물로 찾을 수 있게 별칭을 넣는다.
    db.add_all(
        [
            BuildingAlias(building_id="SOFT_ICT", alias="소프트", priority=1),
            BuildingAlias(building_id="SOFT_ICT", alias="소프트웨어", priority=2),
            BuildingAlias(building_id="SOFT_ICT", alias="ICT", priority=3),
            BuildingAlias(building_id="LIBRARY", alias="도서관", priority=1),
            BuildingAlias(building_id="LIBRARY", alias="퇴계", priority=2),
        ]
    )

    indoor_map = IndoorMap(
        indoor_map_id="MAP_SOFT_ICT_3F",
        building_id="SOFT_ICT",
        floor_number=3,
        floor_label="3F",
        source_pdf_name="soft_ict_3f_evacuation.pdf",
        map_file_url="/maps/soft_ict_3f.svg",
        canvas_width=1000,
        canvas_height=700,
        version="pilot-v1",
        status="draft",
    )
    db.add(indoor_map)

    # 소프트305 검색 결과에 연결될 강의실과 지도 좌표이다.
    room = Room(
        room_id="ROOM_SOFT_ICT_305",
        building_id="SOFT_ICT",
        indoor_map_id="MAP_SOFT_ICT_3F",
        room_code="소프트305",
        room_number="305",
        floor_number=3,
        room_type="LECTURE",
        nearest_indoor_node_id="SOFT_ICT_3F_CORRIDOR_01",
        description="소프트웨어 ICT관 3층 305호",
    )
    db.add(room)
    db.add(
        RoomPosition(
            position_id="POS_SOFT_ICT_305",
            room_id="ROOM_SOFT_ICT_305",
            indoor_map_id="MAP_SOFT_ICT_3F",
            x=420,
            y=180,
            width=80,
            height=45,
            polygon_points=None,
            center_x=460,
            center_y=202.5,
        )
    )

    db.add_all(
        [
            # 실내 경로선 검증을 위한 최소 노드 샘플이다.
            IndoorNode(
                indoor_node_id="SOFT_ICT_3F_ENTRANCE_01",
                building_id="SOFT_ICT",
                indoor_map_id="MAP_SOFT_ICT_3F",
                floor_number=3,
                node_type="INDOOR_ENTRANCE",
                x=160,
                y=250,
                label="3층 출입구",
            ),
            IndoorNode(
                indoor_node_id="SOFT_ICT_3F_CORRIDOR_01",
                building_id="SOFT_ICT",
                indoor_map_id="MAP_SOFT_ICT_3F",
                floor_number=3,
                node_type="CORRIDOR_JUNCTION",
                x=420,
                y=230,
                label="305호 앞 복도 기준점",
            ),
        ]
    )
    db.add(
        # 5주차 실내 Dijkstra 구현 전까지 구조 검증용으로 쓰는 간선이다.
        IndoorEdge(
            indoor_edge_id="IN_EDGE_SOFT_ICT_3F_001",
            indoor_map_id="MAP_SOFT_ICT_3F",
            from_node_id="SOFT_ICT_3F_ENTRANCE_01",
            to_node_id="SOFT_ICT_3F_CORRIDOR_01",
            distance=35,
            estimated_time=0.8,
            edge_type="INDOOR_HALLWAY",
            has_stairs=False,
            has_slope=False,
            is_indoor=True,
            is_covered=True,
            is_accessible=True,
            complexity_level=1,
            description="3주차 더미 실내 경로선 검증용 간선",
        )
    )

    db.add(
        # 실외-실내 연결을 위한 대표 입구 노드 샘플이다.
        OutdoorNode(
            outdoor_node_id="OUT_SOFT_ICT_ENTRANCE_MAIN",
            node_type="BUILDING_ENTRANCE",
            building_id="SOFT_ICT",
            latitude=37.3211,
            longitude=127.1265,
            label="소프트웨어 ICT관 정문",
        )
    )
    db.add(
        # 실외 입구와 실내 출입구를 연결하는 샘플 링크이다.
        EntranceLink(
            link_id="LINK_SOFT_ICT_MAIN_3F",
            building_id="SOFT_ICT",
            outdoor_node_id="OUT_SOFT_ICT_ENTRANCE_MAIN",
            indoor_node_id="SOFT_ICT_3F_ENTRANCE_01",
            entrance_name="정문",
            is_main=True,
        )
    )

    db.add_all(
        [
            # 6주차 경로 옵션 계산에 사용할 기본 가중치 프로필이다.
            RouteWeightProfile(profile_id="WEIGHT_FAST", route_type="FAST", weight_distance=1.0, weight_time=1.0),
            RouteWeightProfile(profile_id="WEIGHT_COMFORTABLE", route_type="COMFORTABLE", weight_distance=1.0, weight_time=1.0, penalty_stairs=80),
            RouteWeightProfile(profile_id="WEIGHT_INDOOR", route_type="INDOOR_FOCUSED", weight_distance=1.0, weight_time=1.0, penalty_outdoor=60, bonus_indoor=30),
        ]
    )

    db.commit()
