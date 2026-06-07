# 8주차 최종 백엔드 제출 정리

## 구현 완료 범위

- FastAPI 기반 백엔드 API 서버
- SQLAlchemy 기반 DB 모델
- Pydantic 기반 요청/응답 schema
- 건물/강의실 검색 API
- 층별 실내 지도, 강의실 좌표, 실내 노드/간선 조회
- 실내 Dijkstra 경로 계산
- 외부 Dijkstra 경로 계산
- 실내-외부-실내 통합 경로 계산
- Dynamic Cost Function 기반 기본 경로/편한 길/비 오는 날 경로
- JWT 로그인
- Passlib/bcrypt 비밀번호 해싱
- 단국대 이메일 인증 코드 요청/검증
- TMI 위치 등록/조회 API
- 사용자 제보 등록/조회 API
- 관리자 승인/반려 API
- 승인된 TMI/제보만 일반 사용자에게 공개
- Render 배포 설정
- Vercel 프론트 연동용 CORS 설정
- 8주차 최종 readiness 점검 API
- GitHub DB 브랜치 참조 CSV 4종 DB 반영
- 참조 데이터 조회 API
- 외부 `polyline_points` import 및 정방향/역방향 상세 경로 응답
- 층별 `INDOOR` 및 층간 `VERTICAL` 경로 세그먼트
- 8주차 백엔드 P0 자동 통합 테스트
- 잘못된 임시 직선 경로를 반환하지 않는 명시적 경로 실패 처리

## 핵심 API

```text
GET /api/buildings
GET /api/rooms/search
GET /api/buildings/{building_id}/floors/{floor}/indoor-map
GET /api/outdoor/map
GET /api/reference-data
POST /api/routes

POST /api/auth/register
POST /api/auth/login
POST /api/auth/email/request
POST /api/auth/email/verify
GET /api/auth/me

GET /api/tmi
POST /api/tmi
GET /api/tmi/admin/list
PATCH /api/tmi/admin/{tmi_location_id}/status

GET /api/reports/approved
POST /api/reports
GET /api/reports/admin/list
PATCH /api/reports/admin/{report_id}/status

GET /api/status/readiness
```

## 제출 기준 상태

- 현재 경로 계산은 ICT관/도서관 중심의 실내외 그래프 자료를 기준으로 동작한다.
- 다른 건물은 DB 자료가 추가되면 같은 import 구조와 API로 확장 가능하다.
- DB 참조 테이블은 `edge_types`, `indoor_node_types`, `room_categories`, `entrance_master`를 기준으로 import한다.
- TMI/제보 기능은 로그인 및 이메일 인증을 통과한 사용자만 등록할 수 있다.
- 일반 사용자는 approved 또는 verified 상태의 TMI/제보만 조회할 수 있다.
- 관리자는 `ADMIN_EMAILS` 환경변수에 등록된 이메일로 가입하면 관리자 권한을 받는다.

## 최종 확인 명령

```powershell
cd backend
python tools/import_available_week7_data.py data/week7 --replace
python tools/week8_final_audit.py
python tools/week8_submission_test.py
uvicorn app.main:app --reload
```

DB 누락까지 모두 실패로 처리하는 엄격 검사는 다음과 같이 실행한다.

```powershell
python tools/week8_submission_test.py --strict
```

Swagger:

```text
http://127.0.0.1:8000/docs
```
