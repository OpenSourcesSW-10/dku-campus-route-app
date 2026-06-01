# DKU WAY — 단국대 죽전캠퍼스 길찾기 (프론트엔드 목업)

React + Vite + TypeScript + Tailwind CSS 기반 **모바일 반응형 웹 목업**입니다.
백엔드/DB 연동 없이 화면과 인터랙션을 하드코딩 데이터로 보여줍니다.

## 실행

```bash
npm install
cp .env.example .env      # .env에 카카오 JS 키 입력
npm run dev               # http://localhost:5190
```

빌드: `npm run build` · 미리보기: `npm run preview`

## ⚠️ 카카오 지도 도메인 등록 (필수)

지도가 "지도를 불러오지 못했습니다"로 뜨면 **도메인 등록**이 안 된 것입니다.

1. [카카오 developers](https://developers.kakao.com) > 내 애플리케이션 > 해당 앱
2. **앱 설정 > 플랫폼 > Web > 사이트 도메인**에 아래를 추가
   ```
   http://localhost:5190
   ```
3. 저장 후 새로고침

> 개발 포트는 `vite.config.ts`에서 `5190`으로 고정돼 있습니다. (등록 도메인과 포트를 일치시키기 위함)

## 구현 범위

| 기능 | 설명 |
| --- | --- |
| 진입/로그인 | 스플래시 → 랜딩 → 이메일 로그인·회원가입 (목업, 아무 값이나 통과) |
| 외부 길찾기 | 카카오맵 + 건물 마커 + 경로 옵션(빠른길/편한길/실내 위주) **표시용 목업** |
| 장소 검색 | "소프트305", "사범104", 건물명 등 검색 → 결과/페이지네이션 |
| 강의실 정보(실내지도) | 건물 → 층 선택 → 안내도 표시 + 강의실 **하이라이트** + 실내 경로선(목업) |
| TMI 정보 | 지도 마커 + 카테고리 필터 + 마커 팝업 |
| 제보하기 | 제보 폼 (목업) |

- **실내 하이라이트는 ICT관·도서관 전 층** 동작 (받은 좌표 기준).
- 길찾기/실내 경로 계산 로직은 백엔드 담당이며, 여기서는 표시만 합니다.

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
  data/         # dku-data.json(생성물) + mock.ts(TMI/경로 더미)
  lib/data.ts   # 데이터 로더 + 검색
  store/        # zustand (목업 인증/길찾기 상태)
```
