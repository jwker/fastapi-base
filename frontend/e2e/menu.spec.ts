/**
 * E2E：动态路由 / 侧边菜单加载
 *
 * 前置：后端 8000 运行中（种子菜单：仪表盘/系统管理组/文件管理），前端 5173。
 * admin 为超管，登录后应看到全部菜单并进入各管理页正常渲染。
 */
import { test, expect } from '@playwright/test'

async function loginAdmin(page: import('@playwright/test').Page) {
  await page.goto('/login')
  await page.getByPlaceholder('用户名').fill('admin')
  await page.getByPlaceholder('密码').fill('admin123')
  await page.getByRole('button', { name: '登 录' }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 })
}

test.describe('动态路由与菜单', () => {
  test('登录后侧边菜单完整加载（一级 + 展开分组后子菜单可见）', async ({ page }) => {
    await loginAdmin(page)

    // 一级菜单
    for (const name of ['仪表盘', '系统管理', '文件管理']) {
      await expect(page.getByText(name, { exact: true }).first()).toBeVisible()
    }

    // 展开"系统管理"分组后，子菜单可见
    await page.getByText('系统管理', { exact: true }).first().click()
    for (const name of ['用户管理', '角色管理', '字典管理', '操作日志']) {
      await expect(page.getByText(name, { exact: true }).first()).toBeVisible()
    }
  })

  test('点击"用户管理"进入 /users 且表格正常渲染', async ({ page }) => {
    await loginAdmin(page)

    // 先展开"系统管理"分组，再点子菜单
    await page.getByText('系统管理', { exact: true }).first().click()
    await page.getByText('用户管理', { exact: true }).first().click()
    await expect(page).toHaveURL(/\/users/, { timeout: 10_000 })

    // 表格出现表头（ProTable 由列配置渲染）
    await expect(page.locator('table').first()).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('用户名', { exact: true }).first()).toBeVisible()
  })
})
