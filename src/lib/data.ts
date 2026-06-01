import raw from '../data/dku-data.json'

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
export const buildings = data.buildings
export const aliases = data.aliases
export const rooms = data.rooms
export const indoorMaps = data.indoorMaps

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

export const roomById = (id: string) => rooms.find((r) => r.id === id)

/** 건물 약칭 → buildingId (소프트→DKU_ICT 등) */
const aliasMap: Record<string, string> = {}
for (const a of aliases) aliasMap[a.alias.replace(/\s/g, '')] = a.buildingId
for (const b of buildings) {
  aliasMap[b.name.replace(/\s/g, '')] = b.id
  aliasMap[b.code.replace(/\s/g, '')] = b.id
}

export interface SearchHit {
  kind: 'room' | 'building'
  building: Building
  room?: Room
  title: string
  subtitle: string
}

/**
 * "소프트305", "사범 104", "퇴계기념중앙도서관", "305" 등 자유 입력 검색.
 * 약칭/건물명 + 호실 패턴을 분리해 매칭.
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
