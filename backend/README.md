# DKU Campus Map Backend - Week 3

이 백엔드는 `DKU_Map_W3toW8.docx`의 **3주차 범위만** 구현한 FastAPI 프로젝트입니다.

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

## 아직 구현하지 않는 범위

- 실내 Dijkstra 완성
- 실외 길찾기 완성
- 통합 `POST /api/routes`
- JWT 로그인
- 이메일 인증
- TMI 제보 API
- 관리자 승인 API

위 기능들은 문서 기준 5~7주차 작업입니다.

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
