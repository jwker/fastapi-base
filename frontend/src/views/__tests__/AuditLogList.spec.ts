/* global Blob, URL */
/**
 * 操作审计日志页测试。
 *
 * 覆盖：
 * - 列表渲染：请求 /audit-logs 并渲染数据行、动作标签
 * - 筛选：点击查询时携带筛选参数重新请求
 * - 详情抽屉：点击「详情」展示请求参数
 * - 导出：点击导出触发 export（未填时间范围时 end_time 兜底当前时刻）
 * - 导出后删除：有 audit:delete 权限 → 确认弹窗 → remove + 刷新；无权限 → 仅提示导出成功
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus, { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import AuditLogList from '@/views/AuditLogList.vue'
import { auditLogApi } from '@/api'
import { useUserStore } from '@/stores/user'

vi.mock('@/api', () => ({
  auditLogApi: { list: vi.fn(), export: vi.fn(), remove: vi.fn() },
}))

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
    permissions: ['*'],
    roles: [],
  } as any
  const wrapper = mount(AuditLogList, {
    global: {
      plugins: [pinia, ElementPlus],
      components: { Search },
    },
  })
  return { wrapper }
}

const pageData = {
  code: 0,
  message: 'ok',
  data: {
    total: 2,
    items: [
      {
        id: 1,
        user_id: 1,
        username: 'admin',
        module: '用户管理',
        action: 'create',
        method: 'POST',
        path: '/api/v1/users',
        request_body: '{"username":"alice","password":"******"}',
        response_status: 201,
        ip: '127.0.0.1',
        user_agent: 'pytest',
        created_at: '2026-09-11T10:00:00',
      },
      {
        id: 2,
        user_id: null,
        username: '',
        module: '认证',
        action: 'login',
        method: 'POST',
        path: '/api/v1/auth/login',
        request_body: '{"username":"nobody","password":"******"}',
        response_status: 400,
        ip: '127.0.0.1',
        user_agent: 'pytest',
        created_at: '2026-09-11T10:01:00',
      },
    ],
  },
}

describe('AuditLogList 操作日志', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(auditLogApi.list).mockResolvedValue(pageData as any)
    // jsdom 未实现 URL.createObjectURL，导出下载处 stub
    vi.stubGlobal('URL', { ...URL, createObjectURL: vi.fn(() => 'blob:test'), revokeObjectURL: vi.fn() })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('列表渲染：请求数据并展示操作人与动作标签', async () => {
    const { wrapper } = mountList()
    await flushPromises()

    expect(auditLogApi.list).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('admin')
    expect(wrapper.text()).toContain('用户管理')
    expect(wrapper.text()).toContain('（匿名）')
    expect(wrapper.text()).toContain('201')
  })

  it('筛选查询：输入操作人后点击查询携带筛选参数', async () => {
    const { wrapper } = mountList()
    await flushPromises()

    const input = wrapper.find('input[placeholder="操作人"]')
    await input.setValue('admin')

    const buttons = wrapper.findAll('button')
    const queryBtn = buttons.find((b) => b.text().includes('查询'))
    expect(queryBtn).toBeTruthy()
    await queryBtn!.trigger('click')
    await flushPromises()

    const lastCall = vi.mocked(auditLogApi.list).mock.calls.at(-1)![0]
    expect(lastCall).toMatchObject({ page: 1, page_size: 10, username: 'admin' })
  })

  it('重置：清空筛选条件后重新请求', async () => {
    const { wrapper } = mountList()
    await flushPromises()

    const input = wrapper.find('input[placeholder="操作人"]')
    await input.setValue('admin')
    const buttons = wrapper.findAll('button')
    const resetBtn = buttons.find((b) => b.text().includes('重置'))
    await resetBtn!.trigger('click')
    await flushPromises()

    const lastCall = vi.mocked(auditLogApi.list).mock.calls.at(-1)![0]
    expect(lastCall).not.toHaveProperty('username')
  })

  it('详情抽屉：点击详情展示脱敏后的请求参数', async () => {
    const { wrapper } = mountList()
    await flushPromises()

    // 排除 el-table 的 hidden-columns（列宽测量用隐藏表格）里的克隆按钮：
    // jsdom 不加载 Element Plus CSS，hidden-columns 无 display:none，isVisible() 会误判
    const detailBtn = wrapper
      .findAll('button')
      .find(
        (b) =>
          b.text().includes('详情') && !b.element.closest('.hidden-columns'),
      )
    expect(detailBtn).toBeTruthy()
    await detailBtn!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('请求参数（已脱敏）')
    expect(wrapper.text()).toContain('"password": "******"')
    expect(wrapper.text()).toContain('127.0.0.1')
  })

  it('导出：点击导出触发 export，未填时间范围时 end_time 兜底当前时刻', async () => {
    vi.mocked(auditLogApi.export).mockResolvedValue(new Blob(['a,b']) as any)
    const { wrapper } = mountList()
    await flushPromises()

    const exportBtn = wrapper.findAll('button').find((b) => b.text().includes('导出 CSV'))
    expect(exportBtn).toBeTruthy()
    await exportBtn!.trigger('click')
    await flushPromises()

    expect(auditLogApi.export).toHaveBeenCalledTimes(1)
    const exportParams = vi.mocked(auditLogApi.export).mock.calls[0][0] as any
    // 无时间筛选时兜底当前时刻（删除边界=导出时刻）
    expect(exportParams.end_time).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)
  })

  it('导出后删除：超管（有权限）确认后调用 remove 并刷新列表', async () => {
    vi.mocked(auditLogApi.export).mockResolvedValue(new Blob(['a,b']) as any)
    vi.mocked(auditLogApi.remove).mockResolvedValue({
      code: 0,
      message: '已删除 2 条',
      data: { deleted: 2 },
    } as any)
    const confirmSpy = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as any)
    const { wrapper } = mountList()
    await flushPromises()

    const exportBtn = wrapper.findAll('button').find((b) => b.text().includes('导出 CSV'))
    await exportBtn!.trigger('click')
    await flushPromises()

    // 确认弹窗（含预计条数）
    expect(confirmSpy).toHaveBeenCalledTimes(1)
    expect(String(confirmSpy.mock.calls[0][0])).toContain('共 2 条')

    // remove 使用与导出相同的筛选参数（含 end_time 边界）
    expect(auditLogApi.remove).toHaveBeenCalledTimes(1)
    const removeParams = vi.mocked(auditLogApi.remove).mock.calls[0][0] as any
    const exportParams = vi.mocked(auditLogApi.export).mock.calls[0][0] as any
    expect(removeParams.end_time).toBe(exportParams.end_time)

    // 删除成功后刷新列表（list 再次被调用：初始 1 + 弹窗前统计 1 + 刷新 1 = 3）
    expect(auditLogApi.list).toHaveBeenCalledTimes(3)
  })

  it('导出后删除：无 audit:delete 权限只提示导出成功，不弹删除确认', async () => {
    vi.mocked(auditLogApi.export).mockResolvedValue(new Blob(['a,b']) as any)
    const confirmSpy = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as any)
    const successSpy = vi
      .spyOn(ElMessage, 'success')
      .mockImplementation((() => undefined) as any)

    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useUserStore()
    store.userInfo = {
      id: 2,
      username: 'viewer',
      nickname: '查看者',
      email: '',
      avatar: '',
      is_superuser: false,
      permissions: ['audit:read'],
      roles: [],
    } as any
    const wrapper = mount(AuditLogList, {
      global: { plugins: [pinia, ElementPlus], components: { Search } },
    })
    await flushPromises()

    const exportBtn = wrapper.findAll('button').find((b) => b.text().includes('导出 CSV'))
    await exportBtn!.trigger('click')
    await flushPromises()

    expect(confirmSpy).not.toHaveBeenCalled()
    expect(auditLogApi.remove).not.toHaveBeenCalled()
    expect(successSpy).toHaveBeenCalledWith('导出成功')
  })
})
