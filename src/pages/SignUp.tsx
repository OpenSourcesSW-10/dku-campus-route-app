import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopBar from '../components/TopBar'

export default function SignUp() {
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [pw, setPw] = useState('')
  const [pw2, setPw2] = useState('')

  const pwValid = pw.length >= 8 && pw.length <= 20
  const match = pw2.length === 0 || pw === pw2
  const canSubmit = email.includes('@') && pwValid && pw === pw2

  return (
    <div className="flex h-full flex-col bg-white">
      <TopBar title="회원가입" onBack={() => nav('/landing')} />
      <div className="flex-1 px-5 pt-10">
        <input
          className="field"
          placeholder="이메일"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <input
          className={`field mt-5 ${pw && !pwValid ? 'border-primary' : ''}`}
          type="password"
          placeholder="비밀번호"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
        />
        <p className="mt-1.5 text-[13px] text-primary">비밀번호는 8~20자 내로 입력해주세요</p>

        <input
          className={`field mt-3 ${pw2 && !match ? 'border-primary' : ''}`}
          type="password"
          placeholder="비밀번호 확인"
          value={pw2}
          onChange={(e) => setPw2(e.target.value)}
        />
        <p className="mt-1.5 text-[13px] text-primary">
          {pw2 && !match ? '비밀번호가 일치하지 않습니다' : '비밀번호는 8~20자 내로 입력해주세요'}
        </p>

        <button className="btn-primary mt-6" disabled={!canSubmit} onClick={() => nav('/login')}>
          회원가입
        </button>
      </div>
    </div>
  )
}
