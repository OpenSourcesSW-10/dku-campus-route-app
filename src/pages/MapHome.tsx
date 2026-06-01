import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import StatusBar from '../components/StatusBar'
import Drawer from '../components/Drawer'
import CampusMap from '../features/map/CampusMap'
import { MenuIcon, SearchIcon, ChevronRight, LocateIcon, PinIcon } from '../components/Icons'
import type { Building } from '../lib/data'
import { indoorMapsOf } from '../lib/data'
import { useApp } from '../store/useApp'
import type { LatLng } from '../data/mock'
import { CAMPUS_CENTER } from '../features/map/useKakao'

export default function MapHome() {
  const nav = useNavigate()
  const [drawer, setDrawer] = useState(false)
  const [selected, setSelected] = useState<Building | null>(null)
  const [myLoc, setMyLoc] = useState<LatLng | null>(null)
  const setRoute = useApp((s) => s.setRoute)

  const locate = () => {
    if (!navigator.geolocation) {
      setMyLoc(CAMPUS_CENTER)
      return
    }
    navigator.geolocation.getCurrentPosition(
      (p) => setMyLoc({ lat: p.coords.latitude, lng: p.coords.longitude }),
      () => setMyLoc(CAMPUS_CENTER),
      { enableHighAccuracy: true, timeout: 4000 },
    )
  }

  const hasIndoor = selected ? indoorMapsOf(selected.id).length > 0 : false

  return (
    <div className="relative flex h-full flex-col bg-white">
      <StatusBar />

      {/* 상단 검색/메뉴 */}
      <div className="absolute inset-x-0 top-11 z-30 flex items-center gap-2 px-4 pt-2">
        <button
          onClick={() => setDrawer(true)}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white text-ink shadow-card"
          aria-label="메뉴"
        >
          <MenuIcon className="h-6 w-6" />
        </button>
        <button
          onClick={() => nav('/search')}
          className="flex h-11 flex-1 items-center gap-2 rounded-full bg-white px-4 text-left text-ink-faint shadow-card"
        >
          <SearchIcon className="h-5 w-5" />
          <span className="text-[15px]">장소 또는 강의실로 검색</span>
        </button>
      </div>

      {/* 지도 */}
      <div className="relative flex-1">
        <CampusMap
          className="absolute inset-0"
          showBuildings
          selectedId={selected?.id ?? null}
          onSelectBuilding={setSelected}
          myLocation={myLoc}
        />

        {/* 현재위치 버튼 */}
        <button
          onClick={locate}
          className="absolute bottom-5 right-4 flex h-12 w-12 items-center justify-center rounded-full bg-white text-primary shadow-card"
          aria-label="현재 위치"
        >
          <LocateIcon className="h-6 w-6" />
        </button>
      </div>

      {/* 선택된 건물 카드 */}
      {selected && (
        <div className="absolute inset-x-0 bottom-0 z-20 rounded-t-2xl bg-white px-5 pb-7 pt-4 shadow-sheet">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
              <PinIcon className="h-6 w-6" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[17px] font-bold text-ink">{selected.name}</p>
              <p className="text-[13px] text-primary">
                {hasIndoor ? '강의실 · TMI · 길찾기 가능' : 'TMI · 길찾기 가능'}
              </p>
            </div>
            <button
              onClick={() => hasIndoor && nav(`/indoor/${selected.id}/${indoorMapsOf(selected.id)[0].floor}`)}
              className="flex h-9 w-9 items-center justify-center text-ink-faint"
              aria-label="자세히"
            >
              <ChevronRight className="h-6 w-6" />
            </button>
          </div>

          <div className="mt-4 flex gap-2">
            <button
              onClick={() => {
                setRoute('내 위치', selected.name)
                nav('/route')
              }}
              className="flex-1 rounded-lg bg-primary py-3 text-center text-[15px] font-semibold text-white"
            >
              길찾기
            </button>
            {hasIndoor && (
              <button
                onClick={() => nav(`/indoor/${selected.id}/${indoorMapsOf(selected.id)[0].floor}`)}
                className="flex-1 rounded-lg border border-primary py-3 text-center text-[15px] font-semibold text-primary"
              >
                강의실 정보
              </button>
            )}
          </div>
        </div>
      )}

      <Drawer open={drawer} onClose={() => setDrawer(false)} />
    </div>
  )
}
