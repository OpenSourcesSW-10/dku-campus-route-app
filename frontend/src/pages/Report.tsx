import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopBar from '../components/TopBar'
import { useApp } from '../store/useApp'
import { createReport, createTmi, ApiError } from '../lib/api'
import { buildings, indoorMapsOf, roomsOf, buildingById } from '../lib/data'

const TYPES = ['TMI 정보', '강의실 정보'] as const
type LocType = 'OUTDOOR' | 'INDOOR'

export default function Report() {
  const nav = useNavigate()
  const isAuthed = useApp((s) => s.isAuthed)

  const [type, setType] = useState<(typeof TYPES)[number]>('TMI 정보')
  const [name, setName] = useState('') // TMI 이름 / 강의실 제보 제목
  const [tags, setTags] = useState('')
  const [content, setContent] = useState('') // 강의실 정보(제보) 전용

  // TMI 위치
  const [locType, setLocType] = useState<LocType>('OUTDOOR')
  const [bId, setBId] = useState('')
  const [fl, setFl] = useState<number | ''>('')
  const [roomId, setRoomId] = useState('')

  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const isTmi = type === 'TMI 정보'
  const indoorBuildings = useMemo(() => buildings.filter((b) => indoorMapsOf(b.id).length > 0), [])
  const buildingList = locType === 'INDOOR' ? indoorBuildings : buildings
  const floorList = bId ? indoorMapsOf(bId) : []
  const roomList = bId && fl !== '' ? roomsOf(bId, Number(fl)) : []

  const canSubmit = (() => {
    if (loading || !name.trim()) return false
    if (isTmi) {
      if (locType === 'OUTDOOR') return !!bId
      return !!bId && fl !== '' // 실내: 건물 + 층 필수 (호실은 선택)
    }
    return !!content.trim() // 강의실 정보(제보)
  })()

  const submit = async () => {
    if (!canSubmit) return
    if (!isAuthed) {
      setError('등록하려면 로그인이 필요합니다.')
      setTimeout(() => nav('/login'), 800)
      return
    }
    setLoading(true)
    setError('')
    try {
      if (isTmi) {
        if (locType === 'OUTDOOR') {
          const b = buildingById(bId)
          await createTmi({
            name: name.trim(),
            locationType: 'OUTDOOR',
            buildingId: bId,
            latitude: b?.lat ?? null,
            longitude: b?.lng ?? null,
            representativeTags: tags.trim(),
          })
        } else {
          const map = indoorMapsOf(bId).find((m) => m.floor === Number(fl))
          const room = roomId ? roomsOf(bId, Number(fl)).find((r) => r.id === roomId) : undefined
          await createTmi({
            name: name.trim(),
            locationType: 'INDOOR',
            buildingId: bId,
            floorNumber: Number(fl),
            indoorMapId: map ? `MAP_${bId}_${map.floorLabel}` : null,
            roomId: roomId || null,
            mapX: room?.pos?.cx ?? null,
            mapY: room?.pos?.cy ?? null,
            representativeTags: tags.trim(),
          })
        }
      } else {
        await createReport({
          reportType: 'ROOM_INFO',
          targetType: 'ROOM',
          buildingId: bId || null,
          roomId: roomId || null,
          title: name.trim(),
          content: content.trim(),
          tags: tags.trim(),
        })
      }
      setDone(true)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : '등록에 실패했습니다. 잠시 후 다시 시도해주세요.')
    } finally {
      setLoading(false)
    }
  }

  const onChangeLocType = (lt: LocType) => {
    setLocType(lt)
    setBId('')
    setFl('')
    setRoomId('')
  }

  return (
    <div className="flex h-full flex-col bg-white">
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

        <label className="mt-5 block text-[14px] font-semibold text-ink">
          {isTmi ? 'TMI 이름' : '장소'}
        </label>
        <input
          className="field mt-2"
          placeholder={isTmi ? '예: 콘센트 있는 자리 / 조용한 휴게실' : '예: 소프트웨어 ICT관 305호'}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        {/* TMI: 위치 선택 */}
        {isTmi && (
          <>
            <label className="mt-5 block text-[14px] font-semibold text-ink">위치 유형</label>
            <div className="mt-2 flex gap-2">
              {(['OUTDOOR', 'INDOOR'] as LocType[]).map((lt) => (
                <button
                  key={lt}
                  onClick={() => onChangeLocType(lt)}
                  className={`flex-1 rounded-lg border py-2.5 text-[14px] font-medium ${
                    locType === lt ? 'border-primary bg-primary/5 text-primary' : 'border-line text-ink-soft'
                  }`}
                >
                  {lt === 'OUTDOOR' ? '실외(건물)' : '실내(층·호실)'}
                </button>
              ))}
            </div>

            <label className="mt-5 block text-[14px] font-semibold text-ink">건물</label>
            <select
              className="field mt-2"
              value={bId}
              onChange={(e) => {
                setBId(e.target.value)
                setFl('')
                setRoomId('')
              }}
            >
              <option value="">건물 선택</option>
              {buildingList.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>

            {locType === 'INDOOR' && (
              <>
                <label className="mt-5 block text-[14px] font-semibold text-ink">층</label>
                <select
                  className="field mt-2"
                  value={fl}
                  disabled={!bId}
                  onChange={(e) => {
                    setFl(e.target.value === '' ? '' : Number(e.target.value))
                    setRoomId('')
                  }}
                >
                  <option value="">층 선택</option>
                  {floorList.map((m) => (
                    <option key={m.floor} value={m.floor}>
                      {m.floorLabel}
                    </option>
                  ))}
                </select>

                <label className="mt-5 block text-[14px] font-semibold text-ink">
                  호실 <span className="text-ink-faint">(선택)</span>
                </label>
                <select
                  className="field mt-2"
                  value={roomId}
                  disabled={fl === ''}
                  onChange={(e) => setRoomId(e.target.value)}
                >
                  <option value="">호실 미지정 (층 전체)</option>
                  {roomList.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.number}호{r.name ? ` · ${r.name}` : ''}
                    </option>
                  ))}
                </select>
              </>
            )}
          </>
        )}

        <label className="mt-5 block text-[14px] font-semibold text-ink">태그</label>
        <input
          className="field mt-2"
          placeholder="쉼표로 구분 (예: 콘센트 많음, 조용한 곳)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />

        {/* 강의실 정보(제보): 내용 */}
        {!isTmi && (
          <>
            <label className="mt-5 block text-[14px] font-semibold text-ink">내용</label>
            <textarea
              className="field mt-2 h-32 resize-none"
              placeholder="제보 내용을 입력하세요"
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </>
        )}

        {error && <p className="mt-3 text-[13px] text-primary">{error}</p>}

        <button className="btn-primary mt-6" disabled={!canSubmit} onClick={submit}>
          {loading ? '등록 중…' : isTmi ? 'TMI 등록' : '제보 등록'}
        </button>
        <p className="mt-3 pb-6 text-center text-[11px] text-ink-faint">
          {isTmi
            ? '* 등록 후 검수(pending)되며, 승인되면 지도에 표시됩니다. (실내 위치는 외부 지도에는 표시되지 않습니다)'
            : '* 등록된 제보는 검수(pending) 후 반영됩니다'}
        </p>
      </div>

      {done && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/40 px-10">
          <div className="w-full rounded-2xl bg-white p-6 text-center">
            <p className="text-[17px] font-bold text-ink">
              {isTmi ? 'TMI가 등록되었습니다' : '제보가 등록되었습니다'}
            </p>
            <p className="mt-1 text-[14px] text-ink-soft">
              {type} · {name}
            </p>
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
