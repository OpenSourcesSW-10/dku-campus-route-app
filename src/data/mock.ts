// 목업 전용 하드코딩 데이터 (TMI 마커, 경로 옵션 등)
// 실제 길찾기/경로 계산은 백엔드 담당이며, 여기서는 화면 표시용 더미 데이터다.

export type TmiCategory = 'classroom' | 'rest' | 'tmi' | 'facility' | 'rain'

export interface TmiCategoryDef {
  key: TmiCategory
  label: string
  color: string
}

export const TMI_CATEGORIES: TmiCategoryDef[] = [
  { key: 'classroom', label: '강의실', color: '#BE3A60' },
  { key: 'rest', label: '휴식공간', color: '#F2B705' },
  { key: 'tmi', label: 'TMI', color: '#2E9E5B' },
  { key: 'facility', label: '편의시설', color: '#5BB8E8' },
  { key: 'rain', label: '비 오는 날 활로', color: '#9B8CE0' },
]

export interface TmiMarker {
  id: string
  name: string
  category: TmiCategory
  lat: number
  lng: number
  tags: string[]
  content: string
  author: string
}

export const TMI_MARKERS: TmiMarker[] = [
  {
    id: 'tmi_01',
    name: '퇴계기념중앙도서관 앞 벤치',
    category: 'rest',
    lat: 37.32128,
    lng: 127.12758,
    tags: ['쉬기 좋은 곳', '경치 구경하기 좋은 곳'],
    content: '날씨 좋을 때 앉아 쉬기 좋고, 오후엔 풍경이 잘 보여요.',
    author: 'user',
  },
  {
    id: 'tmi_02',
    name: '소프트웨어 ICT관 3층 휴게실',
    category: 'rest',
    lat: 37.32284,
    lng: 127.12728,
    tags: ['콘센트 있는 휴식공간', '조용한 곳'],
    content: '콘센트가 많고 사람이 적어서 과제하기 좋습니다.',
    author: 'user',
  },
  {
    id: 'tmi_03',
    name: '폭포공원',
    category: 'tmi',
    lat: 37.32035,
    lng: 127.1281,
    tags: ['고양이 자주 나타나는 곳', '사진 찍기 좋은 장소'],
    content: '점심시간에 고양이가 자주 출몰. 노을 사진 맛집.',
    author: 'user',
  },
  {
    id: 'tmi_04',
    name: 'GS25 죽전점',
    category: 'facility',
    lat: 37.32168,
    lng: 127.12705,
    tags: ['편의점', '24시간'],
    content: '캠퍼스 안에서 가장 가까운 편의점.',
    author: 'user',
  },
  {
    id: 'tmi_05',
    name: '소프트웨어 ICT관 ↔ 도서관 연결통로',
    category: 'rain',
    lat: 37.32205,
    lng: 127.12742,
    tags: ['비 오는 날 이동하기 좋은 통로'],
    content: '비 오는 날 우산 없이 두 건물 사이를 이동할 수 있어요.',
    author: 'user',
  },
  {
    id: 'tmi_06',
    name: '소프트웨어 ICT관 305호',
    category: 'classroom',
    lat: 37.32287,
    lng: 127.12733,
    tags: ['콘센트 많음', '화면 잘 보임'],
    content: '중간 오른쪽 자리가 화면이 가장 잘 보입니다.',
    author: 'user',
  },
]

// ---- 외부 길찾기 경로 옵션 (목업) ----
export type RouteType = 'fast' | 'comfort' | 'indoor'

export interface RouteOption {
  type: RouteType
  label: string
  color: string
  durationMin: number
  distanceM: number
  note: string
}

export const ROUTE_OPTIONS: RouteOption[] = [
  { type: 'fast', label: '빠른 길', color: '#BE3A60', durationMin: 6, distanceM: 420, note: '최단 거리 · 지름길 포함' },
  { type: 'comfort', label: '편한 길', color: '#2E9E5B', durationMin: 8, distanceM: 510, note: '계단 적고 완만함' },
  { type: 'indoor', label: '실내 위주', color: '#5B6BE8', durationMin: 9, distanceM: 560, note: '비 덜 맞는 실내 통로' },
]

export type LatLng = { lat: number; lng: number }

/**
 * 두 지점 사이 목업 경로 폴리라인 생성.
 * 옵션별로 약간 다른 경유점을 만들어 "다른 경로처럼" 보이게 한다. (실제 경로 아님)
 */
export function mockRoute(start: LatLng, dest: LatLng, type: RouteType): LatLng[] {
  const mx = (start.lng + dest.lng) / 2
  const my = (start.lat + dest.lat) / 2
  const dLng = dest.lng - start.lng
  const dLat = dest.lat - start.lat
  // 경로 타입별 수직 방향 오프셋
  const offset = type === 'fast' ? 0 : type === 'comfort' ? 0.0007 : -0.0007
  const ox = -dLat * (offset / (Math.hypot(dLat, dLng) || 1))
  const oy = dLng * (offset / (Math.hypot(dLat, dLng) || 1))
  const bend1: LatLng = { lat: start.lat + dLat * 0.33 + oy * 0.6, lng: start.lng + dLng * 0.33 + ox * 0.6 }
  const mid: LatLng = { lat: my + oy, lng: mx + ox }
  const bend2: LatLng = { lat: start.lat + dLat * 0.66 + oy * 0.6, lng: start.lng + dLng * 0.66 + ox * 0.6 }
  return [start, bend1, mid, bend2, dest]
}

// ---- 실내 경로선 (목업) : 안내도 좌표계(1000x707) 기준 폴리라인 ----
// ICT 3층: 엘리베이터 부근 → 305호 앞 복도 (대략값, 시연용)
export const INDOOR_ROUTE_DEMO: Record<string, { from: string; points: number[][] }> = {
  'DKU_ICT:3': {
    from: '엘리베이터',
    points: [
      [470, 470], // 엘리베이터 앞
      [470, 360],
      [560, 360], // 복도 합류
      [620, 230],
      [690, 150], // 305호 앞
    ],
  },
}
