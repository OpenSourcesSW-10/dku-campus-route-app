import raw from '../data/dku-data.json'
import {
  fetchBuildings,
  fetchFloors,
  fetchIndoorMap,
  searchRoom,
  searchRooms,
  type RoomSearchResult,
} from './api'

export interface Building {
  id: string
  code: string
  name: string
  lat: number
  lng: number
  category: string
  floorsAbove: number
  floorsBelow: number
  hasIndoorMap: boolean
}

export interface RoomPos {
  x: number
  y: number
  width: number
  height: number
  cx: number
  cy: number
  polygon: number[][] | null
}

export interface Room {
  id: string
  buildingId: string
  floor: number
  floorLabel: string
  number: string
  name: string
  type: string
  displayName: string
  pos: RoomPos | null
}

export interface IndoorMap {
  buildingId: string
  floor: number
  floorLabel: string
  image: string
  canvasWidth: number
  canvasHeight: number
}

export interface Alias {
  alias: string
  buildingId: string
}

const data = raw as unknown as {
  canvas: { width: number; height: number }
  buildings: Building[]
  aliases: Alias[]
  rooms: Room[]
  indoorMaps: IndoorMap[]
}

export const CANVAS = data.canvas

// 로컬 JSON을 기본값으로 보유하고, 부트스트랩에서 API 데이터로 in-place 갱신한다.
// (백엔드 데이터가 비어있거나 연결 실패해도 로컬 데이터로 동작하는 하이브리드 구조)
export const buildings: Building[] = [...data.buildings]
export const aliases: Alias[] = [...data.aliases]
export const rooms: Room[] = [...data.rooms]
export const indoorMaps: IndoorMap[] = [...data.indoorMaps]

export const buildingById = (id: string) => buildings.find((b) => b.id === id)

export const indoorMapsOf = (buildingId: string) =>
  indoorMaps
    .filter((m) => m.buildingId === buildingId)
    .sort((a, b) => a.floor - b.floor)

/** 건물 진입 시 기본 층: 1층이 있으면 1층, 없으면 가장 낮은 층 */
export const defaultFloor = (buildingId: string) => {
  const maps = indoorMapsOf(buildingId)
  return (maps.find((m) => m.floor === 1) ?? maps[0])?.floor
}

export const indoorMap = (buildingId: string, floor: number) =>
  indoorMaps.find((m) => m.buildingId === buildingId && m.floor === floor)

export const roomsOf = (buildingId: string, floor: number) =>
  rooms.filter((r) => r.buildingId === buildingId && r.floor === floor)

/** 건물 전체 호실(전 층) — 실내 길찾기 출발/도착 호실 선택용 */
export const roomsOfBuilding = (buildingId: string) =>
  rooms
    .filter((r) => r.buildingId === buildingId)
    .sort((a, b) => a.floor - b.floor || a.number.localeCompare(b.number, undefined, { numeric: true }))

export const roomById = (id: string) => rooms.find((r) => r.id === id)

/** 건물 약칭 → buildingId (소프트→DKU_ICT 등) */
let aliasMap: Record<string, string> = {}
function rebuildAliasMap() {
  const next: Record<string, string> = {}
  for (const a of aliases) next[a.alias.replace(/\s/g, '')] = a.buildingId
  for (const b of buildings) {
    next[b.name.replace(/\s/g, '')] = b.id
    next[b.code.replace(/\s/g, '')] = b.id
  }
  aliasMap = next
}
rebuildAliasMap()

// =====================================================================
// API 하이드레이션 (부트스트랩 시 1회 호출)
// =====================================================================

/** 건물/별칭 목록을 백엔드에서 받아 로컬 데이터와 병합한다. 실패 시 로컬 유지. */
export async function hydrateBuildings(): Promise<void> {
  try {
    const { buildings: apiBuildings, aliases: apiAliases } = await fetchBuildings()
    if (apiBuildings.length === 0) return

    const localById = new Map(buildings.map((b) => [b.id, b]))
    const merged: Building[] = apiBuildings.map((b) => {
      const local = localById.get(b.id)
      // 실내 안내도 관련 정보(층수/안내도 보유)는 로컬 큐레이션 값을 유지한다.
      return local
        ? {
            ...b,
            category: b.category || local.category,
            code: b.code || local.code,
            floorsAbove: local.floorsAbove,
            floorsBelow: local.floorsBelow,
            hasIndoorMap: local.hasIndoorMap,
          }
        : b
    })
    // 백엔드에 누락된 로컬 전용 건물도 보존
    for (const local of buildings) {
      if (!merged.some((m) => m.id === local.id)) merged.push(local)
    }
    buildings.splice(0, buildings.length, ...merged)

    const key = (a: Alias) => `${a.alias}|${a.buildingId}`
    const seen = new Set(aliases.map(key))
    for (const a of apiAliases) {
      if (!seen.has(key(a))) {
        aliases.push(a)
        seen.add(key(a))
      }
    }
    rebuildAliasMap()
  } catch {
    /* 백엔드 연결 실패 → 로컬 데이터 그대로 사용 */
  }
}

// =====================================================================
// 실내 지도 (API 우선, 로컬 폴백)
// =====================================================================

export interface IndoorMapData {
  map: IndoorMap
  rooms: Room[]
}

function localIndoorMapData(buildingId: string, floor: number): IndoorMapData | null {
  const map = indoorMap(buildingId, floor)
  if (!map) return null
  return { map, rooms: roomsOf(buildingId, floor) }
}

function upsertIndoorMaps(nextMaps: IndoorMap[]) {
  for (const next of nextMaps) {
    const index = indoorMaps.findIndex((m) => m.buildingId === next.buildingId && m.floor === next.floor)
    if (index >= 0) indoorMaps[index] = { ...indoorMaps[index], ...next }
    else indoorMaps.push(next)
  }
}

function upsertRooms(nextRooms: Room[]) {
  for (const next of nextRooms) {
    const index = rooms.findIndex((r) => r.id === next.id)
    if (index >= 0) rooms[index] = { ...rooms[index], ...next }
    else rooms.push(next)
  }
}

/** 건물의 층별 실내지도 목록을 API 우선으로 로드한다. */
export async function loadIndoorMaps(buildingId: string): Promise<IndoorMap[]> {
  try {
    const apiFloors = await fetchFloors(buildingId)
    if (apiFloors.length > 0) {
      upsertIndoorMaps(apiFloors)
      return indoorMapsOf(buildingId)
    }
  } catch {
    /* 백엔드 연결 실패 → 로컬 층 목록 사용 */
  }
  return indoorMapsOf(buildingId)
}

/**
 * 층 실내 지도 + 강의실을 로드한다.
 * 최종 DB가 있으면 API 데이터를 우선 사용하고, 백엔드 연결 실패 시 로컬 데이터로 폴백한다.
 */
export async function loadIndoorMap(buildingId: string, floor: number): Promise<IndoorMapData | null> {
  try {
    const api = await fetchIndoorMap(buildingId, floor)
    if (api) {
      upsertIndoorMaps([api.map])
      upsertRooms(api.rooms)
      return api
    }
  } catch {
    /* 백엔드 연결 실패 → 로컬 안내도 사용 */
  }
  return localIndoorMapData(buildingId, floor)
}

// =====================================================================
// 검색
// =====================================================================

export interface SearchHit {
  kind: 'room' | 'building'
  building: Building
  room?: Room
  title: string
  subtitle: string
}

/**
 * "소프트305", "사범 104", "퇴계기념중앙도서관", "305" 등 자유 입력 검색.
 * 약칭/건물명 + 호실 패턴을 분리해 매칭. (로컬 데이터 기준 — 즉시 응답)
 */
export function search(query: string): SearchHit[] {
  const q = query.trim()
  if (!q) return []
  const compact = q.replace(/\s/g, '')

  // 1) 약칭/건물명 + 호실번호 분리 (예: 소프트305, 사범104-1)
  const m = compact.match(/^(.+?)(\d[\d-]*)$/)
  const hits: SearchHit[] = []
  const seen = new Set<string>()

  const pushRoom = (r: Room) => {
    if (seen.has(r.id)) return
    seen.add(r.id)
    const b = buildingById(r.buildingId)
    if (!b) return
    hits.push({
      kind: 'room',
      building: b,
      room: r,
      title: `${b.name} ${r.number}호`,
      subtitle: r.name || '단국대 죽전캠퍼스 강의실',
    })
  }

  if (m) {
    const namePart = m[1]
    const numPart = m[2]
    const bid = aliasMap[namePart] ?? findBuildingByPartial(namePart)?.id
    for (const r of rooms) {
      if (r.number.replace(/\s/g, '') !== numPart) continue
      if (bid && r.buildingId !== bid) continue
      pushRoom(r)
    }
  }

  // 2) 순수 호실 번호만 입력 (예: 305)
  if (/^\d[\d-]*$/.test(compact)) {
    for (const r of rooms) if (r.number.replace(/\s/g, '') === compact) pushRoom(r)
  }

  // 3) 건물명/약칭 부분일치 → 건물 + 그 건물 강의실 일부
  const matchedBuildings = buildings.filter(
    (b) =>
      b.name.replace(/\s/g, '').includes(compact) ||
      Object.entries(aliasMap).some(([al, id]) => id === b.id && al.includes(compact)),
  )
  for (const b of matchedBuildings) {
    const key = 'B:' + b.id
    if (!seen.has(key)) {
      seen.add(key)
      hits.push({
        kind: 'building',
        building: b,
        title: b.name,
        subtitle: '단국대 죽전캠퍼스 주요 장소',
      })
    }
  }

  // 4) 강의실명(room.name) 부분일치
  if (compact.length >= 2) {
    for (const r of rooms) {
      if (r.name && r.name.replace(/\s/g, '').includes(compact)) pushRoom(r)
    }
  }

  return hits.slice(0, 30)
}

function findBuildingByPartial(s: string): Building | undefined {
  return buildings.find((b) => b.name.replace(/\s/g, '').includes(s))
}

/** API 강의실 검색 결과를 SearchHit로 변환 (로컬 검색에서 못 찾았을 때 보강용) */
function apiRoomToHit(r: RoomSearchResult): SearchHit {
  const b: Building =
    buildingById(r.buildingId) ?? {
      id: r.buildingId,
      code: '',
      name: r.buildingName,
      lat: 0,
      lng: 0,
      category: '',
      floorsAbove: 0,
      floorsBelow: 0,
      hasIndoorMap: true,
    }
  const room: Room = {
    id: r.roomId,
    buildingId: r.buildingId,
    floor: r.floorNumber,
    floorLabel: r.floorLabel,
    number: r.roomNumber,
    name: '',
    type: '',
    displayName: `${r.floorLabel} ${r.roomNumber}`,
    pos: null,
  }
  return {
    kind: 'room',
    building: b,
    room,
    title: `${r.buildingName} ${r.roomNumber}호`,
    subtitle: r.roomCode || '단국대 죽전캠퍼스 강의실',
  }
}

/**
 * 로컬 검색 결과와 백엔드 강의실 DB 검색 결과를 병합한다.
 * 최종 DB의 공학관 전체 강의실처럼 로컬 JSON에 없는 데이터도 검색 결과에 포함한다.
 */
export async function searchPlaces(query: string): Promise<SearchHit[]> {
  const local = search(query)
  const q = query.trim()
  if (!q) return local
  const seen = new Set(local.map((hit) => hit.room?.id ?? `B:${hit.building.id}`))
  try {
    const apiRooms = await searchRooms(q, 80)
    const apiHits = apiRooms
      .map(apiRoomToHit)
      .filter((hit) => {
        const key = hit.room?.id ?? `B:${hit.building.id}`
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
    return [...local, ...apiHits].slice(0, 80)
  } catch {
    try {
      const r = await searchRoom(q)
      if (!r) return local
      const hit = apiRoomToHit(r)
      const key = hit.room?.id ?? `B:${hit.building.id}`
      return seen.has(key) ? local : [...local, hit]
    } catch {
      return local
    }
  }
}
