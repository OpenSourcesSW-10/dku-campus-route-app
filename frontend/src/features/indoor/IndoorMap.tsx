import { useEffect, useRef } from 'react'
import {
  TransformWrapper,
  TransformComponent,
  type ReactZoomPanPinchRef,
} from 'react-zoom-pan-pinch'
import type { IndoorMap as IndoorMapType, Room } from '../../lib/data'

interface Props {
  map: IndoorMapType
  rooms: Room[]
  highlightRoomId?: string | null
  onSelectRoom?: (room: Room) => void
  /** 실내 경로선 (안내도 좌표계 1000x707 기준 점들) */
  routePoints?: number[][] | null
  /** 경로 표시 중이면 강의실로 자동확대하지 않고 층 전체가 보이도록 맞춘다 */
  routeActive?: boolean
}

/**
 * 실내 안내도 뷰어.
 * 배경 PNG(1000x707) 위에 SVG로 강의실 좌표를 그린다.
 * 가로로 긴 도면이라 모바일에서 핀치줌/드래그로 이동·확대할 수 있게 했고,
 * 하이라이트된 강의실로는 자동 확대된다.
 */
export default function IndoorMap({ map, rooms, highlightRoomId, onSelectRoom, routePoints, routeActive }: Props) {
  const W = map.canvasWidth
  const H = map.canvasHeight
  const ref = useRef<ReactZoomPanPinchRef | null>(null)

  // 경로 표시 중이면 층 전체가 보이도록 맞추고(경로선이 화면 밖으로 나가지 않게),
  // 아니면 하이라이트된 강의실로 자동 확대/이동한다.
  useEffect(() => {
    const t = setTimeout(() => {
      try {
        if (routeActive) {
          ref.current?.resetTransform(400)
        } else if (highlightRoomId) {
          ref.current?.zoomToElement(`room-${highlightRoomId}`, 2.4, 500)
        }
      } catch {
        /* 요소를 못 찾으면 무시 */
      }
    }, 300)
    return () => clearTimeout(t)
  }, [highlightRoomId, map.image, routeActive])

  const hlRoom = highlightRoomId ? rooms.find((r) => r.id === highlightRoomId) : undefined

  return (
    <div className="relative h-full w-full bg-[#f7f9fc]">
      <TransformWrapper
        ref={ref}
        minScale={1}
        maxScale={6}
        centerOnInit
        doubleClick={{ mode: 'zoomIn', step: 0.7 }}
        wheel={{ step: 0.08 }}
      >
        {({ zoomIn, zoomOut, resetTransform }) => (
          <>
            <TransformComponent
              wrapperStyle={{ width: '100%', height: '100%' }}
              contentStyle={{ width: '100%', height: '100%' }}
            >
              <svg
                viewBox={`0 0 ${W} ${H}`}
                className="h-full w-full"
                preserveAspectRatio="xMidYMid meet"
              >
                <image href={map.image} x={0} y={0} width={W} height={H} />

                {rooms.map((r) => {
                  if (!r.pos) return null
                  const active = r.id === highlightRoomId
                  if (r.pos.polygon && r.pos.polygon.length >= 3) {
                    return (
                      <polygon
                        key={r.id}
                        id={`room-${r.id}`}
                        className={active ? 'room-hl' : undefined}
                        points={r.pos.polygon.map((p) => p.join(',')).join(' ')}
                        onClick={() => onSelectRoom?.(r)}
                        style={{ cursor: 'pointer' }}
                        fill={active ? '#BE3A60' : 'transparent'}
                        stroke={active ? '#BE3A60' : 'transparent'}
                        strokeWidth={active ? 3 : 0}
                      />
                    )
                  }
                  return (
                    <rect
                      key={r.id}
                      id={`room-${r.id}`}
                      className={active ? 'room-hl' : undefined}
                      x={r.pos.x}
                      y={r.pos.y}
                      width={r.pos.width}
                      height={r.pos.height}
                      rx={2}
                      onClick={() => onSelectRoom?.(r)}
                      style={{ cursor: 'pointer' }}
                      fill={active ? '#BE3A60' : 'transparent'}
                      stroke={active ? '#BE3A60' : 'transparent'}
                      strokeWidth={active ? 3 : 0}
                    />
                  )
                })}

                {/* 하이라이트 라벨 */}
                {hlRoom?.pos && (
                  <g pointerEvents="none">
                    <rect x={hlRoom.pos.cx - 26} y={hlRoom.pos.y - 26} width={52} height={20} rx={10} fill="#BE3A60" />
                    <text x={hlRoom.pos.cx} y={hlRoom.pos.y - 12} fontSize={12} fill="#fff" textAnchor="middle" fontWeight={700}>
                      {hlRoom.number}
                    </text>
                  </g>
                )}

                {/* 실내 경로선 (백엔드 INDOOR 세그먼트 좌표) */}
                {routePoints && routePoints.length >= 2 && (
                  <g pointerEvents="none">
                    <polyline
                      points={routePoints.map((p) => p.join(',')).join(' ')}
                      fill="none"
                      stroke="#5B6BE8"
                      strokeWidth={5}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeDasharray="2 10"
                    />
                    {/* 이 층 진입점 */}
                    <circle cx={routePoints[0][0]} cy={routePoints[0][1]} r={5} fill="#5B6BE8" />
                    {/* 이 층 이탈/도착점 */}
                    <circle
                      cx={routePoints[routePoints.length - 1][0]}
                      cy={routePoints[routePoints.length - 1][1]}
                      r={5}
                      fill="#fff"
                      stroke="#5B6BE8"
                      strokeWidth={3}
                    />
                  </g>
                )}
              </svg>
            </TransformComponent>

            {/* 줌 컨트롤 */}
            <div className="absolute right-3 top-3 z-10 flex flex-col overflow-hidden rounded-xl border border-line bg-white shadow-card">
              <button onClick={() => zoomIn()} className="flex h-10 w-10 items-center justify-center text-xl text-ink" aria-label="확대">
                +
              </button>
              <button onClick={() => zoomOut()} className="flex h-10 w-10 items-center justify-center border-t border-line text-xl text-ink" aria-label="축소">
                −
              </button>
              <button onClick={() => resetTransform()} className="flex h-10 w-10 items-center justify-center border-t border-line text-ink" aria-label="전체보기">
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M4 9V5h4M20 9V5h-4M4 15v4h4M20 15v4h-4" />
                </svg>
              </button>
            </div>

            <p className="pointer-events-none absolute bottom-2 left-1/2 -translate-x-1/2 rounded-full bg-black/40 px-3 py-1 text-[11px] text-white">
              두 손가락으로 확대 · 드래그로 이동
            </p>
          </>
        )}
      </TransformWrapper>
    </div>
  )
}
