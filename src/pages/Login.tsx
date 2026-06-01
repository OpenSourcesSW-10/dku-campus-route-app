import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopBar from '../components/TopBar'
import { useApp } from '../store/useApp'

export default function Login() {
  const nav = useNavigate()
  const login = useApp((s) => s.login)
  const [email, setEmail] = useState('')
  const [pw, setPw] = useState('')
  const [showPwError, setShowPwError] = useState(false)

  const submit = () => {
    if (pw.length < 8 || pw.length > 20) {
      setShowPwError(true)
      return
    }
    // 목업: 형식만 맞으면 통과
    login(email || 'user@dankook.ac.kr')
    nav('/home')
  }

  return (
    <div className="flex h-full flex-col bg-white">
      <TopBar title="로그인" onBack={() => nav('/landing')} />
      <div className="flex-1 px-5 pt-10">
        <input
          className="field"
          placeholder="이메일"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="field mt-5"
          type="password"
          placeholder="비밀번호"
          value={pw}
          onChange={(e) => {
            setPw(e.target.value)
            if (showPwError) setShowPwError(false)
          }}
        />
        {showPwError && (
          <p className="mt-1.5 text-[13px] text-primary">비밀번호는 8~20자 내로 입력해주세요</p>
        )}
        <button className="btn-primary mt-4" onClick={submit}>
          로그인
        </button>
      </div>
    </div>
  )
}
