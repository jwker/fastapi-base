/**
 * user store 测试：refreshTokens 并发 single-flight（同一时刻只发一次刷新）。
 *
 * 背景：并发 401 若各自调 refreshTokens，会携带同一旧 refresh token 并发请求；
 * 后端轮换后仅一个有效，其余 401 → 触发登出（"15 分钟掉线"根因）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '@/stores/user'

const refreshMock = vi.fn()
vi.mock('@/api', () => ({
  authApi: {
    login: vi.fn(),
    refresh: (...args: unknown[]) => refreshMock(...args),
    logout: vi.fn(),
    me: vi.fn(),
    updateProfile: vi.fn(),
    changePassword: vi.fn(),
  },
}))

describe('user store refreshTokens single-flight', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('并发调用只发一次 refresh，结果共享', async () => {
    const s = useUserStore()
    s.refreshToken = 'old-refresh'
    refreshMock.mockResolvedValue({
      data: { access_token: 'new-access', refresh_token: 'new-refresh' },
    })

    const [r1, r2, r3] = await Promise.all([
      s.refreshTokens(),
      s.refreshTokens(),
      s.refreshTokens(),
    ])

    expect(refreshMock).toHaveBeenCalledTimes(1) // 只发一次
    expect(refreshMock).toHaveBeenCalledWith('old-refresh')
    expect([r1, r2, r3]).toEqual([true, true, true])
    expect(s.accessToken).toBe('new-access')
    expect(s.refreshToken).toBe('new-refresh')
  })

  it('刷新失败：并发调用共享失败结果且不发第二次', async () => {
    const s = useUserStore()
    s.refreshToken = 'old-refresh'
    refreshMock.mockRejectedValue(new Error('401'))

    const [r1, r2] = await Promise.all([s.refreshTokens(), s.refreshTokens()])

    expect(refreshMock).toHaveBeenCalledTimes(1)
    expect([r1, r2]).toEqual([false, false])
  })

  it('刷新完成后可再次刷新（锁释放）', async () => {
    const s = useUserStore()
    s.refreshToken = 'old-refresh'
    refreshMock.mockResolvedValueOnce({
      data: { access_token: 'a1', refresh_token: 'r1' },
    })
    refreshMock.mockResolvedValueOnce({
      data: { access_token: 'a2', refresh_token: 'r2' },
    })

    expect(await s.refreshTokens()).toBe(true)
    expect(await s.refreshTokens()).toBe(true)
    expect(refreshMock).toHaveBeenCalledTimes(2)
    expect(s.accessToken).toBe('a2')
    expect(s.refreshToken).toBe('r2')
  })
})
