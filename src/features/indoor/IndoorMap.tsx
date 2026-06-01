import { useEffect, useRef } from 'react'
import type { IndoorMap as IndoorMapType, Room } from '../../lib/data'

interface Props {
  map: IndoorMapType
  rooms: Room[]
  highlightRoomId?: string | null
  onSelectRoom?: (room: Room) => void
  /** 실내 경로선 (안내도 좌표계 1000x707 기준 점들) */
  routePoints?: number[][] | null
}

/**
 * 실내 안내도 뷰어.
 * 배경 PNG(1000x707) 위에 SVG viewBox로 강의실 좌표를 그려, 화면 크기에 맞춰 자동 정렬된다.
 */
export default function IndoorMap({ map, rooms, highlightRoomId, onSelectRoom, routePoints }: Props) {
  const W = map.canvasWidth
  const H = map.canvasHeight
  const hlRef = useRef<SVGGElement>(null)

  // 하이라이트된 강의실로 스크롤 (가로 스크롤 컨테이너 기준)
  useEffect(() => {
    hlRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' })
  }, [highlightRoomId])

  return (
    <div className="no-scrollbar h-full w-full overflow-auto bg-[#f7f9fc]">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="block h-auto w-full min-w-[640px]"
        preserveAspectRatio="xMidYMid meet"
      >
        <image href={map.image} x={0} y={0} width={W} height={H} />

        {/* 강의실 클릭 영역 + 하이라이트 */}
        {rooms.map((r) => {
          if (!r.pos) return null
          const active = r.id === highlightRoomId
          const common = {
            onClick: () => onSelectRoom?.(r),
            style: { cursor: 'pointer' as const },
          }
          if (r.pos.polygon && r.pos.polygon.length >= 3) {
            const pts = r.pos.polygon.map((p) => p.join(',')).join(' ')
            return (
              <g key={r.id} ref={active ? hlRef : undefined} {...common}>
                <polygon
                  points={pts}
                  fill={active ? 'rgba(190,58,96,0.38)' : 'transparent'}
                  stroke={active ? '#BE3A60' : 'transparent'}
                  strokeWidth={active ? 3 : 0}
                />
              </g>
            )
          }
          return (
            <g key={r.id} ref={active ? hlRef : undefined} {...common}>
              <rect
                x={r.pos.x}
                y={r.pos.y}
                width={r.pos.width}
                height={r.pos.height}
                rx={2}
                fill={active ? 'rgba(190,58,96,0.38)' : 'transparent'}
                stroke={active ? '#BE3A60' : 'transparent'}
                strokeWidth={active ? 3 : 0}
              />
            </g>
          )
        })}

        {/* 하이라이트 라벨 */}
        {highlightRoomId &&
          (() => {
            const r = rooms.find((x) => x.id === highlightRoomId)
            if (!r?.pos) return null
            return (
              <g pointerEvents="none">
                <rect
                  x={r.pos.cx - 26}
                  y={r.pos.y - 26}
                  width={52}
                  height={20}
                  rx={10}
                  fill="#BE3A60"
                />
                <text x={r.pos.cx} y={r.pos.y - 12} fontSize={12} fill="#fff" textAnchor="middle" fontWeight={700}>
                  {r.number}
                </text>
              </g>
            )
          })()}

        {/* 실내 경로선 (목업) */}
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
            <circle cx={routePoints[0][0]} cy={routePoints[0][1]} r={7} fill="#5B6BE8" />
          </g>
        )}
      </svg>
    </div>
  )
}
