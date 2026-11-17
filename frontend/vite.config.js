import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 端口可用环境变量覆盖：UV_PORT（前端端口）、UV_BACKEND（后端地址）、UV_HOST（绑定地址）
// 默认：前端 5173 @127.0.0.1，后端 http://localhost:8000（与 README 启动说明一致）
const port = Number(process.env.UV_PORT) || 5173
const backend = process.env.UV_BACKEND || 'http://localhost:8000'
const host = process.env.UV_HOST || '127.0.0.1'
const base = process.env.VITE_BASE || '/'

export default defineConfig({
  base,
  plugins: [vue()],
  server: {
    host,
    port,
    proxy: {
      '/api': { target: backend, changeOrigin: true },
      '/share': { target: backend, changeOrigin: true },
      '/generated': { target: backend, changeOrigin: true }
    }
  }
})
