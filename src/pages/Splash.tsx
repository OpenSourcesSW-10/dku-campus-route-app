import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { HeartIcon } from '../components/Icons'

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
          <HeartIcon className="h-12 w-12 text-white" />
        </div>
      </button>
    </div>
  )
}
