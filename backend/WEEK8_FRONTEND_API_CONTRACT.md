# Week 8 Frontend API Contract

이 문서는 8주차 최종 백엔드 기준으로 프론트엔드가 연동해야 할 API를 정리한 문서다.

## 기본 정보

```text
Local API Base URL: http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs
Frontend env: VITE_API_BASE_URL=http://127.0.0.1:8000
```

배포 후에는 프론트 Vercel 환경변수 `VITE_API_BASE_URL`에 배포된 백엔드 주소를 넣으면 된다.

```ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
```

## 공통 규칙

- 요청/응답은 JSON 기준이다.
- 로그인 후 보호 API 호출 시 아래 헤더를 붙인다.
- 이메일 인증 API는 사용하지 않는다.
- 회원가입/로그인은 프론트 화면에 맞춰 `studentId + password`만 사용한다.
- `map_file_url`, `mapFileUrl`처럼 응답 필드명이 endpoint마다 다를 수 있으므로 실제 응답 필드명을 그대로 사용한다.

```http
Authorization: Bearer {accessToken}
```

## 인증 API

### 회원가입

```http
POST /api/auth/register
```

Request:

```json
{
  "studentId": "32207777",
  "password": "password123"
}
```

Validation:

- `studentId`: 숫자만 허용, 1~20자
- `password`: 8~20자

Response `201`:

```json
{
  "accessToken": "JWT_TOKEN",
  "tokenType": "bearer",
  "user": {
    "user_id": "USER_xxx",
    "studentId": "32207777",
    "nickname": "32207777",
    "role": "USER",
    "created_at": "2026-06-08T10:27:08.028753+00:00"
  }
}
```

Error examples:

```json
{
  "detail": {
    "errorCode": "STUDENT_ID_ALREADY_REGISTERED",
    "message": "이미 가입된 학번입니다."
  }
}
```

### 로그인

```http
POST /api/auth/login
```

Request:

```json
{
  "studentId": "32207777",
  "password": "password123"
}
```

Response `200`:

```json
{
  "accessToken": "JWT_TOKEN",
  "tokenType": "bearer",
  "user": {
    "user_id": "USER_xxx",
    "studentId": "32207777",
    "nickname": "32207777",
    "role": "USER",
    "created_at": "2026-06-08T10:27:08.028753+00:00"
  }
}
```

### 현재 사용자 조회

```http
GET /api/auth/me
Authorization: Bearer {accessToken}
```

Response `200`:

```json
{
  "user_id": "USER_xxx",
  "studentId": "32207777",
  "nickname": "32207777",
  "role": "USER",
  "created_at": "2026-06-08T10:27:08.028753+00:00"
}
```

## 건물 API

### 건물 목록

```http
GET /api/buildings
```

용도:

- 외부 지도 건물 마커 표시
- 건물 선택 UI
- 건물 검색 후보 목록

Response:

```json
[
  {
    "building_id": "DKU_ICT",
    "name": "소프트웨어 ICT관",
    "short_code": "ICT",
    "latitude": 37.321,
    "longitude": 127.129,
    "main_outdoor_node_id": "OUT_ICT_MAIN",
    "description": "category=software",
    "aliases": [
      {
        "alias": "ICT",
        "priority": 1
      }
    ]
  }
]
```

### 건물 상세

```http
GET /api/buildings/{building_id}
```

Example:

```http
GET /api/buildings/DKU_ICT
```

### 건물 층 목록

```http
GET /api/buildings/{building_id}/floors
```

Example:

```http
GET /api/buildings/DKU_ICT/floors
```

Response:

```json
[
  {
    "indoor_map_id": "MAP_DKU_ICT_4F",
    "building_id": "DKU_ICT",
    "floor_number": 4,
    "floor_label": "4F",
    "map_file_url": "/maps/ICT_4Fa-1.png",
    "status": "draft"
  }
]
```

## 강의실 검색 API

```http
GET /api/rooms/search?keyword={keyword}
```

Example:

```http
GET /api/rooms/search?keyword=ICT401
GET /api/rooms/search?keyword=소프트401
```

용도:

- 검색창에서 강의실 검색
- 검색 결과에서 실내 지도 이동
- 강의실 하이라이트 표시
- 길찾기 출발지/도착지 입력 검증

Response:

```json
{
  "type": "ROOM",
  "roomId": "DKU_ICT_4_401",
  "roomCode": "ICT-4F-401",
  "buildingId": "DKU_ICT",
  "buildingName": "소프트웨어 ICT관",
  "floorNumber": 4,
  "floorLabel": "4F",
  "roomNumber": "401",
  "indoorMap": {
    "indoorMapId": "MAP_DKU_ICT_4F",
    "mapFileUrl": "/maps/ICT_4Fa-1.png",
    "canvasWidth": 1000,
    "canvasHeight": 707
  },
  "position": {
    "position_id": "POS_DKU_ICT_4_401",
    "room_id": "DKU_ICT_4_401",
    "indoor_map_id": "MAP_DKU_ICT_4F",
    "x": 120.0,
    "y": 200.0,
    "width": 80.0,
    "height": 40.0,
    "polygon_points": null,
    "center_x": 160.0,
    "center_y": 220.0
  },
  "nearestIndoorNodeId": "ICT_4_N001"
}
```

검색 실패 예시:

```json
{
  "detail": {
    "errorCode": "ROOM_NOT_FOUND",
    "message": "검색한 강의실을 찾을 수 없습니다."
  }
}
```

## 실내 지도 API

```http
GET /api/buildings/{building_id}/floors/{floor}/indoor-map
```

Example:

```http
GET /api/buildings/DKU_ICT/floors/4/indoor-map
```

용도:

- 층별 실내 지도 이미지 표시
- 강의실 하이라이트 표시
- 실내 노드/간선 디버그 표시
- 실내 경로선 렌더링 기준 좌표계 확인

Response 핵심 필드:

```json
{
  "indoor_map_id": "MAP_DKU_ICT_4F",
  "building_id": "DKU_ICT",
  "floor_number": 4,
  "floor_label": "4F",
  "map_file_url": "/maps/ICT_4Fa-1.png",
  "canvas_width": 1000,
  "canvas_height": 707,
  "rooms": [],
  "room_positions": [],
  "indoor_nodes": [],
  "indoor_edges": []
}
```

프론트 처리 기준:

- 실내 지도 이미지는 `${API_BASE_URL}${map_file_url}`로 요청한다.
- `canvas_width`, `canvas_height`를 SVG/viewBox 기준으로 사용한다.
- 강의실 하이라이트는 `room_positions`의 `x`, `y`, `width`, `height`를 사용한다.
- 실내 경로선은 길찾기 API의 `segments[].pathPoints`를 같은 좌표계 위에 그린다.

## 지도 파일 API

```http
GET /maps/{map_file_name}
```

Example:

```http
GET /maps/campus-map.png
GET /maps/ICT_4Fa-1.png
```

프론트에서는 DB 응답의 `map_file_url` 값을 그대로 붙이면 된다.

```ts
const imageUrl = `${API_BASE_URL}${mapFileUrl}`;
```

## 외부 지도 API

```http
GET /api/outdoor/map
```

용도:

- 캠퍼스 외부 지도 이미지 표시
- 외부 노드/간선 디버그 표시
- 건물 출입구 연결 정보 확인

Response:

```json
{
  "map_file_url": "/maps/campus-map.png",
  "canvas_width": null,
  "canvas_height": null,
  "nodes": [
    {
      "outdoor_node_id": "OUT_ICT_MAIN",
      "node_type": "entrance",
      "building_id": "DKU_ICT",
      "latitude": 37.321,
      "longitude": 127.129,
      "map_x": 500.0,
      "map_y": 300.0,
      "outdoor_level": "L3",
      "altitude_m": 120.0,
      "label": "ICT관 입구"
    }
  ],
  "edges": [
    {
      "outdoor_edge_id": "OUT_EDGE_001",
      "from_node_id": "OUT_ICT_MAIN",
      "to_node_id": "OUT_LIB_MAIN",
      "is_bidirectional": true,
      "distance": 80.0,
      "estimated_time": 60.0,
      "edge_type": "walkway",
      "is_covered": false,
      "has_stairs": false,
      "has_slope": true,
      "polyline_points": null
    }
  ],
  "entrance_links": [
    {
      "link_id": "LINK_ICT_MAIN",
      "building_id": "DKU_ICT",
      "outdoor_node_id": "OUT_ICT_MAIN",
      "indoor_node_id": "ICT_3_ENTRANCE",
      "entrance_name": "ICT관 후문",
      "floor_number": 3,
      "is_main": true
    }
  ]
}
```

## 통합 길찾기 API

```http
POST /api/routes
```

용도:

- 강의실에서 강의실까지 최종 경로 계산
- 실내-외부-실내 통합 경로 표시
- 기본 경로, 편한 길, 비 오는 날 경로를 한 번에 받기

Request:

```json
{
  "start": "ICT401",
  "destination": "도서관201",
  "routeTypes": ["DEFAULT", "COMFORTABLE", "RAINY"],
  "preferences": {
    "avoidStairs": false,
    "avoidSlope": false,
    "preferIndoor": false,
    "accessibilityMode": false,
    "rainMode": false
  }
}
```

Route types:

- `DEFAULT`: 기본 경로
- `COMFORTABLE`: 편한 길
- `RAINY`: 비 오는 날 경로

Response:

```json
[
  {
    "routeType": "DEFAULT",
    "title": "기본 경로",
    "totalCost": 142.0,
    "totalDistance": 120.0,
    "totalEstimatedTime": 95.0,
    "reason": "가장 기본적인 이동 비용 기준 경로",
    "segments": [
      {
        "type": "INDOOR",
        "buildingId": "DKU_ICT",
        "floorNumber": 4,
        "indoorMapId": "MAP_DKU_ICT_4F",
        "nodeIds": ["ICT_4_N001", "ICT_4_N002"],
        "edgeIds": ["ICT_4_E001"],
        "pathPoints": [
          {
            "nodeId": "ICT_4_N001",
            "pointType": "NODE",
            "x": 100.0,
            "y": 200.0,
            "floorNumber": 4,
            "indoorMapId": "MAP_DKU_ICT_4F",
            "label": "401호 앞"
          }
        ]
      },
      {
        "type": "VERTICAL",
        "buildingId": "DKU_ICT",
        "floorNumber": 4,
        "toFloorNumber": 3,
        "transitionType": "ELEVATOR",
        "instruction": "엘리베이터로 4층에서 3층으로 이동"
      },
      {
        "type": "OUTDOOR",
        "nodeIds": ["OUT_ICT_MAIN", "OUT_LIB_MAIN"],
        "edgeIds": ["OUT_EDGE_001"],
        "pathPoints": [
          {
            "nodeId": "OUT_ICT_MAIN",
            "pointType": "NODE",
            "latitude": 37.321,
            "longitude": 127.129,
            "x": 500.0,
            "y": 300.0,
            "label": "ICT관 입구"
          },
          {
            "nodeId": "OUT_EDGE_001_SHAPE_1",
            "sourceEdgeId": "OUT_EDGE_001",
            "pointType": "SHAPE",
            "latitude": 37.3215,
            "longitude": 127.1295,
            "x": 520.0,
            "y": 320.0
          }
        ]
      }
    ]
  }
]
```

프론트 렌더링 기준:

- `segments[].type === "OUTDOOR"`이면 외부 지도에 `pathPoints`를 polyline으로 그린다.
- `OUTDOOR.pathPoints`에 `latitude`, `longitude`가 있으면 Kakao Map 좌표로 그릴 수 있다.
- `OUTDOOR.pathPoints`에 `x`, `y`가 있으면 캠퍼스 이미지 좌표계에 그릴 수 있다.
- `segments[].type === "INDOOR"`이면 `indoorMapId`, `floorNumber` 기준으로 실내 지도 위에 `x`, `y` polyline을 그린다.
- `segments[].type === "VERTICAL"`이면 지도 선이 아니라 층 이동 안내 UI로 표시한다.
- `pointType === "SHAPE"`는 외부 곡선 경로의 중간 좌표다.
- `sourceEdgeId`는 어떤 외부 간선에서 나온 중간 좌표인지 확인할 때 사용한다.

모든 경로 실패 시 error:

```json
{
  "detail": {
    "errors": [
      {
        "routeType": "DEFAULT",
        "errorCode": "OUTDOOR_ROUTE_NOT_FOUND",
        "message": "건물 사이의 외부 경로를 찾을 수 없습니다."
      }
    ]
  }
}
```

## 실내 길찾기 API

```http
POST /api/routes/indoor
```

용도:

- 같은 건물 내부 경로만 별도로 테스트
- 프론트 최종 기능에서는 보통 `POST /api/routes` 사용 권장

Request:

```json
{
  "fromRoomId": "DKU_ICT_4_401",
  "toRoomId": "DKU_ICT_3_305",
  "routeType": "DEFAULT",
  "preferences": {
    "avoidStairs": false,
    "avoidSlope": false,
    "preferIndoor": false,
    "accessibilityMode": false,
    "rainMode": false
  }
}
```

Response:

```json
{
  "routeType": "DEFAULT",
  "title": "기본 경로",
  "totalCost": 50.0,
  "totalDistance": 45.0,
  "totalEstimatedTime": 35.0,
  "segments": []
}
```

## 참조 데이터 API

```http
GET /api/reference-data
```

용도:

- `edge_type`, `node_type`, `room_type` 표시명 변환
- 출입구 목록 UI
- 필터 UI

Response:

```json
{
  "edgeTypes": [
    {
      "edge_type": "stairs",
      "display_name": "계단",
      "description": "층간 이동 계단"
    }
  ],
  "indoorNodeTypes": [],
  "roomCategories": [],
  "entrances": []
}
```

## TMI API

### 공개 TMI 목록 조회

```http
GET /api/tmi
GET /api/tmi?location_type=OUTDOOR
GET /api/tmi?building_id=DKU_ICT
GET /api/tmi?tag=카페
```

Response:

```json
[
  {
    "tmi_location_id": "TMI_xxx",
    "name": "조용한 휴식 공간",
    "location_type": "OUTDOOR",
    "building_id": "DKU_ICT",
    "room_id": null,
    "indoor_map_id": null,
    "floor_number": null,
    "latitude": 37.321,
    "longitude": 127.129,
    "map_x": 500.0,
    "map_y": 300.0,
    "representative_tags": "휴식,조용함",
    "status": "approved",
    "verified_count": 1,
    "created_by": "USER_xxx",
    "created_at": "2026-06-08T10:27:08.028753+00:00"
  }
]
```

### TMI 등록

```http
POST /api/tmi
Authorization: Bearer {accessToken}
```

Request:

```json
{
  "name": "콘센트 있는 자리",
  "locationType": "INDOOR",
  "buildingId": "DKU_LIB",
  "roomId": null,
  "indoorMapId": "MAP_DKU_LIB_2F",
  "floorNumber": 2,
  "latitude": null,
  "longitude": null,
  "mapX": 450.0,
  "mapY": 280.0,
  "representativeTags": "콘센트,공부"
}
```

등록 직후 상태는 `pending`이다. 일반 공개 목록에는 `approved`, `verified` 상태만 노출된다.

### TMI 상세 조회

```http
GET /api/tmi/{tmi_location_id}
```

### 관리자 TMI 목록

```http
GET /api/tmi/admin/list
GET /api/tmi/admin/list?status=pending
Authorization: Bearer {adminAccessToken}
```

### 관리자 TMI 상태 변경

```http
PATCH /api/tmi/admin/{tmi_location_id}/status
Authorization: Bearer {adminAccessToken}
```

Request:

```json
{
  "status": "approved"
}
```

가능한 status:

- `pending`
- `approved`
- `rejected`
- `verified`

## 제보 API

### 승인된 제보 목록

```http
GET /api/reports/approved
GET /api/reports/approved?building_id=DKU_ICT
GET /api/reports/approved?room_id=DKU_ICT_4_401
GET /api/reports/approved?tmi_location_id=TMI_xxx
```

### 제보 등록

```http
POST /api/reports
Authorization: Bearer {accessToken}
```

Request:

```json
{
  "reportType": "MAP_ERROR",
  "targetType": "ROOM",
  "targetId": "DKU_ICT_4_401",
  "tmiLocationId": null,
  "buildingId": "DKU_ICT",
  "roomId": "DKU_ICT_4_401",
  "title": "강의실 위치가 달라요",
  "content": "지도에서 표시된 위치보다 오른쪽에 있습니다.",
  "tags": "위치오류,강의실"
}
```

Response:

```json
{
  "report_id": "REPORT_xxx",
  "user_id": "USER_xxx",
  "report_type": "MAP_ERROR",
  "target_type": "ROOM",
  "target_id": "DKU_ICT_4_401",
  "tmi_location_id": null,
  "building_id": "DKU_ICT",
  "room_id": "DKU_ICT_4_401",
  "title": "강의실 위치가 달라요",
  "content": "지도에서 표시된 위치보다 오른쪽에 있습니다.",
  "tags": "위치오류,강의실",
  "status": "pending",
  "verified_count": 0,
  "created_at": "2026-06-08T10:27:08.028753+00:00"
}
```

### 관리자 제보 목록

```http
GET /api/reports/admin/list
GET /api/reports/admin/list?status=pending
GET /api/reports/admin/list?report_type=MAP_ERROR
Authorization: Bearer {adminAccessToken}
```

### 관리자 제보 상태 변경

```http
PATCH /api/reports/admin/{report_id}/status
Authorization: Bearer {adminAccessToken}
```

Request:

```json
{
  "status": "approved"
}
```

## 준비 상태 API

```http
GET /api/status/readiness
```

용도:

- 최종 제출 전 DB 자료 누락 여부 확인
- 프론트에서 "현재 경로 계산 가능 범위"를 확인할 때 참고 가능

Response:

```json
{
  "overallStatus": "PARTIAL",
  "checks": [
    {
      "name": "사용자 인증 테이블",
      "status": "READY",
      "message": "학번 기반 회원가입, 로그인, JWT 인증 구조가 준비되어 있습니다.",
      "requiredAction": null,
      "details": {
        "users": 0
      }
    }
  ]
}
```

## 프론트 연결 우선순위

1. `VITE_API_BASE_URL` 설정
2. `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` 연결
3. `GET /api/buildings`, `GET /api/rooms/search` 연결
4. `GET /api/buildings/{building_id}/floors/{floor}/indoor-map` 연결
5. `POST /api/routes` 연결
6. `segments[].type` 기준으로 실외/실내/층 이동 렌더링 분기
7. TMI/제보 등록 시 `Authorization: Bearer {accessToken}` 적용
8. 관리자 기능이 필요하면 `ADMIN_STUDENT_IDS`에 등록된 학번으로 가입 후 admin API 사용

## 프론트에서 특히 맞춰야 하는 부분

- 로그인/회원가입은 이메일 없이 `studentId`, `password`만 보낸다.
- `accessToken`은 로그인 후 저장하고, TMI/제보/관리자 API에 Bearer token으로 넣는다.
- 실내 지도 이미지는 백엔드의 `/maps/...` URL을 사용한다.
- 강의실 검색 결과의 `position`이 있으면 바로 하이라이트 가능하다.
- 통합 길찾기 응답은 `segments` 배열이 핵심이다.
- `OUTDOOR` segment는 외부 지도 polyline으로 표시한다.
- `INDOOR` segment는 해당 `indoorMapId` 실내 지도 위에 표시한다.
- `VERTICAL` segment는 선이 아니라 "엘리베이터/계단으로 층 이동" 안내로 표시한다.
- 이메일 인증 관련 화면/API는 구현하지 않는다.
