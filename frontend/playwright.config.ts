import { defineConfig, devices } from '@playwright/test'

/**
 * E2E 配置：本地连真全栈（后端 8000 + 前端 5173），CI 连 vite preview。
 * baseURL 默认 http://localhost:5173（vite dev），CI 用 E2E_BASE_URL 覆盖为 preview 地址。
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
