/**
 * CI 诊断专用：捕获登录请求的浏览器侧真实错误（console / requestfailed / 响应状态）。
 * 定位"curl 通但浏览器挂"的 runner 环境差异。CI 跑完后删除本文件。
 */
import { test } from '@playwright/test'

test('诊断：登录请求链路（打印网络与控制台）', async ({ page }) => {
  const logs: string[] = []
  page.on('console', (m) => logs.push(`[console:${m.type()}] ${m.text()}`))
  page.on('requestfailed', (r) =>
    logs.push(`[requestfailed] ${r.url()} -> ${r.failure()?.errorText}`),
  )
  page.on('response', (r) => {
    if (r.url().includes('/api/')) logs.push(`[response] ${r.status()} ${r.url()}`)
  })

  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('admin')
  await page.getByPlaceholder('密码').fill('admin123')
  await page.getByRole('button', { name: '登 录' }).click()
  await page.waitForTimeout(4000)

  console.log('===== DIAGNOSE_BEGIN =====')
  console.log(logs.join('\n') || '(no api/console events captured)')
  console.log('URL:', page.url())
  console.log('fb-user:', await page.evaluate(() => localStorage.getItem('fb-user')))
  console.log('===== DIAGNOSE_END =====')
})
