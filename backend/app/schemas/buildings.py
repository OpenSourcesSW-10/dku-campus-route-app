from app.schemas.common import OrmModel


class BuildingAliasResponse(OrmModel):
    # 건물 검색에 쓰이는 별칭 하나 표현.
    alias: str
    priority: int


class BuildingResponse(OrmModel):
    # 건물 목록/상세 API가 반환하는 건물 정보.
    building_id: str
    name: str
    short_code: str
    latitude: float | None = None
    longitude: float | None = None
    main_outdoor_node_id: str | None = None
    description: str | None = None
    aliases: list[BuildingAliasResponse] = []


class BuildingFloorResponse(OrmModel):
    # 프론트엔드 층 선택 UI에 필요한 층별 실내 지도 요약 정보.
    indoor_map_id: str
    building_id: str
    floor_number: int
    floor_label: str
    map_file_url: str
    status: str
