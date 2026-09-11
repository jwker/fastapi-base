/**
 * axios 封装（request.ts）拦截器测试。
 *
 * 覆盖：
 * - 请求拦截器自动携带 Access Token
 * - 401 自动刷新 Token 并重放原请求（带新 Token）
 * - 刷新失败 → 登出并跳转登录页
 * - refresh / logout 请求自身 401 → 不触发刷新，直接清登录态
 * - 已重试过的 401 → 不再刷新、不清登录态
 * - 业务码 code != 0 → 统一错误提示
 * - 403 权限不足 → 统一错误提示
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// 可编程的假 axios 实例：捕获拦截器回调，get/post/put/delete 由各用例控制
const { fakeService, refs } = vi.hoisted(() => {
  const refs: { req?: (config: any) => void; success?: (res: any) => any; error?: (err: any) => any } = {}
  // 模拟真实 axios：响应会先被 response 拦截器解包成 body，这里直接返回 body 形态
  const fakeService: any = vi.fn(async (config: any) => {
    if (refs.req) refs.req(config)
    return { code: 0, message: 'ok', data: null }
  })
  fakeService.get = vi.fn()
  fakeService.post = vi.fn()
  fakeService.put = vi.fn()
  fakeService.delete = vi.fn()
  fakeService.interceptors = {
    request: { use: (cb: any) => { refs.req = cb } },
    response: { use: (cb: any, errCb: any) => { refs.success = cb; refs.error = errCb } },
  }
  return { fakeService, refs }
})

vi.mock('axios', () => ({
  default: { create: vi.fn(() => fakeService) },
}))

vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('@/router', () => ({
  default: { push: vi.fn() },
}))

import { ElMessage } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/stores/user'
// 触发模块加载，完成拦截器注册
import '@/utils/request'

const successResp = (data: unknown) => ({ data: { code: 0, message: 'ok', data }, status: 200 })
const makeError = (status: number, url: string, extra: Record<string, unknown> = {}) => ({
  response: { status, data: { message: 'err' } },
  config: { url, method: 'get', headers: {}, ...extra },
})

describe('request 拦截器', () => {
  let store: ReturnType<typeof useUserStore>

  beforeEach(() => {
    vi.clearAllMocks()
    const pinia = createPinia()
    setActivePinia(pinia)
    store = useUserStore()
    store.accessToken = 'old-access'
    store.refreshToken = 'refresh-1'
  })

  it('请求拦截器自动携带 Bearer Token', () => {
    const config: any = { headers: {} }
    refs.req?.(config)
    expect(config.headers.Authorization).toBe('Bearer old-access')
  })

  it('成功响应（code=0）直接解包返回 body', async () => {
    const res: any = successResp({ id: 1 })
    await expect(refs.success?.(res)).resolves.toBe(res.data)
  })

  it('业务错误（code!=0）统一提示并 reject', async () => {
    const res: any = { data: { code: 4001, message: '用户名已存在', data: null }, status: 200 }
    await expect(refs.success?.(res)).rejects.toThrow('用户名已存在')
    expect(ElMessage.error).toHaveBeenCalledWith('用户名已存在')
  })

  it('401 → 自动刷新并重放原请求（带新 Token）', async () => {
    // 刷新请求的响应（已被拦截器解包为 body）
    fakeService.post.mockResolvedValueOnce({
      code: 0,
      message: 'ok',
      data: { access_token: 'new-access', refresh_token: 'new-refresh', token_type: 'bearer' },
    })
    const err = makeError(401, '/api/v1/users')
    const result = await refs.error?.(err)

    // 用旧 refresh token 发起刷新
    expect(fakeService.post).toHaveBeenCalledWith(
      expect.stringContaining('/auth/refresh'),
      { refresh_token: 'refresh-1' },
      undefined,
    )
    // store 更新为新 token
    expect(store.accessToken).toBe('new-access')
    expect(store.refreshToken).toBe('new-refresh')
    // 原请求被重放，且请求拦截器已换上新 token
    expect(fakeService).toHaveBeenCalledTimes(1)
    expect(fakeService.mock.calls[0][0].headers.Authorization).toBe('Bearer new-access')
    expect(result).toEqual({ code: 0, message: 'ok', data: null })
  })

  it('刷新失败 → 登出并跳转登录页', async () => {
    fakeService.post.mockRejectedValueOnce(makeError(401, '/api/v1/auth/refresh'))
    const err = makeError(401, '/api/v1/users')
    await expect(refs.error?.(err)).rejects.toBe(err)

    // 登录态被清空、跳登录页（logout 内部同样走 post，仅被消费一次 rejected）
    expect(store.accessToken).toBe('')
    expect(store.refreshToken).toBe('')
    expect(router.push).toHaveBeenCalledWith('/login')
  })

  it('refresh 请求自身 401 → 不触发刷新、直接清登录态', async () => {
    const err = makeError(401, '/api/v1/auth/refresh')
    await expect(refs.error?.(err)).rejects.toBe(err)

    expect(fakeService.post).not.toHaveBeenCalled()
    expect(store.accessToken).toBe('')
    expect(router.push).toHaveBeenCalledWith('/login')
  })

  it('已重试过的 401 → 不再刷新、不清登录态', async () => {
    const err = makeError(401, '/api/v1/users', { _retried: true })
    await expect(refs.error?.(err)).rejects.toBe(err)

    expect(fakeService.post).not.toHaveBeenCalled()
    expect(store.accessToken).toBe('old-access')
    expect(router.push).not.toHaveBeenCalled()
  })

  it('403 权限不足 → 统一提示', async () => {
    const err = makeError(403, '/api/v1/users')
    await expect(refs.error?.(err)).rejects.toBe(err)
    expect(ElMessage.error).toHaveBeenCalledWith('err')
  })

  it('400 业务错误（如登录失败）→ 提示后端 message', async () => {
    const err = makeError(400, '/api/v1/auth/login', { method: 'post' })
    await expect(refs.error?.(err)).rejects.toBe(err)
    expect(ElMessage.error).toHaveBeenCalledWith('err')
  })

  it('404 资源不存在 → 提示后端 message', async () => {
    const err = makeError(404, '/api/v1/users/999', { method: 'delete' })
    await expect(refs.error?.(err)).rejects.toBe(err)
    expect(ElMessage.error).toHaveBeenCalledWith('err')
  })
})
