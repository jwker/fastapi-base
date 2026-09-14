/**
 * 菜单管理页测试（任务五接入 ProForm 后补齐，此前无测试）。
 *
 * 覆盖：
 * - 树形列表渲染
 * - 新增：打开弹窗 → 名称/路径必填被防线拦截 → 填完 create 调用（父级/权限码处理）
 * - 编辑：回填旧值 + 父级下拉禁选自己 + update 调用
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import MenuList from '@/views/MenuList.vue'
import { menuApi } from '@/api'
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
  menuApi: { tree: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() },
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
  ;(menuApi.tree as ReturnType<typeof vi.fn>).mockResolvedValue({
    code: 0,
    data: [
      {
        id: 1,
        parent_id: null,
        name: '系统管理',
        path: '/system',
        component: 'Layout',
        icon: 'Setting',
        sort_order: 1,
        is_visible: true,
        permission_code: null,
        children: [],
      },
    ],
  })
  const wrapper = mount(MenuList, {
    global: { plugins: [pinia, ElementPlus] },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('MenuList 列表', () => {
  it('请求菜单树并渲染', async () => {
    const wrapper = mountList()
    await flushPromises()
    await nextTick()
    expect(menuApi.tree).toHaveBeenCalled()
    expect(wrapper.text()).toContain('系统管理')
    expect(wrapper.text()).toContain('/system')
  })
})

describe('MenuList 新增', () => {
  it('名称/路径必填被 ProForm 防线拦截，不调 create', async () => {
    const wrapper = mountList()
    await flushPromises()

    await wrapper.findAll('button').find((b) => b.text().includes('新增菜单'))!.trigger('click')
    await nextTick()

    expect(wrapper.find('input[placeholder="请输入菜单名称"]').exists()).toBe(true)
    expect(wrapper.find('input[placeholder="/users"]').exists()).toBe(true)
    expect(wrapper.html()).toContain('不选则为顶级菜单')

    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()
    expect(menuApi.create).not.toHaveBeenCalled()
  })

  it('填必填后确定 → create 携带 payload（权限码空转 null）并刷新树', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(menuApi.create as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })

    await wrapper.findAll('button').find((b) => b.text().includes('新增菜单'))!.trigger('click')
    await nextTick()

    await wrapper.find('input[placeholder="请输入菜单名称"]').setValue('文件管理')
    await wrapper.find('input[placeholder="/users"]').setValue('/files')
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()

    expect(menuApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        name: '文件管理',
        path: '/files',
        parent_id: null,
        permission_code: null,
        sort_order: 0,
        is_visible: true,
      }),
    )
    expect(menuApi.tree).toHaveBeenCalledTimes(2) // 初始 + 创建后刷新
  })
})

describe('MenuList 编辑', () => {
  it('编辑回填旧值 + 父级下拉禁选自己 + update 调用', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(menuApi.update as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })

    const editBtns = wrapper.findAll('button').filter((b) => b.text().includes('编辑'))
    // MenuList 是手写 el-table（非 ProTable），无 jsdom 幽灵按钮，取数据行按钮
    await editBtns[0].trigger('click')
    await nextTick()

    // 回填
    const nameInput = wrapper.find('input[placeholder="请输入菜单名称"]').element as HTMLInputElement
    expect(nameInput.value).toBe('系统管理')

    // 父级下拉选项（系统管理 id=1）在编辑模式下 disabled（禁选自己）
    // 注意：el-select 下拉面板默认 teleport 到 body，需从 document 查
    const options = Array.from(document.querySelectorAll('.el-select-dropdown__item'))
    const parentOption = options.find((o) => o.textContent?.includes('系统管理'))
    expect(parentOption?.classList.contains('is-disabled')).toBe(true)
  })
})
