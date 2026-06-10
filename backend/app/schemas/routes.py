"""
Route API request and response schemas.

프론트와 백엔드가 공유하는 경로 표시 계약.
segments와 pathPoints 구조는 지도 렌더링 방식에 직접 영향.
"""

from pydantic import BaseModel, Field


class RoutePreferences(BaseModel):
    # 사용자가 선택할 수 있는 경로 선호 옵션.
    avoidStairs: bool = False
    avoidSlope: bool = False
    preferIndoor: bool = False
    accessibilityMode: bool = False
    rainMode: bool = False


class RouteRequest(BaseModel):
    # 통합 길찾기 API 요청 본문.
    start: str
    destination: str
    routeTypes: list[str] = Field(default_factory=lambda: ["DEFAULT", "COMFORTABLE", "RAINY"])
    preferences: RoutePreferences = Field(default_factory=RoutePreferences)


class RouteSummaryResponse(BaseModel):
    # 프론트엔드 경로 카드 표시용 요약 응답.
    routeType: str
    title: str
    totalDistance: float
    estimatedTime: float
    reason: str | None = None


class IndoorRouteRequest(BaseModel):
    fromRoomId: str
    toRoomId: str
    routeType: str = "DEFAULT"
    preferences: RoutePreferences = Field(default_factory=RoutePreferences)


class RoutePoint(BaseModel):
    # NODE는 실제 그래프 노드, SHAPE는 외부 polyline 구성용 중간 좌표.
    nodeId: str
    sourceEdgeId: str | None = None
    pointType: str = "NODE"
    x: float | None = None
    y: float | None = None
    floorNumber: int | None = None
    indoorMapId: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    label: str | None = None


class RouteSegmentResponse(BaseModel):
    # type은 프론트 렌더링 방식 결정.
    # INDOOR는 실내 지도 SVG, OUTDOOR는 외부 지도 Polyline, VERTICAL은 층 이동 안내 처리.
    type: str
    buildingId: str | None = None
    floorNumber: int | None = None
    indoorMapId: str | None = None
    toFloorNumber: int | None = None
    toIndoorMapId: str | None = None
    transitionType: str | None = None
    instruction: str | None = None
    nodeIds: list[str] = Field(default_factory=list)
    edgeIds: list[str] = Field(default_factory=list)
    pathPoints: list[RoutePoint] = Field(default_factory=list)


class RouteDetailResponse(BaseModel):
    routeType: str
    title: str
    totalCost: float
    totalDistance: float
    totalEstimatedTime: float
    reason: str | None = None
    segments: list[RouteSegmentResponse]
