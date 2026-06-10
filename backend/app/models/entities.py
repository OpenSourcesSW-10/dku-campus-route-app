from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Building(Base):
    # 캠퍼스 건물의 기본 정보와 대표 위치 저장.
    __tablename__ = "buildings"

    building_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    short_code: Mapped[str] = mapped_column(String(30), index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    main_outdoor_node_id: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)

    aliases: Mapped[list["BuildingAlias"]] = relationship(back_populates="building")
    indoor_maps: Mapped[list["IndoorMap"]] = relationship(back_populates="building")
    rooms: Mapped[list["Room"]] = relationship(back_populates="building")


class BuildingAlias(Base):
    # "소프트", "ICT" 같은 검색용 건물 별칭 저장.
    __tablename__ = "building_aliases"

    alias_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.building_id"), index=True)
    alias: Mapped[str] = mapped_column(String(50), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)

    building: Mapped[Building] = relationship(back_populates="aliases")


class EdgeType(Base):
    # 실내/외 간선 edge_type의 표시명과 의미 저장.
    __tablename__ = "edge_types"

    edge_type: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)


class IndoorNodeType(Base):
    # 실내 노드 node_type의 표시명과 의미 저장.
    __tablename__ = "indoor_node_types"

    node_type: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)


class RoomCategory(Base):
    # 강의실/공간 room_type의 표시명과 의미 저장.
    __tablename__ = "room_categories"

    room_type: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)


class EntranceMaster(Base):
    # 건물별 출입구 기본 목록 저장. 실제 경로 연결은 entrance_links가 담당.
    __tablename__ = "entrance_master"

    entrance_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.building_id"), index=True)
    floor_number: Mapped[int] = mapped_column(Integer, index=True)
    entrance_name: Mapped[str] = mapped_column(String(100))
    entrance_type: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str | None] = mapped_column(Text)


class IndoorMap(Base):
    # 건물별/층별 실내 지도 파일과 기준 좌표계 저장.
    __tablename__ = "indoor_maps"

    indoor_map_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.building_id"), index=True)
    floor_number: Mapped[int] = mapped_column(Integer, index=True)
    floor_label: Mapped[str] = mapped_column(String(20))
    source_pdf_name: Mapped[str | None] = mapped_column(String(255))
    map_file_url: Mapped[str] = mapped_column(String(255))
    canvas_width: Mapped[int] = mapped_column(Integer)
    canvas_height: Mapped[int] = mapped_column(Integer)
    version: Mapped[str] = mapped_column(String(30), default="v0.1")
    status: Mapped[str] = mapped_column(String(30), default="draft")
    created_at: Mapped[str | None] = mapped_column(String(30))

    building: Mapped[Building] = relationship(back_populates="indoor_maps")
    rooms: Mapped[list["Room"]] = relationship(back_populates="indoor_map")
    room_positions: Mapped[list["RoomPosition"]] = relationship(back_populates="indoor_map")
    indoor_nodes: Mapped[list["IndoorNode"]] = relationship(back_populates="indoor_map")
    indoor_edges: Mapped[list["IndoorEdge"]] = relationship(back_populates="indoor_map")


class Room(Base):
    # 강의실의 건물, 층, 호실, 가까운 실내 노드 정보 저장.
    __tablename__ = "rooms"

    room_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.building_id"), index=True)
    indoor_map_id: Mapped[str] = mapped_column(ForeignKey("indoor_maps.indoor_map_id"), index=True)
    room_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    room_number: Mapped[str] = mapped_column(String(20), index=True)
    floor_number: Mapped[int] = mapped_column(Integer, index=True)
    room_type: Mapped[str] = mapped_column(String(30), default="LECTURE")
    nearest_indoor_node_id: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)

    building: Mapped[Building] = relationship(back_populates="rooms")
    indoor_map: Mapped[IndoorMap] = relationship(back_populates="rooms")
    positions: Mapped[list["RoomPosition"]] = relationship(back_populates="room")


class RoomPosition(Base):
    # 실내 지도 위에서 강의실을 하이라이트할 좌표 저장.
    __tablename__ = "room_positions"

    position_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.room_id"), index=True)
    indoor_map_id: Mapped[str] = mapped_column(ForeignKey("indoor_maps.indoor_map_id"), index=True)
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    width: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)
    polygon_points: Mapped[str | None] = mapped_column(Text)
    center_x: Mapped[float | None] = mapped_column(Float)
    center_y: Mapped[float | None] = mapped_column(Float)

    room: Mapped[Room] = relationship(back_populates="positions")
    indoor_map: Mapped[IndoorMap] = relationship(back_populates="room_positions")


class IndoorNode(Base):
    # 실내 경로 계산에 사용할 출입구, 복도, 계단, 엘리베이터 기준점.
    __tablename__ = "indoor_nodes"

    indoor_node_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.building_id"), index=True)
    indoor_map_id: Mapped[str] = mapped_column(ForeignKey("indoor_maps.indoor_map_id"), index=True)
    floor_number: Mapped[int] = mapped_column(Integer, index=True)
    node_type: Mapped[str] = mapped_column(String(50), index=True)
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    label: Mapped[str | None] = mapped_column(String(100))
    vertical_group_id: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)

    indoor_map: Mapped[IndoorMap] = relationship(back_populates="indoor_nodes")


class IndoorEdge(Base):
    # 실내 노드 사이의 연결선과 경로 비용 계산 속성 저장.
    __tablename__ = "indoor_edges"

    indoor_edge_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    indoor_map_id: Mapped[str] = mapped_column(ForeignKey("indoor_maps.indoor_map_id"), index=True)
    from_node_id: Mapped[str] = mapped_column(String(80), index=True)
    to_node_id: Mapped[str] = mapped_column(String(80), index=True)
    is_bidirectional: Mapped[bool] = mapped_column(Boolean, default=True)
    distance: Mapped[float] = mapped_column(Float)
    estimated_time: Mapped[float] = mapped_column(Float)
    edge_type: Mapped[str] = mapped_column(String(50), index=True)
    has_stairs: Mapped[bool] = mapped_column(Boolean, default=False)
    has_slope: Mapped[bool] = mapped_column(Boolean, default=False)
    slope_level: Mapped[int] = mapped_column(Integer, default=0)
    is_elevator: Mapped[bool] = mapped_column(Boolean, default=False)
    is_ramp: Mapped[bool] = mapped_column(Boolean, default=False)
    is_indoor: Mapped[bool] = mapped_column(Boolean, default=True)
    is_covered: Mapped[bool] = mapped_column(Boolean, default=True)
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=True)
    complexity_level: Mapped[int] = mapped_column(Integer, default=0)
    cost_fast: Mapped[float] = mapped_column(Float, default=1.0)
    cost_comfortable: Mapped[float] = mapped_column(Float, default=1.0)
    cost_indoor: Mapped[float] = mapped_column(Float, default=1.0)
    description: Mapped[str | None] = mapped_column(Text)

    indoor_map: Mapped[IndoorMap] = relationship(back_populates="indoor_edges")


class OutdoorNode(Base):
    # 캠퍼스 외부 길찾기에 사용할 건물 입구와 보행로 기준점.
    __tablename__ = "outdoor_nodes"

    outdoor_node_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    node_type: Mapped[str] = mapped_column(String(50), index=True)
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.building_id"))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    map_x: Mapped[float | None] = mapped_column(Float)
    map_y: Mapped[float | None] = mapped_column(Float)
    outdoor_level: Mapped[str | None] = mapped_column(String(50))
    altitude_m: Mapped[float | None] = mapped_column(Float)
    label: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)


class OutdoorEdge(Base):
    # 실외 노드 사이의 연결선과 DCF 속성 저장.
    __tablename__ = "outdoor_edges"

    outdoor_edge_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    from_node_id: Mapped[str] = mapped_column(String(80), index=True)
    to_node_id: Mapped[str] = mapped_column(String(80), index=True)
    is_bidirectional: Mapped[bool] = mapped_column(Boolean, default=True)
    distance: Mapped[float] = mapped_column(Float)
    estimated_time: Mapped[float] = mapped_column(Float)
    edge_type: Mapped[str] = mapped_column(String(50), index=True)
    is_covered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_indoor: Mapped[bool] = mapped_column(Boolean, default=False)
    has_stairs: Mapped[bool] = mapped_column(Boolean, default=False)
    has_slope: Mapped[bool] = mapped_column(Boolean, default=False)
    slope_level: Mapped[int] = mapped_column(Integer, default=0)
    altitude_gain: Mapped[float | None] = mapped_column(Float)
    complexity_level: Mapped[int] = mapped_column(Integer, default=0)
    accessibility_level: Mapped[int] = mapped_column(Integer, default=0)
    is_shortcut: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_fast: Mapped[float] = mapped_column(Float, default=1.0)
    cost_comfortable: Mapped[float] = mapped_column(Float, default=1.0)
    cost_indoor: Mapped[float] = mapped_column(Float, default=1.0)
    polyline_points: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)


class EntranceLink(Base):
    # 실외 입구 노드와 실내 출입구 노드 연결.
    __tablename__ = "entrance_links"

    link_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.building_id"), index=True)
    outdoor_node_id: Mapped[str] = mapped_column(String(80), index=True)
    indoor_node_id: Mapped[str] = mapped_column(String(80), index=True)
    entrance_name: Mapped[str] = mapped_column(String(100))
    floor_number: Mapped[int | None] = mapped_column(Integer)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)


class User(Base):
    # 학번 기반 로그인과 제보 권한에 사용할 사용자 계정.
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    student_id: Mapped[str | None] = mapped_column(String(30), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(String(30), default="USER")
    created_at: Mapped[str | None] = mapped_column(String(30))


class TmiLocation(Base):
    # 지도 위에 표시될 TMI 마커의 위치와 승인 상태 저장.
    __tablename__ = "tmi_locations"

    tmi_location_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    location_type: Mapped[str] = mapped_column(String(30), index=True)
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.building_id"), index=True)
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.room_id"), index=True)
    indoor_map_id: Mapped[str | None] = mapped_column(ForeignKey("indoor_maps.indoor_map_id"), index=True)
    floor_number: Mapped[int | None] = mapped_column(Integer, index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    map_x: Mapped[float | None] = mapped_column(Float)
    map_y: Mapped[float | None] = mapped_column(Float)
    representative_tags: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    verified_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), index=True)
    created_at: Mapped[str | None] = mapped_column(String(30))


class Report(Base):
    # 강의실 정보나 TMI에 대한 사용자 제보 내용 저장.
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(80), index=True)
    report_type: Mapped[str] = mapped_column(String(30))
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[str | None] = mapped_column(String(80), index=True)
    tmi_location_id: Mapped[str | None] = mapped_column(ForeignKey("tmi_locations.tmi_location_id"), index=True)
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.building_id"), index=True)
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.room_id"), index=True)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    verified_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str | None] = mapped_column(String(30))


class RouteWeightProfile(Base):
    # 빠른 길, 편한 길, 실내 위주별 DCF 가중치 저장.
    __tablename__ = "route_weight_profiles"

    profile_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    route_type: Mapped[str] = mapped_column(String(30), index=True)
    weight_distance: Mapped[float] = mapped_column(Float, default=1.0)
    weight_time: Mapped[float] = mapped_column(Float, default=1.0)
    penalty_stairs: Mapped[float] = mapped_column(Float, default=0.0)
    penalty_slope: Mapped[float] = mapped_column(Float, default=0.0)
    penalty_complexity: Mapped[float] = mapped_column(Float, default=0.0)
    penalty_uncovered: Mapped[float] = mapped_column(Float, default=0.0)
    penalty_outdoor: Mapped[float] = mapped_column(Float, default=0.0)
    bonus_indoor: Mapped[float] = mapped_column(Float, default=0.0)
    bonus_covered: Mapped[float] = mapped_column(Float, default=0.0)
    bonus_elevator: Mapped[float] = mapped_column(Float, default=0.0)
    bonus_ramp: Mapped[float] = mapped_column(Float, default=0.0)
    bonus_shortcut: Mapped[float] = mapped_column(Float, default=0.0)
    bonus_building_passage: Mapped[float] = mapped_column(Float, default=0.0)
    bonus_bridge: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text)
