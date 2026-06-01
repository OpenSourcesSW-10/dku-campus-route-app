import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Splash() {
  const nav = useNavigate()
  useEffect(() => {
    const t = setTimeout(() => nav('/landing'), 1400)
    return () => clearTimeout(t)
  }, [nav])

  return (
    <div className="flex h-full flex-col bg-white">
      <button
        onClick={() => nav('/landing')}
        className="flex flex-1 items-center justify-center"
        aria-label="시작"
      >
        <div className="flex h-28 w-28 items-center justify-center rounded-3xl bg-primary">
          <img src="/heart-white.svg" alt="" className="h-14 w-14" />
        </div>
      </button>
    </div>
  )
}
