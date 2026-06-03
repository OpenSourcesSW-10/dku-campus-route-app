from pydantic import BaseModel, Field


class RoutePreferences(BaseModel):
    # 사용자가 선택할 수 있는 경로 선호 옵션이다.
    avoidStairs: bool = False
    avoidSlope: bool = False
    preferIndoor: bool = False
    accessibilityMode: bool = False
    rainMode: bool = False


class RouteRequest(BaseModel):
    # 6주차 통합 길찾기 API에서 받을 요청 본문 초안이다.
    start: str
    destination: str
    routeTypes: list[str] = Field(default_factory=lambda: ["DEFAULT", "COMFORTABLE", "RAINY"])
    preferences: RoutePreferences = Field(default_factory=RoutePreferences)


class RouteSummaryResponse(BaseModel):
    # 프론트엔드 경로 카드에 표시할 요약 응답이다.
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
    nodeId: str
    x: float | None = None
    y: float | None = None
    floorNumber: int | None = None
    indoorMapId: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    label: str | None = None


class RouteSegmentResponse(BaseModel):
    type: str
    buildingId: str | None = None
    floorNumber: int | None = None
    indoorMapId: str | None = None
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
