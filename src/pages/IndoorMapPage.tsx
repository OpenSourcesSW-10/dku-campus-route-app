import { useMemo, useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import StatusBar from '../components/StatusBar'
import TopBar from '../components/TopBar'
import IndoorMap from '../features/indoor/IndoorMap'
import { ChevronRight, CloseIcon } from '../components/Icons'
import {
  buildings,
  indoorMapsOf,
  indoorMap,
  roomsOf,
  roomById,
  buildingById,
  type Building,
  type Room,
} from '../lib/data'
import { INDOOR_ROUTE_DEMO } from '../data/mock'

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
      <StatusBar />
      <TopBar title="강의실 정보" onBack={() => nav('/home')} />
      <div className="flex-1 px-5 pt-4">
        <p className="mb-2 px-1 text-[14px] text-ink-faint">실내 안내도가 있는 건물</p>
        {indoorBuildings.map((b) => (
          <button
            key={b.id}
            onClick={() => nav(`/indoor/${b.id}/${indoorMapsOf(b.id)[0].floor}`)}
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
  const map = indoorMap(buildingId, floor)
  const rooms = useMemo(() => roomsOf(buildingId, floor), [buildingId, floor])

  const [highlight, setHighlight] = useState<string | null>(initialRoom)
  const [showRoute, setShowRoute] = useState(false)

  // 층/건물/검색 대상이 바뀌면 하이라이트 동기화
  useEffect(() => {
    setHighlight(initialRoom)
    setShowRoute(false)
  }, [initialRoom, buildingId, floor])

  const hlRoom: Room | undefined = highlight ? roomById(highlight) : undefined
  const routeKey = `${buildingId}:${floor}`
  const routeDemo = INDOOR_ROUTE_DEMO[routeKey]

  if (!map) {
    return (
      <div className="flex h-full flex-col bg-white">
        <StatusBar />
        <TopBar title={building?.name ?? '실내 지도'} onBack={() => nav('/home')} />
        <p className="mt-16 text-center text-ink-faint">해당 층 안내도가 없습니다.</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col bg-white">
      <StatusBar />
      <TopBar title={building?.name ?? '실내 지도'} onBack={() => nav('/home')} />

      <div className="relative flex flex-1 overflow-hidden">
        {/* 층 선택 */}
        <div className="no-scrollbar z-10 flex w-16 shrink-0 flex-col items-center gap-2 overflow-y-auto border-r border-line bg-white py-3">
          {floors.map((m) => (
            <button
              key={m.floor}
              onClick={() => nav(`/indoor/${buildingId}/${m.floor}`)}
              className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-[14px] font-bold ${
                m.floor === floor ? 'bg-primary text-white' : 'bg-gray-100 text-ink-soft'
              }`}
            >
              {m.floorLabel}
            </button>
          ))}
        </div>

        {/* 안내도 */}
        <div className="relative flex-1">
          <IndoorMap
            map={map}
            rooms={rooms}
            highlightRoomId={highlight}
            onSelectRoom={(r) => {
              setHighlight(r.id)
              setShowRoute(false)
            }}
            routePoints={showRoute && routeDemo ? routeDemo.points : null}
          />
        </div>
      </div>

      {/* 선택된 강의실 정보 */}
      {hlRoom && (
        <div className="rounded-t-2xl border-t border-line bg-white px-5 pb-7 pt-4 shadow-sheet">
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-[17px] font-bold text-ink">
                {building?.name} {hlRoom.number}호
              </p>
              <p className="text-[13px] text-ink-faint">
                {hlRoom.floorLabel} · {hlRoom.name || '강의실'}
              </p>
            </div>
            <button onClick={() => setHighlight(null)} className="p-1 text-ink-faint" aria-label="닫기">
              <CloseIcon className="h-5 w-5" />
            </button>
          </div>
          {routeDemo && (
            <button
              onClick={() => setShowRoute((v) => !v)}
              className={`mt-3 w-full rounded-lg py-3 text-center text-[15px] font-semibold ${
                showRoute ? 'border border-primary text-primary' : 'bg-primary text-white'
              }`}
            >
              {showRoute ? '실내 경로 숨기기' : `실내 경로 보기 (${routeDemo.from} → ${hlRoom.number})`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
