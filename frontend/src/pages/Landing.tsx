import { useNavigate } from 'react-router-dom'

export default function Landing() {
  const nav = useNavigate()
  return (
    <div className="flex h-full flex-col bg-white">
      <div className="flex flex-1 items-center justify-center">
        <h1 className="animate-fade-up text-[44px] font-extrabold tracking-tight text-ink-soft">DKU WAY</h1>
      </div>
      <div className="animate-fade-in px-6 pb-10" style={{ animationDelay: '0.2s' }}>
        <button className="btn-primary" onClick={() => nav('/login')}>
          학번으로 로그인
        </button>
        <button
          onClick={() => nav('/signup')}
          className="mt-5 w-full text-center text-[15px] text-ink transition-colors active:text-primary"
        >
          단국대 학번으로 가입하기
        </button>
      </div>
    </div>
  )
}
