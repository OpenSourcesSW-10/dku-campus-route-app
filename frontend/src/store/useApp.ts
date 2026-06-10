import { create } from 'zustand'
import { getToken, setToken, type ApiUser } from '../lib/api'

const USER_KEY = 'dku_user'

function loadUser(): ApiUser | null {
  try {
    const s = localStorage.getItem(USER_KEY)
    return s ? (JSON.parse(s) as ApiUser) : null
  } catch {
    return null
  }
}

function saveUser(user: ApiUser | null): void {
  try {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
    else localStorage.removeItem(USER_KEY)
  } catch {
    /* 무시 */
  }
}

interface AppState {
  // 인증 (백엔드 JWT)
  token: string | null
  user: ApiUser | null
  isAuthed: boolean
  setAuth: (token: string, user: ApiUser) => void
  logout: () => void

  // 길찾기 출발/도착 (장소명 텍스트)
  routeStart: string
  routeDest: string
  setRoute: (start: string, dest: string) => void
}

export const useApp = create<AppState>((set) => ({
  token: getToken(),
  user: loadUser(),
  isAuthed: !!getToken(),

  setAuth: (token, user) => {
    setToken(token)
    saveUser(user)
    set({ token, user, isAuthed: true })
  },
  logout: () => {
    setToken(null)
    saveUser(null)
    set({ token: null, user: null, isAuthed: false })
  },

  routeStart: '내 위치',
  routeDest: '',
  setRoute: (routeStart, routeDest) => set({ routeStart, routeDest }),
}))
