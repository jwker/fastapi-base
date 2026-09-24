import fs from 'node:fs'
import path from 'node:path'
import { defineConfig, devices } from '@playwright/test'

/**
 * E2E 配置：本地连真全栈（后端端口见根 .env BACKEND_PORT + 前端 dev），CI 连 vite preview。
 * baseURL 默认读根 .env 的 FRONTEND_PORT（http://localhost:<port>），CI 用 E2E_BASE_URL 覆盖为 preview 地址。
 */
function readFrontendPort(): string {
  try {
    const envPath = path.resolve(__dirname, '../.env')
    const content = fs.readFileSync(envPath, 'utf-8')
    const m = content.match(/^FRONTEND_PORT=(\d+)/m)
    if (m) return m[1]
  } catch {
    // 忽略：无根 .env 时回退默认端口
  }
  return '5173'
}

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL || `http://localhost:${readFrontendPort()}`,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
