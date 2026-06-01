import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import StatusBar from '../components/StatusBar'
import CampusMap from '../features/map/CampusMap'
import { BackIcon } from '../components/Icons'
import { buildings } from '../lib/data'
import { useApp } from '../store/useApp'
import { ROUTE_OPTIONS, type RouteType, type LatLng } from '../data/mock'
import { CAMPUS_CENTER } from '../features/map/useKakao'

function resolve(name: string): LatLng {
  if (!name || name === '내 위치') return CAMPUS_CENTER
  const compact = name.replace(/\s/g, '')
  const b =
    buildings.find((x) => x.name.replace(/\s/g, '') === compact) ||
    buildings.find((x) => compact.includes(x.name.replace(/\s/g, '')) || x.name.replace(/\s/g, '').includes(compact))
  return b ? { lat: b.lat, lng: b.lng } : CAMPUS_CENTER
}

export default function RouteFind() {
  const nav = useNavigate()
  const { routeStart, routeDest } = useApp()
  const [selected, setSelected] = useState<RouteType>('fast')

  const start = useMemo(() => resolve(routeStart), [routeStart])
  const dest = useMemo(() => resolve(routeDest), [routeDest])

  return (
    <div className="relative flex h-full flex-col bg-white">
      <StatusBar />

      {/* 출발/도착 헤더 */}
      <div className="absolute inset-x-0 top-11 z-30 px-4 pt-2">
        <div className="flex items-center gap-3 rounded-2xl bg-white px-4 py-3 shadow-card">
          <button onClick={() => nav('/home')} aria-label="뒤로" className="text-ink">
            <BackIcon className="h-6 w-6" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-2 border-b border-line py-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[#2C7BE5]" />
              <span className="text-[12px] text-ink-faint">출발</span>
              <span className="ml-1 truncate text-[15px] font-semibold text-ink">{routeStart}</span>
            </div>
            <div className="flex items-center gap-2 py-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-primary" />
              <span className="text-[12px] text-ink-faint">도착</span>
              <span className="ml-1 truncate text-[15px] font-semibold text-ink">{routeDest || '도착지 선택'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 지도 + 경로 */}
      <div className="relative flex-1">
        <CampusMap
          className="absolute inset-0"
          route={{ start, dest, options: ROUTE_OPTIONS, selected }}
        />
      </div>

      {/* 경로 옵션 카드 */}
      <div className="rounded-t-2xl bg-white px-4 pb-7 pt-4 shadow-sheet">
        <p className="px-1 pb-2 text-[15px] font-bold text-ink">
          {routeStart} → {routeDest || '도착지'}
        </p>
        <div className="flex flex-col gap-2">
          {ROUTE_OPTIONS.map((o) => {
            const on = o.type === selected
            return (
              <button
                key={o.type}
                onClick={() => setSelected(o.type)}
                className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left ${
                  on ? 'border-primary bg-primary/5' : 'border-line'
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
        <p className="mt-3 text-center text-[11px] text-ink-faint">
          * 실제 경로는 백엔드 연동 시 제공됩니다 (목업 표시)
        </p>
      </div>
    </div>
  )
}
