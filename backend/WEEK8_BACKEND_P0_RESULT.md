# 8주차 백엔드 P0 구현 결과

## 구현 완료 내용

### 외부 상세 경로 좌표 지원

- `OutdoorEdge.polyline_points` 컬럼 추가
- SQLite 기존 DB에 `polyline_points` 자동 추가
- CSV/XLSX의 다음 컬럼명을 자동 인식

```text
polyline_points
geometry
path_points
shape_points
```

- 지원 입력 형식

```json
[[357,112],[359,120],[364,129]]
```

```json
[{"x":357,"y":112},{"x":359,"y":120},{"x":364,"y":129}]
```

```json
{"type":"LineString","coordinates":[[127.1,37.3],[127.2,37.4]]}
```

- 간선 정방향 이동 시 입력 좌표 순서 사용
- 간선 역방향 이동 시 상세 좌표 순서 자동 반전
- 상세 좌표가 없는 간선은 기존 시작·끝 노드 좌표 사용
- 외부 간선 데이터가 전혀 없으면 실제 길이 아닌 임시 직선을 만들지 않고 경로 없음 오류 반환
- 상세 좌표 중간점은 경로 응답에서 `pointType=SHAPE`로 구분
- 상세 좌표가 있으면 자동 거리 계산에도 활용
- 잘못된 상세 좌표 형식은 import 검증에서 오류로 보고

### 실내 층별 경로 분리

다층 실내 경로를 다음 세그먼트로 분리하도록 구현했습니다.

```text
INDOOR
VERTICAL
INDOOR
```

`VERTICAL` 세그먼트는 다음 정보를 반환합니다.

```text
floorNumber
toFloorNumber
indoorMapId
toIndoorMapId
transitionType
instruction
```

`transitionType`은 다음 값으로 구분됩니다.

```text
ELEVATOR
STAIRS
RAMP
VERTICAL
```

### DB 검증 강화

Import 및 readiness에서 다음 문제를 검사합니다.

- 존재하지 않는 노드를 참조하는 실내·외부 간선
- 서로 다른 건물을 연결하는 실내 간선
- 잘못된 종류의 층간 간선
- 다른 건물·층 노드에 연결된 강의실
- 고립된 실내·외부 노드
- 분리된 실내·외부 그래프
- 출입구의 잘못된 건물·층 연결
- 경로 그래프에서 고립된 출입구
- 출입구에서 도달할 수 없는 강의실
- 외부 `polyline_points` 적용률
- DB 참조 테이블 4종 import 여부

Readiness API:

```text
GET /api/status/readiness
```

기존 주소도 호환됩니다.

```text
GET /api/status/week8-readiness
```

### 제출 전 자동 테스트

다음 명령으로 백엔드 P0 제출 테스트를 실행할 수 있습니다.

```powershell
python tools/week8_submission_test.py
```

검사 내용:

- 루트, Swagger, 건물, 강의실 검색, 층별 실내 지도, 외부 지도 API 응답
- 참조 데이터 API 응답
- 캠퍼스 지도 이미지 응답
- ICT관 같은 층 경로
- ICT관 다층 경로
- 도서관 같은 층 경로
- 도서관 다층 경로
- ICT관에서 도서관 통합 경로
- 도서관에서 ICT관 통합 경로
- 층별 `INDOOR`와 `VERTICAL` 세그먼트
- 외부 `OUTDOOR` 세그먼트
- 모든 세그먼트의 `pathPoints`
- `polyline_points` 역방향 처리
- DB-backed 실내·외부 pathfinding 호환 함수
- 접근성 모드에서 계단 등 차단 간선 완전 제외
- 존재하지 않는 강의실 오류 응답
- 빈 출발지 오류 응답
- `nearest_indoor_node_id` 누락 오류 응답
- readiness 상태

현재 DB의 PARTIAL 항목까지 실패로 처리하려면 다음 명령을 사용합니다.

```powershell
python tools/week8_submission_test.py --strict
```

## 실제 데이터 검증 결과

현재 `backend/data/week7` 자료를 새 SQLite DB로 import한 결과:

```text
건물: 9
강의실: 208
실내 지도: 27
강의실 위치: 196
실내 노드: 145
실내 간선: 164
외부 노드: 19
외부 간선: 23
출입구 연결: 8
간선 타입 참조: 4
실내 노드 타입 참조: 6
공간 분류 참조: 28
출입구 기본 목록: 5
외부 polyline_points 적용 간선: 0
```

백엔드 P0 제출 테스트 결과:

```text
ICT관 같은 층 경로: 성공
ICT관 다층 경로: 성공
도서관 같은 층 경로: 성공
도서관 출입구 연결 그래프 내 다층 경로: 성공
ICT관 -> 도서관 통합 경로: 성공
도서관 -> ICT관 통합 경로: 성공
외부 상세 좌표 정방향/역방향 처리: 성공
```

## 현재 DB 자료에서 남은 문제

다음 문제는 백엔드 코드 문제가 아니라 DB 자료 보완이 필요한 항목입니다.

```text
외부 간선 23개 모두 polyline_points 미입력
일부 강의실 위치 좌표 누락
일부 강의실 nearest_indoor_node_id 누락
LIB_1_N070 고립 노드
도서관 실내 그래프 일부 연결 요소 분리
도서관 일부 강의실이 출입구 그래프에서 도달 불가능
```

기본 제출 테스트는 출입구와 연결된 실제 시연 가능 경로를 자동 선택하므로 성공합니다.
`--strict` 검사는 위 데이터 문제가 해결될 때까지 PARTIAL 상태로 실패합니다.

## 프론트 연동 시 사용할 정보

외부 경로:

```text
segments[].type == "OUTDOOR"
segments[].pathPoints
```

상세 곡선 중간점:

```text
pointType == "SHAPE"
sourceEdgeId == 상세 좌표가 속한 외부 간선 ID
```

실내 층별 경로:

```text
segments[].type == "INDOOR"
segments[].indoorMapId
segments[].floorNumber
segments[].pathPoints
```

층간 이동:

```text
segments[].type == "VERTICAL"
segments[].floorNumber
segments[].toFloorNumber
segments[].transitionType
segments[].instruction
```
