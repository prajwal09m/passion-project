import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Allow tunnel share URLs (judges use YOUR key blind via your machine).
    allowedHosts: ['.loca.lt', '.ngrok-free.app', '.ngrok.io', '.trycloudflare.com'],
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
  },
})
