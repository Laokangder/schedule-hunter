import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(() => {
  const apiTarget = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'
  return ({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true
      },
      '/ws': {
        target: apiTarget.replace(/^http/, 'ws'),
        ws: true
      }
    }
  }
  })
})
