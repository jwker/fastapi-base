/**
 * E2E：认证主链路（登录成功 / 登录失败 / 登出）
 *
 * 前置：后端（端口见根 .env BACKEND_PORT）运行中（含种子 admin/admin123），前端（端口见根 .env FRONTEND_PORT，vite dev）
 * 或 CI 中 E2E_BASE_URL 指向 vite preview。
 */
import { test, expect } from '@playwright/test'

async function login(page: import('@playwright/test').Page, username: string, password: string) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill(username)
  await page.getByPlaceholder('密码').fill(password)
  await page.getByRole('button', { name: '登 录' }).click()
}

test.describe('认证主链路', () => {
  test('登录成功：跳转首页（仪表盘）且登录态写入 localStorage', async ({ page }) => {
    await login(page, 'admin', 'admin123')

    // 登录后 '/' 重定向到第一个菜单（仪表盘）
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 })
    await expect(page.getByText('仪表盘', { exact: true }).first()).toBeVisible()

    // 登录态持久化（pinia persistedstate key: fb-user）
    const stored = await page.evaluate(() => localStorage.getItem('fb-user'))
    expect(stored).not.toBeNull()
    expect(JSON.parse(stored || '{}')).toHaveProperty('accessToken')
  })

  test('登录失败：弹出"用户名或密码错误"提示且停留登录页', async ({ page }) => {
    await login(page, 'admin', 'wrong-pass') // 只试 1 次，避免触发登录锁定

    await expect(page.locator('.el-message')).toContainText('用户名或密码错误')
    await expect(page).toHaveURL(/\/login/)
  })

  test('登出：回到登录页且登录态清空', async ({ page }) => {
    await login(page, 'admin', 'admin123')
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 })

    // 右上角用户下拉 → 退出登录（等下拉展开再点，避免动画时序问题）
    await page.locator('.el-dropdown').first().hover()
    const logoutItem = page.getByText('退出登录')
    await expect(logoutItem).toBeVisible({ timeout: 5_000 })
    await logoutItem.click()

    // 确认弹窗（ElMessageBox）→ 确定
    await page.getByRole('button', { name: '确定' }).click()

    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 })
    // 登录态已清空（pinia persistedstate 保留 key、写入空值）
    const stored = JSON.parse(
      (await page.evaluate(() => localStorage.getItem('fb-user'))) || '{}',
    )
    expect(stored.accessToken).toBeFalsy()
    expect(stored.userInfo).toBeNull()
  })
})
