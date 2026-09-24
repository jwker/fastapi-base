import { fileURLToPath, URL } from 'node:url'
import path from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 根 .env：FRONTEND_PORT / BACKEND_PORT（跨层端口唯一事实源）；frontend/.env：VITE_* 业务与代理变量
  const rootEnv = loadEnv(mode, path.resolve(__dirname, '..'), '')
  const frontendEnv = loadEnv(mode, __dirname, '')
  const env = { ...rootEnv, ...frontendEnv }
  // dev 代理目标：默认跟随根 .env BACKEND_PORT；后端不在本机时用 VITE_PROXY_TARGET 显式覆盖
  const proxyTarget = env.VITE_PROXY_TARGET || `http://localhost:${env.BACKEND_PORT || '8000'}`
  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: '0.0.0.0',
      port: Number(env.FRONTEND_PORT || 5173),
      proxy: {
        // 开发环境代理到后端，避免 CORS（目标由 BACKEND_PORT 派生或 VITE_PROXY_TARGET 覆盖）
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
        // 上传文件静态访问（后端 StaticFiles 挂载 /uploads）
        '/uploads': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      chunkSizeWarningLimit: 1500,
    },
  }
})
