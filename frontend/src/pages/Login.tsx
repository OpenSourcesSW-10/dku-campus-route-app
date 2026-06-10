import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopBar from '../components/TopBar'
import { useApp } from '../store/useApp'
import { login as apiLogin, ApiError } from '../lib/api'

export default function Login() {
  const nav = useNavigate()
  const setAuth = useApp((s) => s.setAuth)
  const [studentId, setStudentId] = useState('')
  const [pw, setPw] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    if (!studentId) {
      setError('학번을 입력해주세요')
      return
    }
    if (pw.length < 8 || pw.length > 20) {
      setError('비밀번호는 8~20자 내로 입력해주세요')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await apiLogin(studentId, pw)
      setAuth(res.accessToken, res.user)
      nav('/home')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : '로그인에 실패했습니다. 잠시 후 다시 시도해주세요.')
    } finally {
      setLoading(false)
    }
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
          onKeyDown={(e) => {
            if (e.key === 'Enter') submit()
          }}
        />
        {error && <p className="mt-1.5 text-[13px] text-primary">{error}</p>}
        <button className="btn-primary mt-4" onClick={submit} disabled={loading}>
          {loading ? '로그인 중…' : '로그인'}
        </button>
      </div>
    </div>
  )
}
