import { useMemo, useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import TopBar from '../components/TopBar'
import IndoorMap from '../features/indoor/IndoorMap'
import { ChevronRight, CloseIcon } from '../components/Icons'
import {
  buildings,
  indoorMapsOf,
  defaultFloor,
  loadIndoorMap,
  roomsOfBuilding,
  buildingById,
  type Building,
  type IndoorMapData,
} from '../lib/data'
import { fetchIndoorRoute, ApiError, type RouteResult } from '../lib/api'

// 지하층 표기: "-1층" → "B1층", "-2층" → "B2층"
function fixFloorLabels(text: string): string {
  return text.replace(/-(\d+)층/g, 'B$1층')
}

export default function IndoorMapPage() {
  const { buildingId, floor } = useParams()
  const [params] = useSearchParams()

  // 건물 미선택 → 건물 목록
  if (!buildingId || !floor) {
    return <BuildingPicker />
  }

  return (
    <IndoorView
      buildingId={buildingId}
      floor={Number(floor)}
      initialRoom={params.get('room')}
    />
  )
}

function BuildingPicker() {
  const nav = useNavigate()
  const indoorBuildings = buildings.filter((b) => indoorMapsOf(b.id).length > 0)
  return (
    <div className="flex h-full flex-col bg-white">
      <TopBar title="강의실 정보" onBack={() => nav('/home')} />
      <div className="flex-1 px-5 pt-4">
        <p className="mb-2 px-1 text-[14px] text-ink-faint">실내 안내도가 있는 건물</p>
        {indoorBuildings.map((b) => (
          <button
            key={b.id}
            onClick={() => nav(`/indoor/${b.id}/${defaultFloor(b.id)}`)}
            className="flex w-full items-center justify-between rounded-xl border border-line px-4 py-4 text-left [&+&]:mt-3"
          >
            <div>
              <p className="text-[16px] font-bold text-ink">{b.name}</p>
              <p className="text-[13px] text-ink-faint">{indoorMapsOf(b.id).length}개 층 안내도</p>
            </div>
            <ChevronRight className="h-5 w-5 text-ink-faint" />
          </button>
        ))}
      </div>
    </div>
  )
}

function IndoorView({
  buildingId,
  floor,
  initialRoom,
}: {
  buildingId: string
  floor: number
  initialRoom: string | null
}) {
  const nav = useNavigate()
  const building = buildingById(buildingId) as Building
  const floors = indoorMapsOf(buildingId)
  const bRooms = useMemo(() => roomsOfBuilding(buildingId), [buildingId])

  const [data, setData] = useState<IndoorMapData | null>(null)
  const [loading, setLoading] = useState(true)

  // 도착 호실(지도 탭) / 출발 호실(선택)
  const [destRoomId, setDestRoomId] = useState<string | null>(initialRoom)
  const [fromRoomId, setFromRoomId] = useState<string | null>(null)

  // 실내 경로(호실→호실) 결과
  const [route, setRoute] = useState<RouteResult | null>(null)
  const [routeLoading, setRouteLoading] = useState(false)
  const [routeErr, setRouteErr] = useState('')

  // 출발 호실 선택 모드 (지도에서 직접 터치)
  const [pickingStart, setPickingStart] = useState(false)

  // 층/건물 변경 시 실내 지도 + 강의실 로드 (API 우선, 로컬 폴백)
  useEffect(() => {
    let alive = true
    setLoading(true)
    loadIndoorMap(buildingId, floor).then((res) => {
      if (!alive) return
      setData(res)
      setLoading(false)
    })
    return () => {
      alive = false
    }
  }, [buildingId, floor])

  // 검색 진입(initialRoom)/건물 변경 시 상태 초기화
  useEffect(() => {
    setDestRoomId(initialRoom)
    setFromRoomId(null)
    setRoute(null)
    setRouteErr('')
  }, [initialRoom, buildingId])

  // 출발/도착 호실이 모두 정해지면 실내 경로 API 호출
  useEffect(() => {
    if (!fromRoomId || !destRoomId || fromRoomId === destRoomId) {
      setRoute(null)
      setRouteErr('')
      return
    }
    let alive = true
    setRouteLoading(true)
    setRouteErr('')
    fetchIndoorRoute({ fromRoomId, toRoomId: destRoomId })
      .then((r) => {
        if (!alive) return
        setRoute(r)
        setRouteLoading(false)
      })
      .catch((e) => {
        if (!alive) return
        setRoute(null)
        setRouteErr(e instanceof ApiError ? e.message : '실내 경로를 불러오지 못했습니다.')
        setRouteLoading(false)
      })
    return () => {
      alive = false
    }
  }, [fromRoomId, destRoomId])

  const rooms = data?.rooms ?? []
  const map = data?.map

  const destRoom = destRoomId ? bRooms.find((r) => r.id === destRoomId) : undefined
  const fromRoom = fromRoomId ? bRooms.find((r) => r.id === fromRoomId) : undefined

  // 특정 층의 실내 경로선 좌표 (백엔드 INDOOR 세그먼트).
  // 백엔드 그래프 노드가 적어 여러 호실이 같은 노드를 공유하므로,
  // 출발/도착 호실이 이 층이면 호실 중심까지 선을 연장해 실제 호실에 닿게 한다.
  const floorPoints = (f: number): number[][] | null => {
    if (!route) return null
    const seg = route.segments.find(
      (s) => s.type === 'INDOOR' && s.floorNumber === f && (s.pathPoints?.length ?? 0) >= 1,
    )
    if (!seg?.pathPoints) return null
    let pts = seg.pathPoints
      .filter((p) => p.x != null && p.y != null)
      .map((p) => [p.x as number, p.y as number])
    if (fromRoom?.pos && fromRoom.floor === f) pts = [[fromRoom.pos.cx, fromRoom.pos.cy], ...pts]
    if (destRoom?.pos && destRoom.floor === f) pts = [...pts, [destRoom.pos.cx, destRoom.pos.cy]]
    return pts.length >= 2 ? pts : null
  }

  const routePoints = floorPoints(floor)
  // 층 이동(VERTICAL) 안내
  const verticals = route ? route.segments.filter((s) => s.type === 'VERTICAL') : []
  // 실제 경로선이 그려지는 층 목록
  const routeFloors = route ? floors.map((m) => m.floor).filter((f) => floorPoints(f) !== null) : []

  // 현재 층에 있는 호실만 SVG 하이라이트 (도착 우선, 없으면 출발)
  const onThisFloor = (id?: string | null) => !!id && rooms.some((r) => r.id === id)
  const highlightRoomId = onThisFloor(destRoomId)
    ? destRoomId
    : onThisFloor(fromRoomId)
      ? fromRoomId
      : null

  const reset = () => {
    setDestRoomId(null)
    setFromRoomId(null)
    setRoute(null)
    setRouteErr('')
    setPickingStart(false)
  }

  if (loading) {
    return (
      <div className="flex h-full flex-col bg-white">
        <TopBar title={building?.name ?? '실내 지도'} onBack={() => nav('/home')} />
        <p className="mt-16 text-center text-ink-faint">안내도를 불러오는 중…</p>
      </div>
    )
  }

  if (!map) {
    return (
      <div className="flex h-full flex-col bg-white">
        <TopBar title={building?.name ?? '실내 지도'} onBack={() => nav('/home')} />
        <p className="mt-16 text-center text-ink-faint">해당 층 안내도가 없습니다.</p>
      </div>
    )
  }

  return (
    <div className="relative flex h-full flex-col bg-white">
      <TopBar title={building?.name ?? '실내 지도'} onBack={() => nav('/home')} />

      <div className="relative flex flex-1 overflow-hidden">
        {/* 층 선택 (경로가 지나는 층은 점으로 표시) */}
        <div className="no-scrollbar z-10 flex w-16 shrink-0 flex-col items-center gap-2 overflow-y-auto border-r border-line bg-white py-3">
          {floors.map((m) => {
            const onRoute = routeFloors.includes(m.floor)
            return (
              <button
                key={m.floor}
                onClick={() => nav(`/indoor/${buildingId}/${m.floor}`)}
                className={`relative flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-[14px] font-bold ${
                  m.floor === floor ? 'bg-primary text-white' : 'bg-gray-100 text-ink-soft'
                }`}
              >
                {m.floorLabel}
                {onRoute && m.floor !== floor && (
                  <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-[#5B6BE8]" />
                )}
              </button>
            )
          })}
        </div>

        {/* 안내도 */}
        <div className="relative flex-1">
          <IndoorMap
            map={map}
            rooms={rooms}
            highlightRoomId={highlightRoomId}
            onSelectRoom={(r) => {
              if (pickingStart) {
                // 출발 호실 선택 모드: 탭한 호실을 출발지로
                if (r.id !== destRoomId) setFromRoomId(r.id)
                setPickingStart(false)
              } else {
                setDestRoomId(r.id)
              }
            }}
            routePoints={routePoints}
            routeActive={!!route}
          />

          {/* 출발 호실 선택 안내 배너 */}
          {pickingStart && (
            <div className="absolute inset-x-3 top-3 z-20 flex items-center gap-2 rounded-xl bg-[#5B6BE8] px-4 py-3 text-white shadow-card animate-fade-up">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-white" />
              <p className="flex-1 text-[13px] font-semibold">
                지도에서 출발 호실을 터치하세요{floors.length > 1 ? ' (다른 층은 좌측에서 전환)' : ''}
              </p>
              <button
                onClick={() => setPickingStart(false)}
                className="rounded-md px-2 py-1 text-[12px] font-semibold text-white/90 active:bg-white/20"
              >
                취소
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 도착 호실이 선택되면 출발/도착 + 실내 경로 시트 */}
      {destRoom && (
        <div
          key={destRoom.id}
          className="animate-sheet-up rounded-t-2xl border-t border-line bg-white px-5 pb-7 pt-4 shadow-sheet"
        >
          {/* 출발/도착 선택 줄 */}
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1 space-y-1.5">
              <button
                onClick={() => setPickingStart(true)}
                className={`flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left active:bg-primary/5 ${
                  pickingStart ? 'border-[#5B6BE8] bg-[#5B6BE8]/5' : 'border-line'
                }`}
              >
                <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#5B6BE8]" />
                <span className="text-[12px] text-ink-faint">출발</span>
                <span className="ml-1 truncate text-[14px] font-semibold text-ink">
                  {fromRoom
                    ? `${fromRoom.floorLabel} ${fromRoom.number}호`
                    : pickingStart
                      ? '지도에서 호실 터치'
                      : '출발 호실 선택'}
                </span>
              </button>
              <div className="flex w-full items-center gap-2 rounded-lg bg-primary/5 px-3 py-2">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-primary" />
                <span className="text-[12px] text-ink-faint">도착</span>
                <span className="ml-1 truncate text-[14px] font-semibold text-ink">
                  {destRoom.floorLabel} {destRoom.number}호
                </span>
              </div>
            </div>
            <button onClick={reset} className="p-1 text-ink-faint" aria-label="닫기">
              <CloseIcon className="h-5 w-5" />
            </button>
          </div>

          {/* 상태/결과 */}
          {!fromRoomId ? (
            <p className="mt-3 text-center text-[12px] text-ink-faint">
              {pickingStart
                ? '지도에서 출발 호실을 터치하세요'
                : '‘출발’을 누른 뒤 지도에서 출발 호실을 터치하세요'}
            </p>
          ) : routeLoading ? (
            <p className="mt-3 text-center text-[13px] text-ink-faint">실내 경로 계산 중…</p>
          ) : routeErr ? (
            <p className="mt-3 text-center text-[13px] text-primary">{routeErr}</p>
          ) : route ? (
            <div className="mt-3">
              <div className="flex items-center justify-center gap-4 text-[13px] text-ink-soft">
                <span>총 {Math.round(route.totalDistance)}m</span>
                <span>·</span>
                <span>약 {Math.max(1, Math.round(route.totalEstimatedTime / 60))}분</span>
              </div>
              {verticals.length > 0 && (
                <div className="mt-2 space-y-1">
                  {verticals.map((v, i) => (
                    <p key={i} className="text-center text-[12px] text-[#5B6BE8]">
                      {fixFloorLabels(
                        v.instruction ??
                          `${v.transitionType ?? '계단/엘리베이터'}로 ${v.floorNumber}층 → ${v.toFloorNumber}층 이동`,
                      )}
                    </p>
                  ))}
                </div>
              )}
              {routeFloors.length > 1 && (
                <p className="mt-2 text-center text-[11px] text-ink-faint">
                  여러 층 경로입니다 · 좌측 층 버튼(•)으로 각 층 경로를 확인하세요
                </p>
              )}
            </div>
          ) : null}
        </div>
      )}

    </div>
  )
}
