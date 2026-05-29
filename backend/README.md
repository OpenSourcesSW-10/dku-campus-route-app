# DKU Campus Map Backend - Week 3~5

이 백엔드는 `DKU_Map_W3toW8.docx`의 **3~5주차 백엔드 범위**를 구현한 FastAPI 프로젝트입니다.

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

## 아직 구현하지 않는 범위

- 실내 Dijkstra 완성
- 실외 길찾기 완성
- 통합 `POST /api/routes`
- JWT 로그인
- 이메일 인증
- TMI 제보 API
- 관리자 승인 API
- `room_positions.csv` 기반 강의실 좌표 import
- `indoor_nodes.csv`, `indoor_edges.csv` 기반 실내 그래프 import
- `outdoor_nodes.csv`, `outdoor_edges.csv`, `entrance_links.csv` 기반 실외/실내 연결 그래프 import
- 건물 출입구, 후문 층수, 구름다리 연결처럼 층수가 바뀌는 연결 정보 반영

위 기능들은 문서 기준 5주차 후반~7주차 작업이며, 관련 데이터가 추가되면 백엔드 import/API/경로 계산에 연결합니다.

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
