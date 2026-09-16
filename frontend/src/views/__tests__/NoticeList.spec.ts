/**
 * 公告管理页（NoticeList）测试。
 *
 * 覆盖：
 * - 列表渲染：标题/类型标签/状态标签
 * - 新增：必填被 ProForm 防线拦截 → 填完 create 调用 + 刷新
 * - 发布：草稿行显示"发布"→ publish 调用 + 刷新；已发布行显示"下线"
 * - 删除：确认弹窗 → remove 调用
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus, { ElMessageBox } from 'element-plus'
import NoticeList from '@/views/NoticeList.vue'
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
  announcementApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    publish: vi.fn(),
    offline: vi.fn(),
  },
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
    id: 1,
    username: 'admin',
    nickname: '管理员',
    email: '',
    avatar: '',
    is_superuser: true,
    permissions: ['announce:read', 'announce:write'],
    roles: [],
  } as any
  ;(announcementApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
    code: 0,
    data: {
      total: 2,
      items: [
        {
          id: 1,
          title: '系统维护通知',
          content: '周六凌晨升级',
          type: 'notice',
          status: 0,
          is_top: false,
          expire_time: null,
          publish_time: null,
          created_by: 1,
          created_by_name: 'admin',
          created_at: '2026-09-17 10:00:00',
          updated_at: '2026-09-17 10:00:00',
        },
        {
          id: 2,
          title: '新功能上线公告',
          content: '参数配置模块已上线',
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
      ],
    },
  })
  const wrapper = mount(NoticeList, {
    global: { plugins: [pinia, ElementPlus] },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('公告管理页', () => {
  it('渲染：请求列表并展示标题/类型/状态标签', async () => {
    const wrapper = mountList()
    await flushPromises()
    await nextTick()

    expect(announcementApi.list).toHaveBeenCalled()
    const text = wrapper.text()
    expect(text).toContain('系统维护通知')
    expect(text).toContain('新功能上线公告')
    expect(text).toContain('通知')
    expect(text).toContain('公告')
    expect(text).toContain('草稿')
    expect(text).toContain('已发布')
    expect(text).toContain('置顶') // is_top 标签
  })

  it('新增：必填被防线拦截 → 填完 create 调用并刷新', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(announcementApi.create as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })

    await wrapper.findAll('button').find((b) => b.text().includes('新增公告'))!.trigger('click')
    await nextTick()

    const titleInput = wrapper.find('input[placeholder="公告标题"]')
    expect(titleInput.exists()).toBe(true)

    // 不填必填直接提交 → ProForm 防线拦截，不调 API
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()
    expect(announcementApi.create).not.toHaveBeenCalled()

    // 填标题 + 正文后提交
    await titleInput.setValue('新公告')
    const contentArea = wrapper.find('textarea[placeholder="公告正文（纯文本）"]')
    await contentArea.setValue('公告内容')
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()

    expect(announcementApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ title: '新公告', content: '公告内容', type: 'notice', is_top: false }),
    )
    expect(announcementApi.list).toHaveBeenCalledTimes(2)
  })

  it('发布/下线：按状态显示动作按钮并调用对应接口', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(announcementApi.publish as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })
    ;(announcementApi.offline as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })
    const confirmSpy = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as any)

    // 草稿行（id=1）有"发布"按钮；跳过 jsdom 幽灵空行按钮，取第一个数据行
    const publishBtns = wrapper.findAll('button').filter((b) => b.text().includes('发布'))
    expect(publishBtns.length).toBeGreaterThan(0)
    await publishBtns[1].trigger('click')
    await flushPromises()
    expect(announcementApi.publish).toHaveBeenCalledWith(1)

    // 已发布行（id=2）有"下线"按钮
    const offlineBtns = wrapper.findAll('button').filter((b) => b.text().includes('下线'))
    expect(offlineBtns.length).toBeGreaterThan(0)
    await offlineBtns[0].trigger('click')
    await flushPromises()
    expect(announcementApi.offline).toHaveBeenCalledWith(2)

    confirmSpy.mockRestore()
  })

  it('删除：确认弹窗 → remove 调用并刷新', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(announcementApi.remove as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })
    const confirmSpy = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as any)

    const delBtns = wrapper.findAll('button').filter((b) => b.text().includes('删除'))
    // 跳过 jsdom 幽灵空行按钮，取第一个数据行
    await delBtns[1].trigger('click')
    await flushPromises()

    expect(confirmSpy).toHaveBeenCalled()
    expect(announcementApi.remove).toHaveBeenCalledWith(1)
    expect(announcementApi.list).toHaveBeenCalledTimes(2)
    confirmSpy.mockRestore()
  })
})
