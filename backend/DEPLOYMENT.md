# Backend Deployment Guide

이 문서는 `tmimvp.vercel.app` 프론트엔드와 FastAPI 백엔드를 연결하기 위한 배포 절차를 정리한다.

## 배포 방식

현재 백엔드는 Render 배포를 기준으로 준비되어 있다.

- 배포 설정 파일: `render.yaml`
- 백엔드 루트: `backend`
- 시작 스크립트: `backend/tools/start_server.py`
- 배포 데이터: `backend/data/week7`

## Render 설정

1. Render에서 GitHub 저장소 `OpenSourcesSW-10/dku-campus-route-app`를 연결한다.
2. Blueprint 배포를 선택하면 루트의 `render.yaml`을 사용할 수 있다.
3. 배포 대상 브랜치는 `feature/backend-week7-integrated-route` 또는 PR 병합 후 `dev`를 선택한다.
4. 서비스가 생성되면 Render가 아래 명령을 실행한다.

```bash
pip install -r requirements.txt
python tools/start_server.py
```

`start_server.py`는 서버 시작 전에 `backend/data/week7` 자료를 SQLite DB로 import한 뒤 FastAPI를 실행한다.

## 필수 환경변수

```env
DATABASE_URL=sqlite:///./week8_backend.db
FRONTEND_ORIGINS=https://tmimvp.vercel.app,http://tmimvp.vercel.app,http://localhost:5173,http://127.0.0.1:5173
DEPLOYMENT_DATA_ROOT=data/week7
IMPORT_DATA_ON_START=true
DEBUG=false
JWT_SECRET_KEY=Render에서 생성하거나 직접 등록
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
ADMIN_STUDENT_IDS=관리자학번
```

## 프론트엔드 Vercel 설정

백엔드 배포가 끝나면 Render에서 발급된 URL을 프론트엔드 Vercel 환경변수에 등록한다.

```env
VITE_API_BASE_URL=https://배포된-백엔드-주소
```

예를 들어 Render URL이 `https://dku-campus-route-backend.onrender.com`이면 다음처럼 설정한다.

```env
VITE_API_BASE_URL=https://dku-campus-route-backend.onrender.com
```

## 배포 후 확인 API

아래 API가 정상 응답하면 프론트 연동이 가능하다.

```text
GET /
GET /api/buildings
GET /api/outdoor/map
GET /maps/campus-map.png
POST /api/routes
POST /api/auth/register
POST /api/auth/login
GET /api/auth/me
GET /api/tmi
POST /api/tmi
GET /api/tmi/admin/list
PATCH /api/tmi/admin/{tmiLocationId}/status
GET /api/reports/approved
POST /api/reports
GET /api/reports/admin/list
PATCH /api/reports/admin/{reportId}/status
GET /api/status/week8-readiness
```

## 주의사항

- Render 무료 플랜은 첫 요청 시 서버가 잠시 느리게 깨어날 수 있다.
- 현재 배포 데이터는 ICT관과 도서관 중심의 실내/외 경로 자료를 포함한다.
- 추후 DB 자료가 늘어나면 `backend/data/week7` 내부 CSV/지도 파일을 갱신한 뒤 다시 배포하면 된다.
