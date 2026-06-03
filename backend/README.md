# DKU Campus Map Backend - Week 3~7

이 백엔드는 `DKU_Map_W3toW8.docx`의 **3~7주차 백엔드 범위**를 구현한 FastAPI 프로젝트입니다.

## 3주차 범위

- FastAPI 프로젝트 구조
- `config.py`, `database.py`, `security.py` 기본 구조
- SQLAlchemy 모델 초안
- Pydantic schema 초안
- 최종 테이블 구조를 반영한 `email_verifications`, `tmi_locations` 모델 초안
- `GET /api/buildings`
- `GET /api/rooms/search?keyword=소프트305`
- `GET /api/buildings/{buildingId}/floors/{floor}/indoor-map`
- `resolver.py` 검색어 정규화, 숫자 추출, 건물 약칭 매칭, 층 추정
- `pathfinding.py` 뼈대, `cost_function.py` DCF 초안
- Swagger 실행 확인

## 4주차 범위

4주차에는 DB 담당자가 제공한 건물/강의실/층별 지도 자료를 백엔드에서 실제로 검증하고 DB에 넣을 수 있도록 확장했습니다.

- DB 자료 검증 스크립트 추가
- DB 자료 import 스크립트 추가
- `Building_Master`, `Building_aliases`, `rooms_master`, `floor_pdf_inventory` 자료 읽기 지원
- 같은 이름의 `.xlsx` 또는 `.csv` 파일 모두 지원
- 건물, 건물 약칭, 강의실, 층별 실내 지도 데이터를 SQLAlchemy 모델에 맞게 저장
- 실제 DB 데이터 기준 강의실 검색 로직 개선
- `ICT401`, `소프트401`, `소프트웨어ICT관401` 형태의 검색 흐름 검증
- 층별 실내 지도 API가 DB의 `indoor_maps`, `rooms`를 기준으로 응답하도록 정리
- 8주차 MVP 완성도를 위해 동적 DCF 대신 정적 cost 선택 구조 준비
- `indoor_edges`, `outdoor_edges`에 `cost_fast`, `cost_comfortable`, `cost_indoor` 컬럼 추가
- 기존 SQLite DB에도 새 cost 컬럼이 자동 추가되도록 스키마 보정 함수 작성
- `httpx`를 추가해 FastAPI `TestClient` 기반 API 확인 가능

## 5주차 범위

5주차에는 프론트엔드가 실제 DB 데이터를 받아 Kakao Map, 강의실 검색, 층별 실내 지도 화면을 구성할 수 있도록 API와 좌표 import 구조를 확장했습니다.

- `GET /api/buildings` 프론트 지도 마커용 건물 목록 유지
- `GET /api/buildings/{building_id}/floors` 층 선택 UI용 API 추가
- `GET /api/rooms/search?keyword=ICT401` 검색 응답 구조 정리
- `GET /api/buildings/{building_id}/floors/{floor}/indoor-map` 응답에 rooms 포함
- `room_positions.csv` 또는 `room_positions.xlsx` 검증 코드 추가
- `room_positions` DB import 코드 추가
- 검색 실패 응답을 `errorCode`, `message` 형태로 정리
- 프론트엔드 연동용 API 계약 문서 추가

## 6~7주차 범위

6~7주차에는 ICT관/도서관 실내 그래프와 외부 그래프를 연결해 통합 길찾기가 가능하도록 확장했습니다.

- `indoor_nodes`, `indoor_edges`, `room_nearest_nodes` 기반 실내 Dijkstra 경로 계산
- `outdoor_node`, `outdoor_edge`, `entrance_links` 기반 외부 Dijkstra 경로 계산
- `POST /api/routes` 통합 경로 API 구현
- 기본 경로, 편한 길, 비 오는 날 경로를 동적 DCF로 계산
- `has_ramp`를 `has_slope`로 자동 해석
- `distance_m`이 비어 있으면 외부 노드 `x`, `y` 좌표로 거리 자동 계산
- 외부 예상 시간 자동 계산
- 모든 외부 간선은 기본적으로 양방향 이동 가능하도록 처리
- 출입구가 실제 내부 몇 층 노드와 연결되는지 `entrance_links`와 `indoor_nodes` 기준으로 반영
- `GET /api/outdoor/map` 외부 지도/노드/간선/출입구 링크 조회 API 추가
- `/maps/campus-map.png`로 최종 외부 캠퍼스 지도 이미지 제공
- `외부 구조 설계_최종` 폴더를 통합 import에서 우선 사용
- JWT 기반 로그인 토큰 발급 API 추가
- Passlib/bcrypt 기반 비밀번호 해싱 적용
- 단국대 이메일 인증 요청/검증 API 추가
- SMTP 설정 시 실제 메일 발송, 미설정 시 로컬/시연용 콘솔 인증코드 출력
- `GET /api/auth/me`로 JWT 기반 현재 사용자 조회

## 아직 구현하지 않는 범위

- TMI 제보 API
- 관리자 승인 API
- ICT관/도서관 외 건물의 실내/외부 경로 데이터 확장
- 실제 측정 기반 `distance_m`, 고도, 비가림 구간 정밀 보정

위 기능들은 문서 기준 7주차 이후 작업이며, 관련 데이터가 추가되면 백엔드 import/API/경로 계산에 연결합니다.

## 실행

```powershell
cd backend
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## 3주차 검증 흐름

```text
소프트305 검색
-> 소프트웨어 ICT관 3층 305호로 해석
-> MAP_SOFT_ICT_3F 반환
-> /maps/soft_ict_3f.svg 반환
-> POS_SOFT_ICT_305 좌표 반환
```

## 4주차 데이터 검증/import

DB 담당자가 준 `.xlsx` 또는 `.csv` 파일 4개를 백엔드 모델에 맞게 검증하고 DB에 넣을 수 있습니다.

필요 파일:

```text
Building_Master.xlsx 또는 Building_Master.csv
Building_aliases.xlsx 또는 Building_aliases.csv
rooms_master.xlsx 또는 rooms_master.csv
floor_pdf_inventory.xlsx 또는 floor_pdf_inventory.csv
```

검증:

```powershell
cd backend
python tools/validate_week4_data.py "D:\과제\3-2\오픈소스SW기초\#Project\W3"
```

DB import:

```powershell
cd backend
python tools/import_week4_excel.py "D:\과제\3-2\오픈소스SW기초\#Project\W3" --replace
```

현재 DB 자료에는 `room_positions.csv`가 없으므로 실내 지도 API의 `room_positions`는 비어 있을 수 있습니다.
좌표 파일이 추가되면 같은 방식으로 import 대상에 연결합니다.

## 4주차 정적 cost 방식

8주차 MVP에서는 요청마다 복잡한 DCF를 계산하기보다 edge별 정적 비용을 우선 사용합니다.

`indoor_edges`, `outdoor_edges`에는 아래 비용 컬럼을 사용합니다.

```text
cost_fast
cost_comfortable
cost_indoor
```

경로 계산 시 `FAST`, `COMFORTABLE`, `INDOOR_FOCUSED` routeType에 맞는 cost 컬럼을 선택합니다.
기존 `distance`, `has_stairs`, `has_slope`, `is_covered`, `is_indoor` 같은 속성은 유지하며,
CSV에 cost 값이 없으면 백엔드가 기본 추정값을 계산할 수 있게 준비했습니다.

## 4주차 확인 결과

로컬에서 아래 흐름을 확인했습니다.

```text
엑셀 검증 성공
엑셀 import 성공
/api/buildings 응답 확인
/api/rooms/search?keyword=ICT401 응답 확인
/api/rooms/search?keyword=소프트401 응답 확인
/api/buildings/DKU_ICT/floors/4/indoor-map 응답 확인
```

현재 강의실 좌표와 실내 경로 노드/간선 데이터는 아직 없기 때문에,
API 응답에서 `position`, `nearestIndoorNodeId`, `indoorNodes`, `indoorEdges`는 비어 있을 수 있습니다.

## 5주차 room_positions 검증/import

강의실 좌표 파일을 받으면 아래 명령으로 검증하고 DB에 넣을 수 있습니다.

필요 파일:

```text
room_positions.csv 또는 room_positions.xlsx
```

필수 컬럼:

```text
room_id
x
y
width
height
```

선택 컬럼:

```text
position_id 또는 room_position_id
indoor_map_id
polygon_points
center_x 또는 label_x
center_y 또는 label_y
```

검증:

```powershell
cd backend
python tools/validate_week5_positions.py "D:\과제\3-2\오픈소스SW기초\#Project\W5"
```

DB import:

```powershell
cd backend
python tools/import_week5_positions.py "D:\과제\3-2\오픈소스SW기초\#Project\W5" --replace
```

5주차 API 확인:

```text
GET /api/buildings
GET /api/buildings/DKU_ICT/floors
GET /api/rooms/search?keyword=ICT401
GET /api/buildings/DKU_ICT/floors/4/indoor-map
```

## 7주차 외부 그래프 검증/import

최종 외부 구조 자료는 아래 폴더를 우선 사용합니다.

```text
D:\과제\3-2\오픈소스SW기초\#Project\DB\외부 구조 설계_최종
```

필요 파일:

```text
outdoor_node.csv 또는 outdoor_node.xlsx
outdoor_edge.csv 또는 outdoor_edge.xlsx
entrance_links.csv 또는 entrance_links.xlsx
```

통합 import:

```powershell
cd backend
python tools/import_available_week7_data.py "D:\과제\3-2\오픈소스SW기초\#Project\DB" --replace
```

7주차 API 확인:

```text
GET /api/outdoor/map
POST /api/routes
GET /maps/campus-map.png
```

## 7주차 인증 API 확인

회원가입, 로그인, 이메일 인증, JWT 사용자 조회를 확인할 수 있습니다.

```text
POST /api/auth/register
POST /api/auth/login
POST /api/auth/email/request
POST /api/auth/email/verify
GET /api/auth/me
```

로컬/시연 환경에서는 `.env`의 `EMAIL_DELIVERY_MODE=console`을 사용하면 인증 코드가 서버 로그와 응답의 `devCode`에 표시됩니다.
실제 SMTP 발송을 사용하려면 `EMAIL_DELIVERY_MODE=smtp`로 바꾸고 SMTP 환경변수를 설정해야 합니다.
