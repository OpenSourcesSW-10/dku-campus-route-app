import { useNavigate } from 'react-router-dom'
import { PersonIcon } from './Icons'
import { useApp } from '../store/useApp'

interface Props {
  open: boolean
  onClose: () => void
}

const MENU = [
  { label: '길찾기', to: '/home' },
  { label: '강의실 정보', to: '/indoor' },
  { label: 'TMI 정보', to: '/tmi' },
  { label: '제보하기', to: '/report' },
]

export default function Drawer({ open, onClose }: Props) {
  const nav = useNavigate()
  const user = useApp((s) => s.user)

  return (
    <>
      {/* dim */}
      <div
        onClick={onClose}
        className={`absolute inset-0 z-40 bg-black/30 transition-opacity ${
          open ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
      />
      {/* panel */}
      <aside
        className={`absolute inset-y-0 left-0 z-50 flex w-[74%] max-w-[320px] flex-col bg-white px-6 pt-6 shadow-2xl transition-transform duration-300 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="mt-6 flex flex-col items-center">
          <div className="flex h-24 w-24 items-center justify-center rounded-full bg-gray-100 text-gray-700">
            <PersonIcon className="h-14 w-14" />
          </div>
          <span className="mt-3 text-[17px] text-ink">{user ?? 'user'}</span>
        </div>

        <nav className="mt-10 flex flex-col gap-3">
          {MENU.map((m, i) => (
            <button
              key={m.to}
              onClick={() => {
                onClose()
                nav(m.to)
              }}
              style={{ animationDelay: open ? `${i * 60 + 100}ms` : '0ms' }}
              className={`press rounded-xl px-5 py-4 text-left text-[17px] ${
                open ? 'animate-fade-up' : ''
              } ${i === 0 ? 'bg-primary font-semibold text-white' : 'bg-gray-100 text-ink'}`}
            >
              {m.label}
            </button>
          ))}
        </nav>
      </aside>
    </>
  )
}
