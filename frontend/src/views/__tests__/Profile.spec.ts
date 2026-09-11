/**
 * Profile 个人中心页面测试。
 *
 * 覆盖：
 * - 资料表单渲染初始值，保存调用 updateProfile 并同步 userInfo
 * - 改密码表单：两次密码不一致时被提交前防线拦截（不调用 API、提示错误）
 * - 改密码成功：调用 changePassword、清登录态并跳转登录页
 *
 * 说明：element-plus 表单校验在 vitest/jsdom 下存在已知问题（多表单时 rules
 * 校验空转），因此提交逻辑内置了不依赖 el-form 的手动防线；本测试基于该防线断言。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus, { ElMessage } from 'element-plus'
import Profile from '@/views/Profile.vue'
import { authApi } from '@/api'
import { useUserStore } from '@/stores/user'

const pushMock = vi.hoisted(() => vi.fn())

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
  useRoute: () => ({ query: {} }),
}))

vi.mock('@/api', () => ({
  authApi: {
    changePassword: vi.fn(),
    updateProfile: vi.fn(),
  },
}))

const baseUser = {
  id: 1,
  username: 'admin',
  nickname: '管理员',
  email: 'admin@example.com',
  phone: '13800000000',
  avatar: '',
  is_superuser: true,
  permissions: ['*'],
  roles: ['super_admin'],
}

function mountProfile() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useUserStore()
  store.userInfo = { ...baseUser } as any
  store.accessToken = 'tok'
  store.refreshToken = 'refresh'
  const wrapper = mount(Profile, { global: { plugins: [pinia, ElementPlus] } })
  return { wrapper, store }
}

describe('Profile 个人中心', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('资料表单渲染当前用户信息，保存调用 updateProfile 并同步', async () => {
    vi.mocked(authApi.updateProfile).mockResolvedValue({
      code: 0,
      message: 'ok',
      data: { ...baseUser, nickname: '新昵称' },
    } as any)
    const { wrapper, store } = mountProfile()
    await flushPromises()

    const inputs = wrapper.findAll('input')
    expect(inputs.some((i) => (i.element as HTMLInputElement).value === '管理员')).toBe(true)

    // 改昵称并保存
    const nicknameInput = inputs.find((i) => (i.element as HTMLInputElement).value === '管理员')!
    await nicknameInput.setValue('新昵称')
    const saveBtn = wrapper.findAll('button').find((b) => b.text().includes('保存资料'))!
    await saveBtn.trigger('click')
    await flushPromises()

    expect(authApi.updateProfile).toHaveBeenCalledTimes(1)
    expect(store.userInfo?.nickname).toBe('新昵称')
  })

  it('两次新密码不一致时被拦截，不调用 API 并提示错误', async () => {
    const errorSpy = vi.spyOn(ElMessage, 'error')
    const { wrapper } = mountProfile()
    await flushPromises()

    const inputs = wrapper.findAll('input')
    // 原密码/新密码/确认密码（资料区 5 个输入在前，密码区是后 3 个）
    const pwdInputs = inputs.slice(-3)
    await pwdInputs[0].setValue('admin123')
    await pwdInputs[1].setValue('newpass123')
    await pwdInputs[2].setValue('different123')

    const changeBtn = wrapper.findAll('button').find((b) => b.text().includes('修改密码'))!
    await changeBtn.trigger('click')
    await flushPromises()

    expect(authApi.changePassword).not.toHaveBeenCalled()
    expect(errorSpy).toHaveBeenCalledWith('两次输入的密码不一致')
  })

  it('改密码成功：调用 changePassword、清登录态并跳转登录页', async () => {
    vi.mocked(authApi.changePassword).mockResolvedValue({
      code: 0,
      message: 'ok',
      data: null,
    } as any)
    const { wrapper, store } = mountProfile()
    await flushPromises()

    const inputs = wrapper.findAll('input')
    const pwdInputs = inputs.slice(-3)
    await pwdInputs[0].setValue('admin123')
    await pwdInputs[1].setValue('newpass123')
    await pwdInputs[2].setValue('newpass123')

    const changeBtn = wrapper.findAll('button').find((b) => b.text().includes('修改密码'))!
    await changeBtn.trigger('click')
    await flushPromises()

    expect(authApi.changePassword).toHaveBeenCalledWith('admin123', 'newpass123')
    expect(store.accessToken).toBe('') // 登录态已清空
    expect(pushMock).toHaveBeenCalledWith('/login')
  })
})
