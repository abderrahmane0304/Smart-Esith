import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
// Le build est généré directement dans backend/static/dashboard et servi par Flask sur /dashboard.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'build' ? '/static/dashboard/' : '/',
  server: {
    proxy: {
      '/api': 'http://localhost:5001',
      '/static': 'http://localhost:5001',
    },
  },
  build: {
    outDir: '../backend/static/dashboard',
    emptyOutDir: true,
  },
}))
