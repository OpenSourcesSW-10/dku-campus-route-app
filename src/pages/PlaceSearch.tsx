import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import StatusBar from '../components/StatusBar'
import TopBar from '../components/TopBar'
import { SearchIcon, PinIcon } from '../components/Icons'
import { search, buildings, indoorMapsOf, type SearchHit } from '../lib/data'

const PAGE = 7

// 검색 전 기본 노출: 주요 건물 + 대표 강의실
const DEFAULT_HITS: SearchHit[] = [
  ...search('소프트305').slice(0, 1),
  ...buildings.map<SearchHit>((b) => ({
    kind: 'building',
    building: b,
    title: b.name,
    subtitle: '단국대 죽전캠퍼스 주요 장소',
  })),
]

export default function PlaceSearch() {
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const [page, setPage] = useState(0)

  const hits = useMemo(() => {
    setPage(0)
    return q.trim() ? search(q) : DEFAULT_HITS
  }, [q])

  const pages = Math.max(1, Math.ceil(hits.length / PAGE))
  const view = hits.slice(page * PAGE, page * PAGE + PAGE)

  const go = (h: SearchHit) => {
    if (h.kind === 'room' && h.room) {
      nav(`/indoor/${h.building.id}/${h.room.floor}?room=${h.room.id}`)
    } else {
      const maps = indoorMapsOf(h.building.id)
      if (maps.length) nav(`/indoor/${h.building.id}/${maps[0].floor}`)
      else nav('/home')
    }
  }

  return (
    <div className="flex h-full flex-col bg-white">
      <StatusBar />
      <TopBar title="장소 검색" />
      <div className="px-5 pt-6">
        <div className="flex items-center gap-2 rounded-lg border border-line px-4 py-3">
          <input
            autoFocus
            className="flex-1 text-[15px] outline-none placeholder:text-ink-faint"
            placeholder="장소 또는 강의실로 검색"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <SearchIcon className="h-5 w-5 text-ink" />
        </div>
      </div>

      <div className="no-scrollbar flex-1 overflow-y-auto px-5">
        {view.length === 0 && (
          <p className="mt-16 text-center text-[15px] text-ink-faint">검색 결과가 없습니다.</p>
        )}
        {view.map((h, i) => (
          <button
            key={(h.room?.id ?? h.building.id) + i}
            onClick={() => go(h)}
            className="flex w-full items-center gap-3 border-b border-line py-4 text-left"
          >
            <PinIcon className="h-5 w-5 shrink-0 text-primary" />
            <div className="min-w-0">
              <p className="truncate text-[16px] font-bold text-ink">{h.title}</p>
              <p className="truncate text-[13px] text-ink-faint">{h.subtitle}</p>
            </div>
          </button>
        ))}
      </div>

      <div className="flex items-center justify-between px-6 py-4 text-[15px] text-ink-soft">
        <button disabled={page === 0} onClick={() => setPage((p) => p - 1)} className="disabled:opacity-30">
          ‹ 이전페이지
        </button>
        <span className="text-[13px] text-ink-faint">
          {page + 1} / {pages}
        </span>
        <button
          disabled={page >= pages - 1}
          onClick={() => setPage((p) => p + 1)}
          className="disabled:opacity-30"
        >
          다음페이지 ›
        </button>
      </div>
    </div>
  )
}
