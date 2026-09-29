import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// `npm run dev` on a dev machine: the page comes from Vite, /api and /ws
// are forwarded to the local FastAPI + tty proxy, same paths as Caddy uses
// in production. `npm run build` writes dist/, which Caddy serves.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/ws': { target: 'ws://127.0.0.1:7681', ws: true },
    },
  },
})
