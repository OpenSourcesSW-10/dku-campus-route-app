import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { hydrateBuildings } from './lib/data'

// 건물/별칭 목록을 백엔드에서 미리 받아 로컬 데이터를 보강한다.
// 렌더를 막지 않고 백그라운드로 진행한다(백엔드 콜드스타트 대비). 실패해도 로컬 데이터로 동작한다.
void hydrateBuildings()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
