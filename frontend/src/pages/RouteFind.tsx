import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import CampusMap, { type RouteLine } from '../features/map/CampusMap'
import IndoorMap from '../features/indoor/IndoorMap'
import { BackIcon, CloseIcon, SearchIcon, PinIcon, LocateIcon } from '../components/Icons'
import { buildings, rooms, loadIndoorMap, type Building, type IndoorMapData } from '../lib/data'
import { useApp } from '../store/useApp'
import { ROUTE_OPTIONS, mockRoute, type LatLng } from '../data/mock'
import { CAMPUS_CENTER } from '../features/map/useKakao'
import { fetchRoutes, ApiError, type RouteResult } from '../lib/api'

const ENGINEERING_REPRESENTATIVE_ROOMS: Record<string, string> = {
  DKU_SCI1: '제1공301',
  DKU_SCI2: '제2공301',
  DKU_SCI3: '제3공319',
}

const ENGINEERING_ROOM_SUGGESTIONS = [
  '제1공301',
  '제1공학관301',
  '제2공301',
  '제2공학관301',
  '제3공319',
  '제3공학관319',
  'SCI1-3F-301',
  'SCI2-3F-301',
  'SCI3-3F-319',
]

function findBuilding(name: string): Building | undefined {
  if (!name || name === '내 위치') return undefined
  const compact = name.replace(/\s/g, '')
  return (
    buildings.find((x) => x.name.replace(/\s/g, '') === compact) ||
    buildings.find((x) => x.code.replace(/\s/g, '').toLowerCase() === compact.toLowerCase()) ||
    buildings.find((x) => compact.startsWith(x.code.replace(/\s/g, ''))) ||
    (compact.startsWith('제1공') ? buildings.find((x) => x.id === 'DKU_SCI1') : undefined) ||
    (compact.startsWith('제2공') ? buildings.find((x) => x.id === 'DKU_SCI2') : undefined) ||
    (compact.startsWith('제3공') ? buildings.find((x) => x.id === 'DKU_SCI3') : undefined) ||
    buildings.find((x) => compact.includes(x.name.replace(/\s/g, '')) || x.name.replace(/\s/g, '').includes(compact))
  )
}

function resolve(name: string): LatLng {
  const b = findBuilding(name)
  return b ? { lat: b.lat, lng: b.lng } : CAMPUS_CENTER
}

/**
 * 통합 길찾기 API는 건물명이 아니라 호실 식별자("ICT401")를 요구한다.
 * 건물을 대표 호실 코드로 변환한다. (백엔드 외부 그래프가 2층 이상에 연결돼 있어 2층 우선)
 * 로컬 호실 데이터가 있는 건물(ICT·도서관)만 변환 가능 — 그 외는 null → 목업 폴백.
 */
function representativeRoomCode(name: string): string | null {
  const b = findBuilding(name)
  if (!b) return null
  if (ENGINEERING_REPRESENTATIVE_ROOMS[b.id]) return ENGINEERING_REPRESENTATIVE_ROOMS[b.id]
  const inB = rooms.filter((r) => r.buildingId === b.id)
  if (inB.length === 0) return null
  const byFloor = (f: number) => inB.find((r) => r.floor === f)
  const r = byFloor(2) ?? byFloor(3) ?? byFloor(1) ?? inB.find((x) => x.floor > 0) ?? inB[0]
  return `${b.code}${r.number}`
}

function routeKeyword(name: string): string | null {
  if (!name || name === '내 위치') return null
  return representativeRoomCode(name) ?? name.replace(/\s/g, '')
}

// routeType(백엔드) → 화면 표시 메타
const ROUTE_META: Record<string, { label: string; color: string; note: string }> = {
  DEFAULT: { label: '기본 경로', color: '#BE3A60', note: '가장 기본적인 이동 비용 기준' },
  COMFORTABLE: { label: '편한 길', color: '#2E9E5B', note: '계단 적고 완만한 길' },
  RAINY: { label: '비 오는 날', color: '#5B6BE8', note: '비 덜 맞는 실내 위주' },
}

interface DisplayOption {
  key: string
  label: string
  color: string
  note: string
  durationMin: number
  distanceM: number
  line: LatLng[]
  route?: RouteResult
}

interface TotalStage {
  key: string
  kind: 'TOTAL'
  label: string
  instruction: string
}

interface IndoorStage {
  key: string
  kind: 'INDOOR'
  label: string
  buildingId: string
  floorNumber: number
  instruction: string
  routePoints: number[][]
}

interface VerticalStage {
  key: string
  kind: 'VERTICAL'
  label: string
  buildingId: string
  floorNumber: number
  instruction: string
  routePoints: number[][]
}

interface OutdoorStage {
  key: string
  kind: 'OUTDOOR'
  label: string
  instruction: string
  line: LatLng[]
}

type RouteStage = TotalStage | IndoorStage | VerticalStage | OutdoorStage

/** 통합 경로 응답에서 외부(OUTDOOR) 구간의 위경도 폴리라인을 추출 */
function outdoorLine(r: RouteResult): LatLng[] {
  const pts: LatLng[] = []
  for (const seg of r.segments) {
    if (seg.type !== 'OUTDOOR' || !seg.pathPoints) continue
    for (const p of seg.pathPoints) {
      if (p.latitude != null && p.longitude != null) pts.push({ lat: p.latitude, lng: p.longitude })
    }
  }
  return pts
}

/** 실내 전용 경로가 아닌데 외부 polyline이 없을 때만 쓰는 최소 fallback */
function indoorConnectionLine(r: RouteResult, start: LatLng, dest: LatLng): LatLng[] {
  const pts: LatLng[] = [start]
  let lastKey = `${start.lat},${start.lng}`
  for (const seg of r.segments) {
    if (!seg.buildingId) continue
    const b = buildings.find((x) => x.id === seg.buildingId)
    if (!b) continue
    const key = `${b.lat},${b.lng}`
    if (key !== lastKey) {
      pts.push({ lat: b.lat, lng: b.lng })
      lastKey = key
    }
  }
  const destKey = `${dest.lat},${dest.lng}`
  if (lastKey !== destKey) pts.push(dest)
  return pts.length >= 2 ? pts : [start, dest]
}

function displayLine(r: RouteResult, start: LatLng, dest: LatLng): LatLng[] {
  const outdoor = outdoorLine(r)
  return outdoor.length >= 2 ? outdoor : indoorConnectionLine(r, start, dest)
}

function hasBridgeSegment(r: RouteResult): boolean {
  return r.segments.some((seg) => seg.transitionType === 'BRIDGE' || seg.edgeIds?.some((id) => id.startsWith('SCI')))
}

function indoorRoutePoints(seg: RouteResult['segments'][number]): number[][] {
  return (seg.pathPoints ?? [])
    .filter((p) => p.x != null && p.y != null)
    .map((p) => [p.x as number, p.y as number])
}

function verticalStageLabel(transitionType?: string): string {
  if (transitionType === 'ELEVATOR') return '엘리베이터'
  if (transitionType === 'STAIRS') return '계단'
  if (transitionType === 'BRIDGE') return '구름다리'
  return '층 이동'
}

function routeStagesOf(route?: RouteResult): RouteStage[] {
  if (!route) return []
  const stages: RouteStage[] = []
  let indoorCount = 0
  let outdoorCount = 0
  let verticalCount = 0
  const hasOutdoor = route.segments.some((seg) => seg.type === 'OUTDOOR')
  for (const [index, seg] of route.segments.entries()) {
    if (seg.type === 'INDOOR' && seg.buildingId && typeof seg.floorNumber === 'number') {
      const routePoints = indoorRoutePoints(seg)
      if (routePoints.length < 1) continue
      indoorCount += 1
      stages.push({
        key: `${seg.buildingId}-${seg.floorNumber}-${index}`,
        kind: 'INDOOR',
        label: `${buildingLabel(seg.buildingId)} ${floorLabel(seg.floorNumber)}`,
        buildingId: seg.buildingId,
        floorNumber: seg.floorNumber,
        instruction: seg.instruction ?? `${floorLabel(seg.floorNumber)} 실내 경로`,
        routePoints,
      })
    }
    if (seg.type === 'VERTICAL' && seg.buildingId && typeof seg.floorNumber === 'number') {
      const routePoints = indoorRoutePoints(seg)
      if (routePoints.length < 1) continue
      verticalCount += 1
      const label = verticalStageLabel(seg.transitionType)
      stages.push({
        key: `vertical-${seg.buildingId}-${seg.floorNumber}-${index}`,
        kind: 'VERTICAL',
        label: `${buildingLabel(seg.buildingId)} ${floorLabel(seg.floorNumber)} ${label}`,
        buildingId: seg.buildingId,
        floorNumber: seg.floorNumber,
        instruction:
          seg.instruction ??
          `${floorLabel(seg.floorNumber)}에서 ${label}를 이용해 ${seg.toFloorNumber != null ? floorLabel(seg.toFloorNumber) : '다른 층'}으로 이동하세요.`,
        routePoints: [routePoints[0]],
      })
    }
    if (seg.type === 'OUTDOOR') {
      const line = (seg.pathPoints ?? [])
        .filter((p) => p.latitude != null && p.longitude != null)
        .map((p) => ({ lat: p.latitude as number, lng: p.longitude as number }))
      if (line.length < 2) continue
      outdoorCount += 1
      stages.push({
        key: `outdoor-${index}`,
        kind: 'OUTDOOR',
        label: outdoorCount === 1 ? '외부 이동' : `외부 이동 ${outdoorCount}`,
        instruction: '외부 지도 경로를 따라 다음 건물 출입구까지 이동하세요.',
        line,
      })
    }
  }
  if (indoorCount === 0 && verticalCount === 0 && outdoorCount === 1 && stages.length === 1) return []
  if (!hasOutdoor || stages.length === 0) return stages
  return [
    {
      key: 'total',
      kind: 'TOTAL',
      label: '전체 경로',
      instruction: '전체 외부 경로를 지도에서 확인하세요. 실내 구간은 아래 단계에서 따로 확인할 수 있습니다.',
    },
    ...stages,
  ]
}

function buildingLabel(buildingId: string): string {
  return buildings.find((b) => b.id === buildingId)?.name ?? buildingId
}

function floorLabel(floorNumber: number): string {
  return floorNumber < 0 ? `B${Math.abs(floorNumber)}층` : `${floorNumber}층`
}

export default function RouteFind() {
  const nav = useNavigate()
  const { routeStart, routeDest, setRoute } = useApp()
  const [selectedKey, setSelectedKey] = useState<string>('DEFAULT')
  const [editing, setEditing] = useState<'start' | 'dest' | null>(null)
  const [q, setQ] = useState('')
  const [apiRoutes, setApiRoutes] = useState<RouteResult[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState('')
  const [selectedStageIndex, setSelectedStageIndex] = useState(0)
  const [indoorData, setIndoorData] = useState<IndoorMapData | null>(null)
  const [indoorLoading, setIndoorLoading] = useState(false)

  const start = useMemo(() => resolve(routeStart), [routeStart])
  const dest = useMemo(() => resolve(routeDest), [routeDest])

  // 출발지 = 도착지 (같은 장소) 여부
  const sameSpot =
    !!routeStart && !!routeDest && routeStart.replace(/\s/g, '') === routeDest.replace(/\s/g, '')

  // 건물 선택 → 대표 호실 코드로 변환 (API는 호실 단위 입력만 받음)
  const startCode = useMemo(() => routeKeyword(routeStart), [routeStart])
  const destCode = useMemo(() => routeKeyword(routeDest), [routeDest])

  // 통합 길찾기 API 호출 (출발/도착을 호실 코드로 변환할 수 있을 때만)
  useEffect(() => {
    if (sameSpot || !startCode || !destCode) {
      setApiRoutes(null)
      setErrMsg('')
      return
    }
    let alive = true
    setLoading(true)
    setErrMsg('')
    fetchRoutes({ start: startCode, destination: destCode })
      .then((res) => {
        if (!alive) return
        setApiRoutes(res)
        setLoading(false)
      })
      .catch((e) => {
        if (!alive) return
        setApiRoutes(null)
        setErrMsg(e instanceof ApiError ? e.message : '경로를 불러오지 못했습니다.')
        setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [startCode, destCode, sameSpot])


  const options = useMemo<DisplayOption[]>(() => {
    if (apiRoutes && apiRoutes.length > 0) {
      return apiRoutes.map((r) => {
        const meta = ROUTE_META[r.routeType] ?? {
          label: r.title,
          color: '#BE3A60',
          note: r.reason ?? '',
        }
        const line = displayLine(r, start, dest)
        return {
          key: r.routeType,
          label: meta.label,
          color: meta.color,
          note: hasBridgeSegment(r) ? `${meta.note} · 구름다리/실내 연결 포함` : meta.note,
          durationMin: Math.max(1, Math.round(r.totalEstimatedTime / 60)),
          distanceM: Math.round(r.totalDistance),
          line,
          route: r,
        }
      })
    }
    // 목업 폴백
    return ROUTE_OPTIONS.map((o) => ({
      key: o.type,
      label: o.label,
      color: o.color,
      note: o.note,
      durationMin: o.durationMin,
      distanceM: o.distanceM,
      line: mockRoute(start, dest, o.type),
    }))
  }, [apiRoutes, start, dest])

  // 선택된 옵션이 현재 목록에 없으면 첫 번째로
  useEffect(() => {
    if (options.length > 0 && !options.some((o) => o.key === selectedKey)) {
      setSelectedKey(options[0].key)
    }
  }, [options, selectedKey])

  const lines: RouteLine[] = options.map((o) => ({
    color: o.color,
    selected: o.key === selectedKey,
    points: o.line,
  }))

  const selectedOption = options.find((o) => o.key === selectedKey) ?? options[0]
  const selectedRoute = selectedOption?.route
  const routeStages = useMemo(() => routeStagesOf(selectedRoute), [selectedRoute])
  const showStagedRoute = routeStages.length > 0
  const selectedStage = routeStages[Math.min(selectedStageIndex, Math.max(routeStages.length - 1, 0))]
  const selectedIndoorStage =
    selectedStage?.kind === 'INDOOR' || selectedStage?.kind === 'VERTICAL' ? selectedStage : null

  useEffect(() => {
    setSelectedStageIndex(0)
  }, [selectedKey, routeStart, routeDest])

  useEffect(() => {
    if (!showStagedRoute || !selectedIndoorStage) {
      setIndoorData(null)
      setIndoorLoading(false)
      return
    }
    let alive = true
    setIndoorLoading(true)
    loadIndoorMap(selectedIndoorStage.buildingId, selectedIndoorStage.floorNumber)
      .then((data) => {
        if (!alive) return
        setIndoorData(data)
        setIndoorLoading(false)
      })
      .catch(() => {
        if (!alive) return
        setIndoorData(null)
        setIndoorLoading(false)
      })
    return () => {
      alive = false
    }
  }, [showStagedRoute, selectedIndoorStage])

  const openPicker = (which: 'start' | 'dest') => {
    setQ('')
    setEditing(which)
  }

  const pick = (name: string) => {
    if (editing === 'start') setRoute(name, routeDest)
    else if (editing === 'dest') setRoute(routeStart, name)
    setEditing(null)
  }

  const swap = () => setRoute(routeDest || '내 위치', routeStart)

  // 선택 후보: 출발지에는 '내 위치' 포함, 도착지는 건물만.
  const candidates = useMemo(() => {
    const all =
      editing === 'start'
        ? ['내 위치', ...ENGINEERING_ROOM_SUGGESTIONS, ...buildings.map((b) => b.name)]
        : [...ENGINEERING_ROOM_SUGGESTIONS, ...buildings.map((b) => b.name)]
    const exclude = (editing === 'start' ? routeDest : routeStart).replace(/\s/g, '')
    const names = all.filter((n) => n.replace(/\s/g, '') !== exclude)
    const cq = q.replace(/\s/g, '')
    const filtered = cq ? names.filter((n) => n.replace(/\s/g, '').includes(cq)) : names
    if (cq && !filtered.some((n) => n.replace(/\s/g, '') === cq)) {
      return [q.trim(), ...filtered]
    }
    return filtered
  }, [editing, q, routeStart, routeDest])

  return (
    <div className="relative flex h-full flex-col bg-white">
      {/* 출발/도착 헤더 */}
      <div className="absolute inset-x-0 top-0 z-30 px-4 pt-3">
        <div className="flex items-center gap-2 rounded-2xl bg-white px-3 py-3 shadow-card">
          <button onClick={() => nav('/home')} aria-label="뒤로" className="px-1 text-ink">
            <BackIcon className="h-6 w-6" />
          </button>
          <div className="flex-1">
            <button
              onClick={() => openPicker('start')}
              className="flex w-full items-center gap-2 border-b border-line py-1.5 text-left active:bg-primary/5"
            >
              <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#2C7BE5]" />
              <span className="text-[12px] text-ink-faint">출발</span>
              <span className="ml-1 truncate text-[15px] font-semibold text-ink">{routeStart || '출발지 선택'}</span>
            </button>
            <button
              onClick={() => openPicker('dest')}
              className="flex w-full items-center gap-2 py-1.5 text-left active:bg-primary/5"
            >
              <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-primary" />
              <span className="text-[12px] text-ink-faint">도착</span>
              <span className="ml-1 truncate text-[15px] font-semibold text-ink">{routeDest || '도착지 선택'}</span>
            </button>
          </div>
          <button onClick={swap} aria-label="출발/도착 변경" className="px-1 text-ink-soft active:text-primary">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M7 4v16M7 4l-3 3M7 4l3 3M17 20V4M17 20l-3-3M17 20l3-3" />
            </svg>
          </button>
        </div>
      </div>

      {/* 지도 + 경로 */}
      <div className="relative flex-1">
        {showStagedRoute ? (
          <div className="absolute inset-0 bg-[#f7f9fc] pt-[112px]">
            {selectedStage?.kind === 'TOTAL' ? (
              <CampusMap
                className="h-full w-full"
                route={sameSpot ? null : { start, dest, lines }}
              />
            ) : selectedStage?.kind === 'OUTDOOR' ? (
              <CampusMap
                className="h-full w-full"
                route={{
                  start: selectedStage.line[0],
                  dest: selectedStage.line[selectedStage.line.length - 1],
                  lines: [
                    {
                      color: selectedOption?.color ?? '#BE3A60',
                      selected: true,
                      points: selectedStage.line,
                    },
                  ],
                }}
              />
            ) : indoorLoading ? (
              <div className="flex h-full items-center justify-center text-[14px] text-ink-faint">
                실내 경로를 불러오는 중…
              </div>
            ) : indoorData && selectedIndoorStage ? (
              <IndoorMap
                map={indoorData.map}
                rooms={indoorData.rooms}
                routePoints={selectedIndoorStage.routePoints}
                routeActive
              />
            ) : (
              <div className="flex h-full items-center justify-center px-8 text-center text-[14px] text-ink-faint">
                이 구간의 실내 안내도를 불러오지 못했습니다.
              </div>
            )}

            <div className="absolute inset-x-3 top-[118px] z-20 rounded-2xl bg-white/95 p-3 shadow-card backdrop-blur">
              <p className="mb-2 text-[12px] font-semibold text-ink-soft">
                경로 단계 {selectedStageIndex + 1} / {routeStages.length}
              </p>
              <div className="no-scrollbar flex gap-2 overflow-x-auto">
                {routeStages.map((stage, index) => (
                  <button
                    key={stage.key}
                    onClick={() => setSelectedStageIndex(index)}
                    className={`shrink-0 rounded-full px-3 py-1.5 text-[12px] font-semibold ${
                      index === selectedStageIndex ? 'bg-primary text-white' : 'bg-gray-100 text-ink-soft'
                    }`}
                  >
                    {stage.label}
                  </button>
                ))}
              </div>
              {selectedStage && (
                <p className="mt-2 line-clamp-2 text-[11px] text-ink-faint">{selectedStage.instruction}</p>
              )}
            </div>
          </div>
        ) : (
          <CampusMap
            className="absolute inset-0"
            route={sameSpot ? null : { start, dest, lines }}
          />
        )}
      </div>

      {/* 경로 옵션 카드 */}
      <div className="rounded-t-2xl bg-white px-4 pb-7 pt-4 shadow-sheet">
        <p className="px-1 pb-2 text-[15px] font-bold text-ink">
          {routeStart || '출발지'} → {routeDest || '도착지'}
        </p>
        {sameSpot ? (
          <div className="my-1 rounded-xl bg-primary/5 px-4 py-6 text-center">
            <p className="text-[15px] font-semibold text-primary">출발지와 도착지가 같아요</p>
            <p className="mt-1 text-[13px] text-ink-faint">다른 장소를 선택해주세요</p>
          </div>
        ) : loading ? (
          <div className="my-1 px-4 py-8 text-center text-[14px] text-ink-faint">경로를 계산하는 중…</div>
        ) : (
          <>
            <div className="flex flex-col gap-2">
              {options.map((o, i) => {
                const on = o.key === selectedKey
                return (
                  <button
                    key={o.key}
                    onClick={() => setSelectedKey(o.key)}
                    style={{ animationDelay: `${i * 80}ms` }}
                    className={`flex animate-fade-up items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all duration-200 active:scale-[0.98] ${
                      on ? 'border-primary bg-primary/5 shadow-card' : 'border-line'
                    }`}
                  >
                    <span className="h-3 w-3 rounded-full" style={{ background: o.color }} />
                    <div className="flex-1">
                      <p className="text-[15px] font-bold text-ink">{o.label}</p>
                      <p className="text-[12px] text-ink-faint">{o.note}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[15px] font-bold text-ink">{o.durationMin}분</p>
                      <p className="text-[12px] text-ink-faint">{o.distanceM}m</p>
                    </div>
                  </button>
                )
              })}
            </div>
            {errMsg && (
              <p className="mt-3 text-center text-[11px] text-primary">
                {errMsg} · 목업 경로로 표시 중
              </p>
            )}
          </>
        )}
      </div>

      {/* 출발지/도착지 선택 시트 */}
      {editing && (
        <div className="absolute inset-0 z-40 flex flex-col bg-white animate-fade-up">
          <div className="flex items-center gap-2 border-b border-line px-4 py-3">
            <button onClick={() => setEditing(null)} aria-label="닫기" className="px-1 text-ink">
              <CloseIcon className="h-6 w-6" />
            </button>
            <div className="flex flex-1 items-center gap-2 rounded-lg border border-line px-3 py-2">
              <SearchIcon className="h-5 w-5 text-ink-faint" />
              <input
                autoFocus
                className="flex-1 text-[15px] outline-none placeholder:text-ink-faint"
                placeholder={editing === 'start' ? '출발지 검색' : '도착지 검색'}
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </div>
          </div>
          <div className="no-scrollbar flex-1 overflow-y-auto">
            {candidates.length === 0 && (
              <p className="mt-16 text-center text-[15px] text-ink-faint">검색 결과가 없습니다.</p>
            )}
            {candidates.map((name) => {
              const isMyLoc = name === '내 위치'
              return (
                <button
                  key={name}
                  onClick={() => pick(name)}
                  className="flex w-full items-center gap-3 border-b border-line px-5 py-4 text-left active:bg-primary/5"
                >
                  {isMyLoc ? (
                    <LocateIcon className="h-5 w-5 shrink-0 text-[#2C7BE5]" />
                  ) : (
                    <PinIcon className="h-5 w-5 shrink-0 text-primary" />
                  )}
                  <span className="truncate text-[16px] text-ink">{name}</span>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
