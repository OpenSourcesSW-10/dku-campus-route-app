import { useEffect, useState } from 'react'

// 카카오맵 JS SDK를 동적 로드한다. (autoload=false 후 maps.load 콜백)
declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    kakao: any
  }
}

const KEY = import.meta.env.VITE_KAKAO_JS_KEY as string | undefined

let loadPromise: Promise<void> | null = null

function loadSdk(): Promise<void> {
  if (loadPromise) return loadPromise
  loadPromise = new Promise<void>((resolve, reject) => {
    if (window.kakao && window.kakao.maps) {
      resolve()
      return
    }
    if (!KEY) {
      reject(new Error('VITE_KAKAO_JS_KEY 가 설정되지 않았습니다.'))
      return
    }
    const script = document.createElement('script')
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KEY}&autoload=false&libraries=services`
    script.async = true
    script.onload = () => window.kakao.maps.load(() => resolve())
    script.onerror = () => reject(new Error('카카오맵 SDK 로드 실패'))
    document.head.appendChild(script)
  })
  return loadPromise
}

export function useKakao() {
  const [ready, setReady] = useState(!!(window.kakao && window.kakao.maps))
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    loadSdk()
      .then(() => mounted && setReady(true))
      .catch((e) => mounted && setError(e.message))
    return () => {
      mounted = false
    }
  }, [])

  return { ready, error }
}

// 죽전캠퍼스 중심 좌표
export const CAMPUS_CENTER = { lat: 37.3216, lng: 127.1277 }
