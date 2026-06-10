// 백엔드 API 클라이언트
// 규격: WEEK8_FRONTEND_API_CONTRACT.md
// 백엔드 응답은 snake_case / camelCase가 endpoint마다 섞여 있으므로,
// 이 파일의 어댑터에서 프론트 타입(lib/data.ts, data/mock.ts)으로 변환한다.

import type { Building, Room, IndoorMap, RoomPos } from './data'
import type { TmiCategory, TmiMarker } from '../data/mock'

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ??
  'http://127.0.0.1:8000'

/** `/maps/...` 같은 상대 경로를 백엔드 절대 URL로 변환. 이미 절대 URL이면 그대로. */
export const assetUrl = (path: string): string =>
  /^https?:\/\//.test(path) ? path : `${API_BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`

// ---- 인증 토큰 (localStorage) ----
const TOKEN_KEY = 'dku_access_token'
export const getToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}
export const setToken = (token: string | null): void => {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* localStorage 접근 불가 시 무시 */
  }
}

// ---- 공통 에러 ----
export class ApiError extends Error {
  status: number
  code?: string
  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

interface FetchOpts {
  method?: string
  body?: unknown
  auth?: boolean
  query?: Record<string, string | number | boolean | undefined | null>
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function asRecord(v: unknown): Record<string, unknown> | null {
  return v && typeof v === 'object' ? (v as Record<string, unknown>) : null
}

/** 백엔드 에러 포맷 정규화: { detail: { errorCode, message } } | { detail: { errors:[...] } } | { detail: "..." } */
function toApiError(data: unknown, status: number): ApiError {
  const root = asRecord(data)
  const detail = root?.detail
  if (typeof detail === 'string') return new ApiError(detail, status)
  const d = asRecord(detail)
  if (d) {
    if (typeof d.message === 'string') {
      return new ApiError(d.message, status, typeof d.errorCode === 'string' ? d.errorCode : undefined)
    }
    if (Array.isArray(d.errors) && d.errors.length > 0) {
      const first = asRecord(d.errors[0])
      const msg = typeof first?.message === 'string' ? first.message : '요청을 처리할 수 없습니다.'
      const code = typeof first?.errorCode === 'string' ? first.errorCode : undefined
      return new ApiError(msg, status, code)
    }
  }
  return new ApiError(`요청을 처리할 수 없습니다. (${status})`, status)
}

async function apiFetch<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  const { method = 'GET', body, auth = false, query } = opts
  let url = `${API_BASE_URL}${path}`
  if (query) {
    const qs = Object.entries(query)
      .filter(([, v]) => v !== undefined && v !== null && v !== '')
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
      .join('&')
    if (qs) url += `?${qs}`
  }

  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth) {
    const t = getToken()
    if (t) headers['Authorization'] = `Bearer ${t}`
  }

  let res: Response
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError('서버에 연결할 수 없습니다. 네트워크 또는 백엔드 주소를 확인해주세요.', 0)
  }

  const text = await res.text()
  const data = text ? safeJson(text) : null
  if (!res.ok) throw toApiError(data, res.status)
  return data as T
}

// =====================================================================
// 인증
// =====================================================================

export interface ApiUser {
  user_id: string
  studentId: string
  nickname: string
  role: string
  created_at: string
}

interface AuthResponse {
  accessToken: string
  tokenType: string
  user: ApiUser
}

export async function register(studentId: string, password: string): Promise<AuthResponse> {
  const data = await apiFetch<AuthResponse>('/api/auth/register', {
    method: 'POST',
    body: { studentId, password },
  })
  setToken(data.accessToken)
  return data
}

export async function login(studentId: string, password: string): Promise<AuthResponse> {
  const data = await apiFetch<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: { studentId, password },
  })
  setToken(data.accessToken)
  return data
}

export async function fetchMe(): Promise<ApiUser> {
  return apiFetch<ApiUser>('/api/auth/me', { auth: true })
}

// =====================================================================
// 건물 / 층 / 실내지도  (→ 프론트 Building/IndoorMap/Room 타입으로 변환)
// =====================================================================

interface ApiBuilding {
  building_id: string
  name: string
  short_code: string
  latitude: number
  longitude: number
  main_outdoor_node_id?: string | null
  description?: string | null
  aliases?: { alias: string; priority?: number }[]
}

/** description="category=software; has_indoor_map=TRUE" → "software" */
function parseCategory(desc?: string | null): string {
  if (!desc) return ''
  const m = desc.match(/category=([^\s;,]+)/)
  return m ? m[1] : desc
}

function parseHasIndoorMap(desc?: string | null): boolean {
  return !!desc && /has_indoor_map\s*=\s*true/i.test(desc)
}

/** 백엔드 polygon_points는 "x1,y1;x2,y2;..." 문자열이거나 number[][]일 수 있다. number[][]로 정규화. */
function parsePolygon(raw: number[][] | string | null | undefined): number[][] | null {
  if (!raw) return null
  if (Array.isArray(raw)) return raw.length >= 3 ? raw : null
  const pts = raw
    .split(';')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((pair) => pair.split(',').map((n) => Number(n)))
    .filter((p) => p.length === 2 && p.every((n) => !Number.isNaN(n)))
  return pts.length >= 3 ? pts : null
}

export interface FetchedBuildings {
  buildings: Building[]
  aliases: { alias: string; buildingId: string }[]
}

export async function fetchBuildings(): Promise<FetchedBuildings> {
  const list = await apiFetch<ApiBuilding[]>('/api/buildings')
  const buildings: Building[] = list.map((b) => ({
    id: b.building_id,
    code: b.short_code,
    name: b.name,
    lat: b.latitude,
    lng: b.longitude,
    category: parseCategory(b.description),
    floorsAbove: 0,
    floorsBelow: 0,
    hasIndoorMap: parseHasIndoorMap(b.description),
  }))
  const aliases = list.flatMap((b) =>
    (b.aliases ?? []).map((a) => ({ alias: a.alias, buildingId: b.building_id })),
  )
  return { buildings, aliases }
}

interface ApiFloor {
  indoor_map_id: string
  building_id: string
  floor_number: number
  floor_label: string
  map_file_url: string
  status?: string
}

export async function fetchFloors(buildingId: string): Promise<IndoorMap[]> {
  const list = await apiFetch<ApiFloor[]>(`/api/buildings/${buildingId}/floors`)
  return list.map((f) => ({
    buildingId: f.building_id,
    floor: f.floor_number,
    floorLabel: f.floor_label,
    image: assetUrl(f.map_file_url),
    canvasWidth: 1000,
    canvasHeight: 707,
  }))
}

interface ApiRoomPosition {
  room_id: string
  x: number
  y: number
  width: number
  height: number
  polygon_points?: number[][] | string | null
  center_x: number
  center_y: number
}

interface ApiRoom {
  room_id: string
  building_id: string
  floor_number: number
  floor_label?: string
  room_number: string
  room_code?: string | null
  name?: string | null
  room_type?: string | null
  description?: string | null
}

interface ApiIndoorMap {
  indoor_map_id: string
  building_id: string
  floor_number: number
  floor_label: string
  map_file_url: string
  canvas_width?: number | null
  canvas_height?: number | null
  rooms: ApiRoom[]
  room_positions: ApiRoomPosition[]
  indoor_nodes?: unknown[]
  indoor_edges?: unknown[]
}

export interface FetchedIndoorMap {
  map: IndoorMap
  rooms: Room[]
}

export async function fetchIndoorMap(buildingId: string, floor: number): Promise<FetchedIndoorMap> {
  const d = await apiFetch<ApiIndoorMap>(`/api/buildings/${buildingId}/floors/${floor}/indoor-map`)
  const map: IndoorMap = {
    buildingId: d.building_id,
    floor: d.floor_number,
    floorLabel: d.floor_label,
    image: assetUrl(d.map_file_url),
    canvasWidth: d.canvas_width ?? 1000,
    canvasHeight: d.canvas_height ?? 707,
  }
  const posByRoom = new Map(d.room_positions.map((p) => [p.room_id, p]))
  const rooms: Room[] = d.rooms.map((r) => {
    const p = posByRoom.get(r.room_id)
    const pos: RoomPos | null = p
      ? {
          x: p.x,
          y: p.y,
          width: p.width,
          height: p.height,
          cx: p.center_x,
          cy: p.center_y,
          polygon: parsePolygon(p.polygon_points),
        }
      : null
    const name = r.name ?? r.description ?? ''
    return {
      id: r.room_id,
      buildingId: r.building_id,
      floor: r.floor_number,
      floorLabel: r.floor_label ?? d.floor_label,
      number: r.room_number,
      name,
      type: r.room_type ?? '',
      displayName: `${map.floorLabel} ${r.room_number}${name ? ` (${name})` : ''}`,
      pos,
    }
  })
  return { map, rooms }
}

// =====================================================================
// 강의실 검색
// =====================================================================

export interface RoomSearchResult {
  roomId: string
  roomCode: string
  buildingId: string
  buildingName: string
  floorNumber: number
  floorLabel: string
  roomNumber: string
  nearestIndoorNodeId?: string
}

export async function searchRooms(keyword: string, limit = 50): Promise<RoomSearchResult[]> {
  return apiFetch<RoomSearchResult[]>('/api/rooms', { query: { keyword, limit } })
}

export async function fetchRoomDetail(roomId: string): Promise<RoomSearchResult> {
  return apiFetch<RoomSearchResult>(`/api/rooms/${encodeURIComponent(roomId)}`)
}

/** keyword로 강의실 1건 검색. 없으면 null. */
export async function searchRoom(keyword: string): Promise<RoomSearchResult | null> {
  try {
    const d = await apiFetch<RoomSearchResult>('/api/rooms/search', { query: { keyword } })
    return d
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.code === 'ROOM_NOT_FOUND')) return null
    throw e
  }
}

// =====================================================================
// 통합 길찾기
// =====================================================================

export interface RoutePreferences {
  avoidStairs: boolean
  avoidSlope: boolean
  preferIndoor: boolean
  accessibilityMode: boolean
  rainMode: boolean
}

export const DEFAULT_PREFERENCES: RoutePreferences = {
  avoidStairs: false,
  avoidSlope: false,
  preferIndoor: false,
  accessibilityMode: false,
  rainMode: false,
}

export type RouteSegmentType = 'INDOOR' | 'OUTDOOR' | 'VERTICAL'

export interface RoutePathPoint {
  nodeId?: string
  sourceEdgeId?: string
  pointType?: string
  x?: number
  y?: number
  latitude?: number
  longitude?: number
  floorNumber?: number
  indoorMapId?: string
  label?: string
}

export interface RouteSegment {
  type: RouteSegmentType
  buildingId?: string
  floorNumber?: number
  toFloorNumber?: number
  indoorMapId?: string
  transitionType?: string
  instruction?: string
  nodeIds?: string[]
  edgeIds?: string[]
  pathPoints?: RoutePathPoint[]
}

export interface RouteResult {
  routeType: string
  title: string
  totalCost: number
  totalDistance: number
  totalEstimatedTime: number
  reason?: string
  segments: RouteSegment[]
}

export interface RouteRequest {
  start: string
  destination: string
  routeTypes?: string[]
  preferences?: Partial<RoutePreferences>
}

export async function fetchRoutes(req: RouteRequest): Promise<RouteResult[]> {
  return apiFetch<RouteResult[]>('/api/routes', {
    method: 'POST',
    body: {
      start: req.start,
      destination: req.destination,
      routeTypes: req.routeTypes ?? ['DEFAULT', 'COMFORTABLE', 'RAINY'],
      preferences: { ...DEFAULT_PREFERENCES, ...(req.preferences ?? {}) },
    },
  })
}

export interface IndoorRouteRequest {
  fromRoomId: string
  toRoomId: string
  routeType?: string
  preferences?: Partial<RoutePreferences>
}

/** 같은(또는 연결된) 건물 내 호실→호실 실내 경로. 단일 결과 반환. */
export async function fetchIndoorRoute(req: IndoorRouteRequest): Promise<RouteResult> {
  return apiFetch<RouteResult>('/api/routes/indoor', {
    method: 'POST',
    body: {
      fromRoomId: req.fromRoomId,
      toRoomId: req.toRoomId,
      routeType: req.routeType ?? 'DEFAULT',
      preferences: { ...DEFAULT_PREFERENCES, ...(req.preferences ?? {}) },
    },
  })
}

// =====================================================================
// TMI
// =====================================================================

interface ApiTmi {
  tmi_location_id: string
  name: string
  location_type: string
  building_id?: string | null
  room_id?: string | null
  indoor_map_id?: string | null
  floor_number?: number | null
  latitude?: number | null
  longitude?: number | null
  map_x?: number | null
  map_y?: number | null
  representative_tags?: string | null
  status?: string
  verified_count?: number
  created_by?: string | null
  created_at?: string
}

/** 태그 문자열로 프론트 카테고리(필터/색상)를 추정한다. 백엔드에 category 필드가 없기 때문. */
function guessCategory(tags: string[], locationType: string): TmiCategory {
  const t = tags.join(' ')
  if (/비|우천|우산|통로/.test(t)) return 'rain'
  if (/편의점|카페|식당|매점|24시간|편의/.test(t)) return 'facility'
  if (/콘센트|휴식|조용|쉬|벤치|쉼/.test(t)) return 'rest'
  if (/강의실|호실|수업|강의/.test(t) || locationType === 'INDOOR') return 'classroom'
  return 'tmi'
}

function adaptTmi(t: ApiTmi): TmiMarker | null {
  // 외부 지도(Kakao) 표시는 위경도가 필요하다. 없으면 마커로 그릴 수 없어 제외.
  if (t.latitude == null || t.longitude == null) return null
  const tags = (t.representative_tags ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
  return {
    id: t.tmi_location_id,
    name: t.name,
    category: guessCategory(tags, t.location_type),
    lat: t.latitude,
    lng: t.longitude,
    tags,
    content: '', // 목록 응답에는 본문이 없다. 상세에서 보강 가능.
    author: t.created_by ?? '익명',
  }
}

export interface TmiFilter {
  location_type?: string
  building_id?: string
  tag?: string
}

export async function fetchTmi(filter: TmiFilter = {}): Promise<TmiMarker[]> {
  const list = await apiFetch<ApiTmi[]>('/api/tmi', {
    query: {
      location_type: filter.location_type,
      building_id: filter.building_id,
      tag: filter.tag,
    },
  })
  return list.map(adaptTmi).filter((m): m is TmiMarker => m !== null)
}

export interface CreateTmiInput {
  name: string
  locationType: 'INDOOR' | 'OUTDOOR'
  buildingId?: string | null
  roomId?: string | null
  indoorMapId?: string | null
  floorNumber?: number | null
  latitude?: number | null
  longitude?: number | null
  mapX?: number | null
  mapY?: number | null
  representativeTags?: string
}

export async function createTmi(input: CreateTmiInput): Promise<ApiTmi> {
  return apiFetch<ApiTmi>('/api/tmi', { method: 'POST', auth: true, body: input })
}

// =====================================================================
// 제보
// =====================================================================

export interface CreateReportInput {
  reportType: string
  targetType: string
  targetId?: string | null
  tmiLocationId?: string | null
  buildingId?: string | null
  roomId?: string | null
  title: string
  content: string
  tags?: string
}

export async function createReport(input: CreateReportInput): Promise<unknown> {
  return apiFetch('/api/reports', { method: 'POST', auth: true, body: input })
}
