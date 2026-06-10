# DKU MAP — 단국대 죽전캠퍼스 길찾기

React + Vite + TypeScript + Tailwind CSS 기반 모바일 반응형 웹 앱입니다.
FastAPI 백엔드와 연동해 건물 조회, 강의실 검색, 실내지도, 길찾기, TMI, 제보 기능을 제공합니다.
백엔드 연결 실패나 미지원 데이터는 제출 시연 안정성을 위해 로컬 fallback 데이터를 사용합니다.

## 실행

> Node 20 이상 환경을 권장합니다.

```bash
npm install
cp .env.example .env      # .env에 카카오 JS 키와 백엔드 API 주소 입력
npm run dev               # http://localhost:5190
```

빌드: `npm run build` · 미리보기: `npm run preview`

## ⚠️ 카카오 지도 도메인 등록 (필수)

지도가 "지도를 불러오지 못했습니다"로 뜨면 **도메인 등록**이 안 된 것입니다.

1. [카카오 developers](https://developers.kakao.com) > 내 애플리케이션 > 해당 앱
2. **앱 설정 > 플랫폼 > Web > 사이트 도메인**에 아래를 추가
   ```
   http://localhost:5190
   https://tmimvp.vercel.app
   ```
3. 저장 후 새로고침

> 개발 포트는 `vite.config.ts`에서 `5190`으로 고정돼 있습니다. (등록 도메인과 포트를 일치시키기 위함)

## 환경변수

로컬 `.env` 또는 Vercel 환경변수에 아래 값을 설정합니다.

```env
VITE_KAKAO_JS_KEY=카카오_JavaScript_키
VITE_API_BASE_URL=https://dku-campus-route-backend.onrender.com
```

로컬 백엔드를 직접 실행할 때는 `VITE_API_BASE_URL=http://127.0.0.1:8000`으로 변경할 수 있습니다.

## 구현 범위

| 기능 | 설명 |
| --- | --- |
| 진입/로그인 | 스플래시 → 랜딩 → 학번 기반 회원가입/로그인, JWT 토큰 저장 |
| 외부 길찾기 | Kakao Map 위에 백엔드 `/api/routes` 결과의 외부 경로 Polyline 표시 |
| 장소 검색 | "소프트305", "도서관201", 건물명 등 검색 → 실내지도/강의실 위치 연결 |
| 강의실 정보(실내지도) | 건물 → 층 선택 → 안내도 표시 + 강의실 하이라이트 + 백엔드 실내 경로선 |
| TMI 정보 | 승인된 TMI 마커 조회, 카테고리 필터, 마커 팝업 |
| 제보하기 | 로그인 사용자 기준 TMI/강의실 정보 제보 등록 |

- 최종 시연은 **ICT관·도서관 중심**으로 검증합니다.
- 제1/2/3공학관 구름다리 데이터는 백엔드 데이터에 반영되어 있으나, 강의실 검색 데이터 범위에 따라 시연 범위가 제한될 수 있습니다.
- GPS 기반 현재 위치 자동 전환은 최종 제출 범위에서 제외했습니다.

## 데이터

원본 엑셀(`scripts/source/`)을 `scripts/gen_data.py`로 변환해
`src/data/dku-data.json`을 생성합니다. 좌표/건물 데이터가 갱신되면:

```bash
python3 scripts/gen_data.py
```

- 좌표 캔버스 기준: **1000 × 707** (제공된 안내도 PNG와 1:1 정렬)
- 안내도 이미지: `public/floorplans/{ICT,LIB}/`

## 구조

```
src/
  pages/        # 화면 (Splash, Landing, Login, MapHome, RouteFind, PlaceSearch,
                #        IndoorMapPage, Tmi, Report ...)
  features/
    map/        # 카카오맵 로더 + 캠퍼스 지도
    indoor/     # 실내 안내도 뷰어 (SVG viewBox 스케일 + 하이라이트 + 경로선)
  components/   # Drawer, TopBar, StatusBar, Icons
  data/         # dku-data.json(로컬 fallback) + mock.ts(경로/TMI fallback)
  lib/api.ts    # FastAPI 백엔드 API 클라이언트
  lib/data.ts   # 로컬 데이터 + 백엔드 데이터 병합, 검색
  store/        # zustand (JWT 인증/길찾기 상태)
```
