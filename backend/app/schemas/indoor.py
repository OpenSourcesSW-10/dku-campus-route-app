from app.schemas.common import OrmModel


class RoomPositionResponse(OrmModel):
    # 실내 지도 위 강의실 하이라이트 좌표이다.
    position_id: str
    room_id: str
    x: float
    y: float
    width: float
    height: float
    polygon_points: str | None = None
    center_x: float | None = None
    center_y: float | None = None


class IndoorNodeResponse(OrmModel):
    # 실내 경로 계산과 표시 기준점이다.
    indoor_node_id: str
    node_type: str
    x: float
    y: float
    label: str | None = None
    vertical_group_id: str | None = None
    description: str | None = None


class IndoorEdgeResponse(OrmModel):
    # 실내 노드 사이 연결선과 비용 계산 속성이다.
    indoor_edge_id: str
    from_node_id: str
    to_node_id: str
    distance: float
    estimated_time: float
    edge_type: str
    has_stairs: bool
    has_slope: bool
    slope_level: int
    is_elevator: bool
    is_ramp: bool
    is_indoor: bool
    is_covered: bool
    is_accessible: bool
    complexity_level: int
    description: str | None = None


class IndoorMapResponse(OrmModel):
    # 한 층의 지도 파일, 강의실 좌표, 실내 그래프 데이터를 묶은 응답이다.
    indoor_map_id: str
    building_id: str
    floor_number: int
    floor_label: str
    source_pdf_name: str | None = None
    map_file_url: str
    canvas_width: int
    canvas_height: int
    version: str
    status: str
    room_positions: list[RoomPositionResponse] = []
    indoor_nodes: list[IndoorNodeResponse] = []
    indoor_edges: list[IndoorEdgeResponse] = []
