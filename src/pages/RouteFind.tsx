import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import CampusMap from '../features/map/CampusMap'
import { BackIcon, CloseIcon, SearchIcon, PinIcon, LocateIcon } from '../components/Icons'
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
  const { routeStart, routeDest, setRoute } = useApp()
  const [selected, setSelected] = useState<RouteType>('fast')
  const [editing, setEditing] = useState<'start' | 'dest' | null>(null)
  const [q, setQ] = useState('')

  const start = useMemo(() => resolve(routeStart), [routeStart])
  const dest = useMemo(() => resolve(routeDest), [routeDest])

  // 출발지 = 도착지 (같은 장소) 여부
  const sameSpot =
    !!routeStart && !!routeDest && routeStart.replace(/\s/g, '') === routeDest.replace(/\s/g, '')

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
  // 반대편에 이미 선택된 장소는 목록에서 제외(같은 지점 선택 예방).
  const candidates = useMemo(() => {
    const all = editing === 'start' ? ['내 위치', ...buildings.map((b) => b.name)] : buildings.map((b) => b.name)
    const exclude = (editing === 'start' ? routeDest : routeStart).replace(/\s/g, '')
    const names = all.filter((n) => n.replace(/\s/g, '') !== exclude)
    const cq = q.replace(/\s/g, '')
    return cq ? names.filter((n) => n.replace(/\s/g, '').includes(cq)) : names
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
        <CampusMap
          className="absolute inset-0"
          route={sameSpot ? null : { start, dest, options: ROUTE_OPTIONS, selected }}
        />
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
        ) : (
          <>
            <div className="flex flex-col gap-2">
              {ROUTE_OPTIONS.map((o, i) => {
                const on = o.type === selected
                return (
                  <button
                    key={o.type}
                    onClick={() => setSelected(o.type)}
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
            <p className="mt-3 text-center text-[11px] text-ink-faint">
              * 실제 경로는 백엔드 연동 시 제공됩니다 (목업 표시)
            </p>
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
