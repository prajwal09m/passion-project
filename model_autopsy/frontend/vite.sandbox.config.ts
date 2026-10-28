// Temporary demo-audit sandbox config: dev server on :5174 proxying to the
// sandbox backend on :8001 (a throwaway COPY of the app DB). Used only for
// exercising the full write-path workflow without touching the real
// application database. Safe to delete after the audit.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: { '/api': { target: 'http://127.0.0.1:8001', changeOrigin: true } },
  },
})
