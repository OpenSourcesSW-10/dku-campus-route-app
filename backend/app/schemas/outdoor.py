from app.schemas.common import OrmModel


class OutdoorNodeResponse(OrmModel):
    outdoor_node_id: str
    node_type: str
    building_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    map_x: float | None = None
    map_y: float | None = None
    outdoor_level: str | None = None
    altitude_m: float | None = None
    label: str | None = None
    description: str | None = None


class OutdoorEdgeResponse(OrmModel):
    outdoor_edge_id: str
    from_node_id: str
    to_node_id: str
    is_bidirectional: bool
    distance: float
    estimated_time: float
    edge_type: str
    is_covered: bool
    is_indoor: bool
    has_stairs: bool
    has_slope: bool
    slope_level: int
    altitude_gain: float | None = None
    complexity_level: int
    accessibility_level: int
    is_shortcut: bool
    cost_fast: float
    cost_comfortable: float
    cost_indoor: float
    description: str | None = None


class EntranceLinkResponse(OrmModel):
    link_id: str
    building_id: str
    outdoor_node_id: str
    indoor_node_id: str
    entrance_name: str
    floor_number: int | None = None
    is_main: bool


class OutdoorMapResponse(OrmModel):
    map_file_url: str
    canvas_width: int | None = None
    canvas_height: int | None = None
    nodes: list[OutdoorNodeResponse]
    edges: list[OutdoorEdgeResponse]
    entrance_links: list[EntranceLinkResponse]
