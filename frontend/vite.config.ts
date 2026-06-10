import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 카카오맵 JS 키에 등록할 도메인을 고정하기 위해 포트 고정
    // 카카오 developers > 플랫폼 > Web > 사이트 도메인에 http://localhost:5190 등록 필요
    port: 5190,
    strictPort: true,
    host: true,
  },
})
