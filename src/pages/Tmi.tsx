import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import CampusMap from '../features/map/CampusMap'
import { BackIcon, CloseIcon } from '../components/Icons'
import { TMI_CATEGORIES, TMI_MARKERS, type TmiCategory, type TmiMarker } from '../data/mock'

export default function Tmi() {
  const nav = useNavigate()
  const [enabled, setEnabled] = useState<Set<TmiCategory>>(
    () => new Set(TMI_CATEGORIES.map((c) => c.key)),
  )
  const [picked, setPicked] = useState<TmiMarker | null>(null)

  const visible = useMemo(() => TMI_MARKERS.filter((m) => enabled.has(m.category)), [enabled])

  const toggle = (k: TmiCategory) =>
    setEnabled((prev) => {
      const next = new Set(prev)
      next.has(k) ? next.delete(k) : next.add(k)
      return next
    })

  return (
    <div className="relative flex h-full flex-col bg-white">
      <div className="absolute inset-x-0 top-0 z-30 px-4 pt-3">
        <div className="flex items-center gap-3 rounded-2xl bg-white px-4 py-3 shadow-card">
          <button onClick={() => nav('/home')} aria-label="뒤로" className="text-ink">
            <BackIcon className="h-6 w-6" />
          </button>
          <span className="text-[16px] font-bold text-ink">TMI 정보</span>
        </div>
      </div>

      <div className="relative flex-1">
        <CampusMap className="absolute inset-0" tmi={visible} onSelectTmi={setPicked} />

        {/* 마커 팝업 */}
        {picked && (
          <div className="absolute inset-x-4 bottom-4 z-20 rounded-2xl bg-white p-4 shadow-sheet">
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-[16px] font-bold text-ink">{picked.name}</p>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {picked.tags.map((t) => (
                    <span key={t} className="rounded-full bg-primary/10 px-2 py-0.5 text-[12px] text-primary">
                      #{t}
                    </span>
                  ))}
                </div>
                <p className="mt-2 text-[14px] text-ink-soft">{picked.content}</p>
                <p className="mt-2 text-[12px] text-ink-faint">제보자 · {picked.author}</p>
              </div>
              <button onClick={() => setPicked(null)} className="p-1 text-ink-faint" aria-label="닫기">
                <CloseIcon className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 마커 필터링 */}
      <div className="rounded-t-2xl bg-white px-5 pb-7 pt-4 shadow-sheet">
        <p className="text-center text-[16px] font-bold text-ink">마커 필터링</p>
        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3">
          {TMI_CATEGORIES.map((c) => {
            const on = enabled.has(c.key)
            return (
              <button key={c.key} onClick={() => toggle(c.key)} className="flex items-center gap-2.5 text-left">
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded ${
                    on ? 'bg-[#2C7BE5] text-white' : 'border border-line text-transparent'
                  }`}
                >
                  ✓
                </span>
                <span className="h-3 w-3 rounded-full" style={{ background: c.color }} />
                <span className="text-[15px] text-ink">{c.label}</span>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
