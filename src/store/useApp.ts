import { create } from 'zustand'

interface AppState {
  // 목업 인증 (이메일 로그인 - 아무 값이나 통과)
  user: string | null
  login: (email: string) => void
  logout: () => void

  // 길찾기 출발/도착 (장소명 텍스트)
  routeStart: string
  routeDest: string
  setRoute: (start: string, dest: string) => void
}

export const useApp = create<AppState>((set) => ({
  user: null,
  login: (email) => set({ user: email.split('@')[0] || 'user' }),
  logout: () => set({ user: null }),

  routeStart: '내 위치',
  routeDest: '',
  setRoute: (routeStart, routeDest) => set({ routeStart, routeDest }),
}))
