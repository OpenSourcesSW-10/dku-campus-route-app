import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import TopBar from '../components/TopBar'
import { useApp } from '../store/useApp'
import { register as apiRegister, ApiError } from '../lib/api'

export default function SignUp() {
  const nav = useNavigate()
  const setAuth = useApp((s) => s.setAuth)
  const [sid, setSid] = useState('')
  const [pw, setPw] = useState('')
  const [pw2, setPw2] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const pwValid = pw.length >= 8 && pw.length <= 20
  const match = pw2.length === 0 || pw === pw2
  const canSubmit = sid.length > 0 && pwValid && pw === pw2 && !loading

  const submit = async () => {
    if (!canSubmit) return
    setLoading(true)
    setError('')
    try {
      // 회원가입 성공 시 토큰이 함께 발급되므로 바로 로그인 상태로 진입한다.
      const res = await apiRegister(sid, pw)
      setAuth(res.accessToken, res.user)
      nav('/home')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : '회원가입에 실패했습니다. 잠시 후 다시 시도해주세요.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-full flex-col bg-white">
      <TopBar title="회원가입" onBack={() => nav('/landing')} />
      <div className="flex-1 px-5 pt-10">
        <input
          className="field"
          inputMode="numeric"
          placeholder="학번"
          value={sid}
          onChange={(e) => {
            setSid(e.target.value.replace(/\D/g, ''))
            if (error) setError('')
          }}
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

        {error && <p className="mt-2 text-[13px] text-primary">{error}</p>}

        <button className="btn-primary mt-6" disabled={!canSubmit} onClick={submit}>
          {loading ? '가입 중…' : '회원가입'}
        </button>
      </div>
    </div>
  )
}
