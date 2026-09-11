/**
 * ProTable 通用表格组件测试。
 *
 * 覆盖：
 * - 挂载后自动拉取数据并渲染表格行
 * - 搜索后以 page=1 + 关键字重新请求
 * - 操作按钮按权限过滤（无权限隐藏 / 超管始终可见）
 * - 带 confirm 的操作先弹确认框，确认后执行并刷新
 * - 新增按钮按权限控制显示，点击触发 onCreate
 * - 分页组件渲染
 */
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import ElementPlus, { ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import ProTable, { type ActionConfig, type ColumnConfig } from '@/components/ProTable.vue'
import { useUserStore } from '@/stores/user'

// jsdom 缺失的浏览器 API（真实渲染 Element Plus 组件所需）
beforeAll(() => {
  if (!globalThis.ResizeObserver) {
    globalThis.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    } as any
  }
  if (!window.matchMedia) {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  }
})

afterEach(() => {
  vi.restoreAllMocks()
})

const columns: ColumnConfig[] = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'username', label: '用户名', minWidth: 120 },
  { prop: 'status', label: '状态', width: 90, formatter: (_r, v) => (v === 1 ? '启用' : '禁用') },
]

const rows = {
  total: 2,
  items: [
    { id: 1, username: 'alice', status: 1 },
    { id: 2, username: 'bob', status: 1 },
  ],
}

function mountProTable(
  props: Record<string, any> = {},
  permissions: string[] = [],
  isSuperuser = false,
) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useUserStore()
  store.userInfo = {
    id: 1,
    username: 'tester',
    nickname: '',
    email: '',
    avatar: '',
    is_superuser: isSuperuser,
    permissions,
    roles: [],
  } as any
  const wrapper = mount(ProTable as any, {
    props: props as any,
    global: {
      plugins: [pinia, ElementPlus],
      components: { Search, Plus },
    },
  })
  return { wrapper, store }
}

describe('ProTable', () => {
  it('挂载后自动拉取数据并渲染表格行', async () => {
    const fetchApi = vi.fn().mockResolvedValue({ data: rows })
    const { wrapper } = mountProTable({ columns, fetchApi })
    await flushPromises()
    await nextTick()

    expect(fetchApi).toHaveBeenCalledWith({ page: 1, page_size: 10, keyword: undefined })
    expect(wrapper.findAll('.el-table__row')).toHaveLength(2)
    expect(wrapper.text()).toContain('alice')
    expect(wrapper.text()).toContain('bob')
  })

  it('搜索后以 page=1 + 关键字重新请求', async () => {
    const fetchApi = vi.fn().mockResolvedValue({ data: rows })
    const { wrapper } = mountProTable({ columns, fetchApi })
    await flushPromises()

    const input = wrapper.find('.el-input__inner')
    await input.setValue('alice')
    await input.trigger('keyup.enter')
    await flushPromises()

    expect(fetchApi).toHaveBeenCalledTimes(2)
    expect(fetchApi).toHaveBeenLastCalledWith({ page: 1, page_size: 10, keyword: 'alice' })
  })

  it('无权限时隐藏操作按钮，超管始终可见', async () => {
    const actions: ActionConfig[] = [
      { label: '编辑', permission: 'user:update', onClick: vi.fn() },
      { label: '删除', type: 'danger', permission: 'user:delete', onClick: vi.fn() },
    ]
    const fetchApi = vi.fn().mockResolvedValue({ data: rows })

    // 只有 user:read → 编辑/删除都隐藏
    const { wrapper: w1 } = mountProTable({ columns, fetchApi, actions }, ['user:read'])
    await flushPromises()
    await nextTick()
    expect(w1.text()).not.toContain('编辑')
    expect(w1.text()).not.toContain('删除')

    // 超管 → 全部可见
    const { wrapper: w2 } = mountProTable({ columns, fetchApi, actions }, [], true)
    await flushPromises()
    await nextTick()
    expect(w2.text()).toContain('编辑')
    expect(w2.text()).toContain('删除')
  })

  it('有权限时按钮可点击，confirm 先弹确认框', async () => {
    const onClick = vi.fn()
    const actions: ActionConfig[] = [
      { label: '删除', type: 'danger', permission: 'user:delete', confirm: '确定删除？', onClick },
    ]
    const fetchApi = vi.fn().mockResolvedValue({ data: rows })
    const confirmSpy = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as any)

    const { wrapper } = mountProTable({ columns, fetchApi, actions }, ['user:delete'])
    await flushPromises()
    await nextTick()

    const delBtn = wrapper.findAll('button').find((b) => b.text() === '删除')!
    expect(delBtn).toBeTruthy()
    await delBtn.trigger('click')
    await flushPromises()

    expect(confirmSpy).toHaveBeenCalledWith('确定删除？', '提示', expect.anything())
    expect(onClick).toHaveBeenCalledTimes(1)
    // 操作成功后刷新列表（初始加载 + 刷新 = 2 次）
    expect(fetchApi).toHaveBeenCalledTimes(2)
  })

  it('新增按钮按权限控制显示，点击触发 onCreate', async () => {
    const onCreate = vi.fn()
    const fetchApi = vi.fn().mockResolvedValue({ data: rows })

    // 无权限 → 不显示
    const { wrapper: w1 } = mountProTable(
      { columns, fetchApi, createLabel: '新增用户', createPermission: 'user:create', onCreate },
      ['user:read'],
    )
    await flushPromises()
    expect(w1.text()).not.toContain('新增用户')

    // 有权限 → 显示且可点击
    const { wrapper: w2 } = mountProTable(
      { columns, fetchApi, createLabel: '新增用户', createPermission: 'user:create', onCreate },
      ['user:create'],
    )
    await flushPromises()
    await nextTick()
    const addBtn = w2.findAll('button').find((b) => b.text() === '新增用户')!
    expect(addBtn).toBeTruthy()
    await addBtn.trigger('click')
    expect(onCreate).toHaveBeenCalledTimes(1)
  })

  it('渲染分页组件', async () => {
    const fetchApi = vi.fn().mockResolvedValue({ data: rows })
    const { wrapper } = mountProTable({ columns, fetchApi })
    await flushPromises()
    expect(wrapper.find('.el-pagination').exists()).toBe(true)
  })
})
