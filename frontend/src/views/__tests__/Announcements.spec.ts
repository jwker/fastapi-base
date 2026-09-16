/**
 * 用户端公告页（Announcements）测试。
 *
 * 覆盖：
 * - 列表渲染：请求 publicList，标题/置顶标记/类型标签
 * - 详情：点击行 → publicDetail → 抽屉展示正文
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import Announcements from '@/views/Announcements.vue'
import { announcementApi } from '@/api'
import { useUserStore } from '@/stores/user'

if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}

vi.mock('@/api', () => ({
  announcementApi: { publicList: vi.fn(), publicDetail: vi.fn() },
}))

const wrappers: VueWrapper[] = []
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
})

beforeEach(() => {
  vi.clearAllMocks()
})

function mountList() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useUserStore()
  store.userInfo = {
    id: 2,
    username: 'zhangsan',
    nickname: '张三',
    email: '',
    avatar: '',
    is_superuser: false,
    permissions: [],
    roles: [],
  } as any
  ;(announcementApi.publicList as ReturnType<typeof vi.fn>).mockResolvedValue({
    code: 0,
    data: {
      total: 2,
      items: [
        { id: 1, title: '系统维护通知', type: 'notice', is_top: false, publish_time: '2026-09-17 10:00:00' },
        { id: 2, title: '新功能上线公告', type: 'announcement', is_top: true, publish_time: '2026-09-16 12:00:00' },
      ],
    },
  })
  const wrapper = mount(Announcements, {
    global: { plugins: [pinia, ElementPlus] },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('用户端公告页', () => {
  it('渲染：请求 publicList 并展示标题/置顶/类型标签', async () => {
    const wrapper = mountList()
    await flushPromises()
    await nextTick()

    expect(announcementApi.publicList).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, page_size: 10 }),
    )
    const text = wrapper.text()
    expect(text).toContain('系统维护通知')
    expect(text).toContain('新功能上线公告')
    expect(text).toContain('置顶')
    expect(text).toContain('通知')
    expect(text).toContain('公告')
  })

  it('详情：点击查看 → publicDetail 调用并展示正文', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(announcementApi.publicDetail as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: {
        id: 2,
        title: '新功能上线公告',
        content: '参数配置模块已上线，请前往系统管理查看。',
        type: 'announcement',
        status: 1,
        is_top: true,
        expire_time: null,
        publish_time: '2026-09-16 12:00:00',
        created_by: 1,
        created_by_name: 'admin',
        created_at: '2026-09-16 12:00:00',
        updated_at: '2026-09-16 12:00:00',
      },
    })

    // 跳过 jsdom 幽灵空行的"查看"按钮，取最后一个（真实数据行 id=2）
    const viewBtns = wrapper.findAll('button').filter((b) => b.text().includes('查看'))
    await viewBtns.at(-1)!.trigger('click')
    await flushPromises()

    expect(announcementApi.publicDetail).toHaveBeenCalledWith(2)
    expect(wrapper.text()).toContain('参数配置模块已上线')
  })
})
