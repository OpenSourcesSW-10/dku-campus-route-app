from pydantic import BaseModel, Field


class RoutePreferences(BaseModel):
    # 사용자가 선택할 수 있는 경로 선호 옵션이다.
    avoidStairs: bool = False
    preferIndoor: bool = False
    accessibilityMode: bool = False
    rainMode: bool = False


class RouteRequest(BaseModel):
    # 6주차 통합 길찾기 API에서 받을 요청 본문 초안이다.
    start: str
    destination: str
    routeTypes: list[str] = ["FAST", "COMFORTABLE", "INDOOR_FOCUSED"]
    preferences: RoutePreferences = Field(default_factory=RoutePreferences)


class RouteSummaryResponse(BaseModel):
    # 프론트엔드 경로 카드에 표시할 요약 응답이다.
    routeType: str
    title: str
    totalDistance: float
    estimatedTime: float
    reason: str | None = None
