import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopBar from '../components/TopBar'
import { useApp } from '../store/useApp'

export default function Login() {
  const nav = useNavigate()
  const login = useApp((s) => s.login)
  const [studentId, setStudentId] = useState('')
  const [pw, setPw] = useState('')
  const [error, setError] = useState('')

  const submit = () => {
    // 목업: 비밀번호 형식만 확인 (학번은 숫자만 입력)
    if (pw.length < 8 || pw.length > 20) {
      setError('비밀번호는 8~20자 내로 입력해주세요')
      return
    }
    login(studentId)
    nav('/home')
  }

  return (
    <div className="flex h-full flex-col bg-white">
      <TopBar title="로그인" onBack={() => nav('/landing')} />
      <div className="flex-1 px-5 pt-10">
        <input
          className="field"
          inputMode="numeric"
          placeholder="학번"
          value={studentId}
          onChange={(e) => {
            setStudentId(e.target.value.replace(/\D/g, ''))
            if (error) setError('')
          }}
        />
        <input
          className="field mt-5"
          type="password"
          placeholder="비밀번호"
          value={pw}
          onChange={(e) => {
            setPw(e.target.value)
            if (error) setError('')
          }}
        />
        {error && <p className="mt-1.5 text-[13px] text-primary">{error}</p>}
        <button className="btn-primary mt-4" onClick={submit}>
          로그인
        </button>
      </div>
    </div>
  )
}
