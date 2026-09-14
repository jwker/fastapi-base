/**
 * 用户管理页测试（任务五接入 ProForm 后补齐，此前无测试）。
 *
 * 覆盖：
 * - 列表渲染（ProTable）
 * - 新增：打开弹窗 → ProForm 渲染（含头像插槽/角色多选/密码仅新增必填）→
 *   用户名+密码必填被防线拦截 → 填完 create 调用
 * - 编辑：回填旧值 + 用户名禁用 + 密码非必填（留空不传 password）
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import UserList from '@/views/UserList.vue'
import { dictApi, roleApi, userApi } from '@/api'
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
  roleApi: { list: vi.fn() },
  userApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() },
  dictApi: { byType: vi.fn() },
}))

const wrappers: VueWrapper[] = []
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
})

beforeEach(() => {
  vi.clearAllMocks()
  ;(dictApi.byType as ReturnType<typeof vi.fn>).mockResolvedValue({
    code: 0,
    data: [
      { label: '启用', value: '1' },
      { label: '禁用', value: '0' },
    ],
  })
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
  ;(userApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
    code: 0,
    data: {
      total: 1,
      items: [
        {
          id: 2,
          username: 'alice',
          nickname: '爱丽丝',
          email: 'alice@test.com',
          phone: '13800000000',
          avatar: '',
          status: 1,
          is_superuser: false,
          role_ids: [1],
          created_at: '2026-09-14 10:00:00',
        },
      ],
    },
  })
  ;(roleApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
    code: 0,
    data: {
      total: 1,
      items: [{ id: 1, name: '管理员', code: 'admin', description: '', status: 1, permission_ids: [], menu_ids: [] }],
    },
  })
  const wrapper = mount(UserList, {
    global: { plugins: [pinia, ElementPlus] },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('UserList 列表', () => {
  it('请求用户与角色列表并渲染', async () => {
    const wrapper = mountList()
    await flushPromises()
    await nextTick()
    expect(userApi.list).toHaveBeenCalled()
    expect(roleApi.list).toHaveBeenCalled()
    expect(wrapper.text()).toContain('alice')
    expect(wrapper.text()).toContain('爱丽丝')
  })
})

describe('UserList 新增', () => {
  it('用户名/密码必填被 ProForm 防线拦截，不调 create', async () => {
    const wrapper = mountList()
    await flushPromises()

    await wrapper.findAll('button').find((b) => b.text().includes('新增用户'))!.trigger('click')
    await nextTick()

    // ProForm 渲染：用户名 + 密码（create 模式必填）+ 头像插槽
    expect(wrapper.find('input[placeholder="登录用户名"]').exists()).toBe(true)
    expect(wrapper.find('input[placeholder="至少 6 位"]').exists()).toBe(true)
    expect(wrapper.find('.el-upload').exists()).toBe(true)

    // 必填未填 → 确定被拦截
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()
    expect(userApi.create).not.toHaveBeenCalled()
  })

  it('填必填后确定 → create 携带 payload 并刷新', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(userApi.create as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })

    await wrapper.findAll('button').find((b) => b.text().includes('新增用户'))!.trigger('click')
    await nextTick()

    await wrapper.find('input[placeholder="登录用户名"]').setValue('bob')
    await wrapper.find('input[placeholder="至少 6 位"]').setValue('bob123456')
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()

    expect(userApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        username: 'bob',
        password: 'bob123456',
        status: 1,
        role_ids: [],
        avatar: '',
      }),
    )
    expect(userApi.list).toHaveBeenCalledTimes(2)
  })
})

describe('UserList 编辑', () => {
  it('编辑回填旧值 + 用户名禁用 + 密码留空不传 password', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(userApi.update as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })

    const editBtns = wrapper.findAll('button').filter((b) => b.text().includes('编辑'))
    await editBtns[1].trigger('click')
    await nextTick()

    // 回填 + 用户名禁用
    const usernameInput = wrapper.find('input[placeholder="登录用户名"]').element as HTMLInputElement
    expect(usernameInput.value).toBe('alice')
    expect((usernameInput as any).disabled || usernameInput.hasAttribute('disabled')).toBe(true)

    // 编辑模式：密码 placeholder 变为"留空则不修改"（非必填）
    const pwdInput = wrapper.find('input[placeholder="留空则不修改"]').element as HTMLInputElement
    expect(pwdInput).toBeTruthy()

    // 只改昵称 → update 不传 password
    const nicknameInput = wrapper.findAll('input').find(
      (i) => (i.element as HTMLInputElement).placeholder === '请输入昵称',
    )!
    await nicknameInput.setValue('爱丽丝-改')
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()

    expect(userApi.update).toHaveBeenCalledWith(
      2,
      expect.objectContaining({
        nickname: '爱丽丝-改',
        email: 'alice@test.com',
        role_ids: [1],
      }),
    )
    expect(userApi.update).toHaveBeenCalledWith(
      2,
      expect.not.objectContaining({ password: expect.anything() }),
    )
  })
})
