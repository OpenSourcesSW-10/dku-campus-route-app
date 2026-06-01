import { useEffect, useRef } from 'react'
import { useKakao, CAMPUS_CENTER } from './useKakao'
import { buildings as ALL_BUILDINGS, type Building } from '../../lib/data'
import type { TmiMarker, RouteOption, RouteType, LatLng } from '../../data/mock'
import { mockRoute } from '../../data/mock'

interface RouteProp {
  start: LatLng
  dest: LatLng
  options: RouteOption[]
  selected: RouteType
}

interface Props {
  className?: string
  showBuildings?: boolean
  selectedId?: string | null
  onSelectBuilding?: (b: Building) => void
  tmi?: TmiMarker[]
  onSelectTmi?: (t: TmiMarker) => void
  route?: RouteProp | null
  myLocation?: LatLng | null
}

export default function CampusMap({
  className,
  showBuildings = false,
  selectedId,
  onSelectBuilding,
  tmi,
  onSelectTmi,
  route,
  myLocation,
}: Props) {
  const { ready, error } = useKakao()
  const boxRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mapRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const overlaysRef = useRef<any[]>([])

  // 지도 초기화
  useEffect(() => {
    if (!ready || !boxRef.current || mapRef.current) return
    const kakao = window.kakao
    mapRef.current = new kakao.maps.Map(boxRef.current, {
      center: new kakao.maps.LatLng(CAMPUS_CENTER.lat, CAMPUS_CENTER.lng),
      level: 4,
    })
  }, [ready])

  // 오버레이(마커/경로) 갱신
  useEffect(() => {
    if (!ready || !mapRef.current) return
    const kakao = window.kakao
    const map = mapRef.current

    // 기존 오버레이 제거
    overlaysRef.current.forEach((o) => o.setMap(null))
    overlaysRef.current = []
    const add = (o: unknown) => overlaysRef.current.push(o)

    // 건물 마커
    if (showBuildings) {
      ALL_BUILDINGS.forEach((b) => {
        const active = b.id === selectedId
        const el = document.createElement('div')
        el.className = 'dku-pin'
        el.innerHTML = `<div style="
          transform:translate(-50%,-100%);cursor:pointer;display:flex;flex-direction:column;align-items:center;">
          <div style="background:${active ? '#A32E50' : '#BE3A60'};color:#fff;font-size:12px;font-weight:700;
            padding:5px 10px;border-radius:14px;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,.3);
            ${active ? 'transform:scale(1.08);' : ''}">${b.name}</div>
          <div style="width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;
            border-top:7px solid ${active ? '#A32E50' : '#BE3A60'};"></div>
        </div>`
        el.onclick = () => onSelectBuilding?.(b)
        const ov = new kakao.maps.CustomOverlay({
          position: new kakao.maps.LatLng(b.lat, b.lng),
          content: el,
          yAnchor: 1,
          zIndex: active ? 10 : 3,
        })
        ov.setMap(map)
        add(ov)
      })
    }

    // TMI 마커
    tmi?.forEach((t) => {
      const el = document.createElement('div')
      el.innerHTML = `<div style="transform:translate(-50%,-50%);cursor:pointer;">
        <div style="width:22px;height:22px;border-radius:50%;background:${tmiColor(t.category)};
          border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4);"></div></div>`
      el.onclick = () => onSelectTmi?.(t)
      const ov = new kakao.maps.CustomOverlay({
        position: new kakao.maps.LatLng(t.lat, t.lng),
        content: el,
        zIndex: 5,
      })
      ov.setMap(map)
      add(ov)
    })

    // 경로 (목업 폴리라인)
    if (route) {
      // 선택 안 된 옵션은 흐리게, 선택된 옵션 위에
      route.options.forEach((opt) => {
        const path = mockRoute(route.start, route.dest, opt.type).map(
          (p) => new kakao.maps.LatLng(p.lat, p.lng),
        )
        const isSel = opt.type === route.selected
        const line = new kakao.maps.Polyline({
          path,
          strokeWeight: isSel ? 6 : 4,
          strokeColor: opt.color,
          strokeOpacity: isSel ? 0.95 : 0.4,
          strokeStyle: 'solid',
        })
        line.setMap(map)
        add(line)
      })
      // 출발/도착 마커
      addEndpoint(kakao, map, route.start, '출발', '#2C7BE5', add)
      addEndpoint(kakao, map, route.dest, '도착', '#BE3A60', add)
      // 경로가 보이도록 영역 맞춤
      const bounds = new kakao.maps.LatLngBounds()
      bounds.extend(new kakao.maps.LatLng(route.start.lat, route.start.lng))
      bounds.extend(new kakao.maps.LatLng(route.dest.lat, route.dest.lng))
      map.setBounds(bounds, 60, 40, 200, 40)
    }

    // 현재 위치
    if (myLocation) {
      const el = document.createElement('div')
      el.innerHTML = `<div style="transform:translate(-50%,-50%);">
        <div style="width:18px;height:18px;border-radius:50%;background:#2C7BE5;border:3px solid #fff;
          box-shadow:0 0 0 6px rgba(44,123,229,.25);"></div></div>`
      const ov = new kakao.maps.CustomOverlay({
        position: new kakao.maps.LatLng(myLocation.lat, myLocation.lng),
        content: el,
        zIndex: 8,
      })
      ov.setMap(map)
      add(ov)
    }
  }, [ready, showBuildings, selectedId, tmi, route, myLocation, onSelectBuilding, onSelectTmi])

  if (error) {
    return (
      <div className={`flex items-center justify-center bg-gray-100 p-6 text-center text-sm text-ink-soft ${className}`}>
        지도를 불러오지 못했습니다.
        <br />
        (카카오 JS 키 / 도메인 등록 확인)
      </div>
    )
  }

  return <div ref={boxRef} className={className} />
}

function tmiColor(cat: TmiMarker['category']) {
  return (
    { classroom: '#BE3A60', rest: '#F2B705', tmi: '#2E9E5B', facility: '#5BB8E8', rain: '#9B8CE0' }[
      cat
    ] || '#BE3A60'
  )
}

function addEndpoint(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  kakao: any,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  map: any,
  pos: LatLng,
  label: string,
  color: string,
  add: (o: unknown) => void,
) {
  const el = document.createElement('div')
  el.innerHTML = `<div style="transform:translate(-50%,-100%);display:flex;flex-direction:column;align-items:center;">
    <div style="background:${color};color:#fff;font-size:11px;font-weight:700;padding:3px 8px;border-radius:10px;">${label}</div>
    <div style="width:0;height:0;border-left:4px solid transparent;border-right:4px solid transparent;border-top:6px solid ${color};"></div>
  </div>`
  const ov = new kakao.maps.CustomOverlay({
    position: new kakao.maps.LatLng(pos.lat, pos.lng),
    content: el,
    yAnchor: 1,
    zIndex: 9,
  })
  ov.setMap(map)
  add(ov)
}
