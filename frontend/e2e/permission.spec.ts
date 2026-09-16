/**
 * E2E：按钮权限（v-permission）
 *
 * 前置：后端 8000 运行中，前端 5173。
 * admin 为超管（权限通配 *），用户管理页"新增用户"按钮应可见可用。
 * 普通用户（角色受限）的按钮隐藏场景列入第二版（需造非超管账号）。
 */
import { test, expect } from '@playwright/test'

test.describe('按钮权限（超管）', () => {
  test('admin 可见"新增用户"按钮且可打开弹窗', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('用户名').fill('admin')
    await page.getByPlaceholder('密码').fill('admin123')
    await page.getByRole('button', { name: '登 录' }).click()
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 })

    await page.getByText('系统管理', { exact: true }).first().click()
    await page.getByText('用户管理', { exact: true }).first().click()
    await expect(page).toHaveURL(/\/users/, { timeout: 10_000 })

    const addBtn = page.getByRole('button', { name: '新增用户' })
    await expect(addBtn).toBeVisible({ timeout: 10_000 })
    await addBtn.click()
    await expect(page.getByRole('dialog').getByText('新增用户')).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog')).not.toBeVisible()
  })
})
