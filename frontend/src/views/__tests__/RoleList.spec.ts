/**
 * 角色管理页测试（任务五接入 ProForm 后补齐，此前无测试）。
 *
 * 覆盖：
 * - 列表渲染（ProTable）
 * - 新增：打开弹窗（ProForm 渲染字段）→ 必填未填点确定被防线拦截 → 填完创建成功
 * - 编辑：行内编辑 → 回填旧值 → 编码禁用 → 修改后 update 调用
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import RoleList from '@/views/RoleList.vue'
import { roleApi } from '@/api'
import { useUserStore } from '@/stores/user'

// el-table 依赖 ResizeObserver（jsdom 未实现），缺失时表格不渲染行
if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}

vi.mock('@/api', () => ({
  roleApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn(), assignPermissions: vi.fn(), assignMenus: vi.fn() },
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
    permissions: [],
    roles: [],
  } as any
  ;(roleApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
    code: 0,
    data: {
      total: 1,
      items: [
        {
          id: 1,
          name: '审计员',
          code: 'auditor',
          description: '审计角色',
          status: 1,
          permission_ids: [1],
          menu_ids: [1],
          created_at: '2026-09-14 10:00:00',
        },
      ],
    },
  })
  const wrapper = mount(RoleList, {
    global: { plugins: [pinia, ElementPlus] },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('RoleList 列表', () => {
  it('请求列表并渲染角色数据', async () => {
    const wrapper = mountList()
    await flushPromises()
    await nextTick()
    expect(roleApi.list).toHaveBeenCalled()
    expect(wrapper.text()).toContain('审计员')
    expect(wrapper.text()).toContain('auditor')
  })
})

describe('RoleList 新增', () => {
  it('必填未填点确定被 ProForm 防线拦截，不调 create', async () => {
    const wrapper = mountList()
    await flushPromises()

    // 打开新增弹窗（ProTable 新增按钮）
    await wrapper.findAll('button').find((b) => b.text().includes('新增角色'))!.trigger('click')
    await nextTick()

    // ProForm 渲染字段（placeholder 缺省自动生成）
    expect(wrapper.find('input[placeholder="请输入角色名称"]').exists()).toBe(true)
    expect(wrapper.find('input[placeholder="如 auditor"]').exists()).toBe(true)

    // 必填未填 → 确定被拦截
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()
    expect(roleApi.create).not.toHaveBeenCalled()
  })

  it('填必填后确定 → 调 create 并刷新', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(roleApi.create as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })

    await wrapper.findAll('button').find((b) => b.text().includes('新增角色'))!.trigger('click')
    await nextTick()

    await wrapper.find('input[placeholder="请输入角色名称"]').setValue('运营')
    await wrapper.find('input[placeholder="如 auditor"]').setValue('operator')
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()

    expect(roleApi.create).toHaveBeenCalledWith({
      name: '运营',
      code: 'operator',
      description: '',
    })
    expect(roleApi.list).toHaveBeenCalledTimes(2) // 初始 + 创建后刷新
  })
})

describe('RoleList 编辑', () => {
  it('编辑回填旧值 + 编码禁用 + 修改后 update 调用', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(roleApi.update as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })

    // 点击行内"编辑"（跳过 jsdom 幽灵按钮，取数据行按钮）
    const editBtns = wrapper.findAll('button').filter((b) => b.text().includes('编辑'))
    await editBtns[1].trigger('click')
    await nextTick()

    // 回填：名称输入框显示旧值
    const nameInput = wrapper.find('input[placeholder="请输入角色名称"]').element as HTMLInputElement
    expect(nameInput.value).toBe('审计员')

    // 编码禁用（编辑模式）
    const codeInput = wrapper.find('input[placeholder="如 auditor"]').element as HTMLInputElement
    expect((codeInput as any).disabled || codeInput.hasAttribute('disabled')).toBe(true)

    // 修改名称后确定 → update(id, 新值)
    await wrapper.find('input[placeholder="请输入角色名称"]').setValue('审计员-改')
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()

    expect(roleApi.update).toHaveBeenCalledWith(1, {
      name: '审计员-改',
      code: 'auditor',
      description: '审计角色',
    })
  })
})
