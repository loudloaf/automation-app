import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev: http://localhost:5173 (API & login diteruskan ke FastAPI :8000). Build: hasil di ./dist, disajikan oleh main.py
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000', '/auth': 'http://localhost:8000' } },
  build: { outDir: 'dist', chunkSizeWarningLimit: 900 },
})
