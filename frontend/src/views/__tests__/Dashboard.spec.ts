/**
 * Dashboard 仪表盘测试：统计数据仅超级管理员可见。
 *
 * 覆盖：
 * - 超管：渲染统计卡片并请求 /stats/overview
 * - 普通用户：隐藏统计卡片且不发起请求（欢迎卡片保留）
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import { Avatar, Lock, Menu, User } from '@element-plus/icons-vue'
import Dashboard from '@/views/Dashboard.vue'
import { statsApi } from '@/api'
import { useUserStore } from '@/stores/user'

vi.mock('@/api', () => ({
  statsApi: { overview: vi.fn() },
}))

function mountDashboard(isSuperuser: boolean) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useUserStore()
  store.userInfo = {
    id: 1,
    username: 'admin',
    nickname: '管理员',
    email: '',
    avatar: '',
    is_superuser: isSuperuser,
    permissions: isSuperuser ? ['*'] : [],
    roles: [],
  } as any
  const wrapper = mount(Dashboard, {
    global: {
      plugins: [pinia, ElementPlus],
      components: { User, Avatar, Lock, Menu },
    },
  })
  return { wrapper, store }
}

const overviewData = {
  code: 0,
  message: 'ok',
  data: { user_count: 5, role_count: 3, permission_count: 14, menu_count: 6 },
}

describe('Dashboard 统计数据（仅超管）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('超管：显示统计卡片并请求统计数据', async () => {
    vi.mocked(statsApi.overview).mockResolvedValue(overviewData as any)
    const { wrapper } = mountDashboard(true)
    await flushPromises()

    expect(statsApi.overview).toHaveBeenCalledTimes(1)
    expect(wrapper.find('.stats-row').exists()).toBe(true)
    expect(wrapper.text()).toContain('5') // user_count
    expect(wrapper.text()).toContain('14') // permission_count
    expect(wrapper.text()).toContain('菜单')
  })

  it('普通用户：隐藏统计卡片且不请求数据', async () => {
    const { wrapper } = mountDashboard(false)
    await flushPromises()

    expect(statsApi.overview).not.toHaveBeenCalled()
    expect(wrapper.find('.stats-row').exists()).toBe(false)
    // 欢迎卡片对普通用户保留
    expect(wrapper.text()).toContain('欢迎回来')
  })
})
