import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import StatusBar from '../components/StatusBar'
import TopBar from '../components/TopBar'

const TYPES = ['TMI 정보', '강의실 정보'] as const

export default function Report() {
  const nav = useNavigate()
  const [type, setType] = useState<(typeof TYPES)[number]>('TMI 정보')
  const [place, setPlace] = useState('')
  const [tags, setTags] = useState('')
  const [content, setContent] = useState('')
  const [done, setDone] = useState(false)

  const canSubmit = place.trim() && content.trim()

  return (
    <div className="flex h-full flex-col bg-white">
      <StatusBar />
      <TopBar title="제보하기" onBack={() => nav('/home')} />

      <div className="no-scrollbar flex-1 overflow-y-auto px-5 pt-5">
        <label className="text-[14px] font-semibold text-ink">제보 유형</label>
        <div className="mt-2 flex gap-2">
          {TYPES.map((t) => (
            <button
              key={t}
              onClick={() => setType(t)}
              className={`flex-1 rounded-lg border py-2.5 text-[14px] font-medium ${
                type === t ? 'border-primary bg-primary/5 text-primary' : 'border-line text-ink-soft'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <label className="mt-5 block text-[14px] font-semibold text-ink">장소</label>
        <input
          className="field mt-2"
          placeholder="예: 소프트웨어 ICT관 305호 / 폭포공원"
          value={place}
          onChange={(e) => setPlace(e.target.value)}
        />

        <label className="mt-5 block text-[14px] font-semibold text-ink">태그</label>
        <input
          className="field mt-2"
          placeholder="쉼표로 구분 (예: 콘센트 많음, 조용한 곳)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />

        <label className="mt-5 block text-[14px] font-semibold text-ink">내용</label>
        <textarea
          className="field mt-2 h-32 resize-none"
          placeholder="제보 내용을 입력하세요"
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />

        <button className="btn-primary mt-6" disabled={!canSubmit} onClick={() => setDone(true)}>
          제보 등록
        </button>
        <p className="mt-3 pb-6 text-center text-[11px] text-ink-faint">
          * 등록된 제보는 검수 후 지도에 반영됩니다 (목업)
        </p>
      </div>

      {done && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/40 px-10">
          <div className="w-full rounded-2xl bg-white p-6 text-center">
            <p className="text-[17px] font-bold text-ink">제보가 등록되었습니다</p>
            <p className="mt-1 text-[14px] text-ink-soft">{type} · {place}</p>
            <button
              className="btn-primary mt-5"
              onClick={() => {
                setDone(false)
                nav('/home')
              }}
            >
              확인
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
