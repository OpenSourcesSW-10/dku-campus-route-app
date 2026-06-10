import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { BackIcon } from './Icons'

interface Props {
  title: string
  onBack?: () => void
  right?: ReactNode
}

export default function TopBar({ title, onBack, right }: Props) {
  const nav = useNavigate()
  return (
    <div className="relative flex h-14 shrink-0 items-center border-b border-line px-3">
      <button
        aria-label="뒤로"
        onClick={() => (onBack ? onBack() : nav(-1))}
        className="z-10 flex h-10 w-10 items-center justify-center text-ink"
      >
        <BackIcon className="h-6 w-6" />
      </button>
      <h1 className="pointer-events-none absolute inset-x-0 text-center text-[18px] font-bold text-ink">
        {title}
      </h1>
      <div className="z-10 ml-auto">{right}</div>
    </div>
  )
}
