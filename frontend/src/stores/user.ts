import { defineStore } from 'pinia'
import { authApi } from '@/api'
import { useTagsStore } from '@/stores/tags'
import type { UserInfo } from '@/types'

// 模块级刷新锁：并发 401 共享同一次刷新（见 refreshTokens）
let refreshPromise: Promise<boolean> | null = null

interface UserState {
  accessToken: string
  refreshToken: string
  userInfo: UserInfo | null
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    accessToken: '',
    refreshToken: '',
    userInfo: null,
  }),
  getters: {
    isLoggedIn: (s) => !!s.accessToken,
    permissions: (s): string[] => s.userInfo?.permissions ?? [],
    isSuperuser: (s) => !!s.userInfo?.is_superuser,
  },
  actions: {
    async login(username: string, password: string) {
      const res = await authApi.login(username, password)
      const data = res.data
      this.accessToken = data.tokens.access_token
      this.refreshToken = data.tokens.refresh_token
      this.userInfo = data.user
    },
    async refreshTokens(): Promise<boolean> {
      // single-flight：并发 401 只发一次刷新，所有人共享同一结果。
      // 否则多个 refresh 携带同一旧 token 并发，后端轮换后只有一个有效，
      // 其余 401 → 触发登出（15 分钟掉线的根因）。
      if (!refreshPromise) {
        refreshPromise = (async () => {
          try {
            const res = await authApi.refresh(this.refreshToken)
            this.accessToken = res.data.access_token
            this.refreshToken = res.data.refresh_token
            return true
          } catch {
            return false
          } finally {
            refreshPromise = null
          }
        })()
      }
      return refreshPromise
    },
    async fetchUserInfo() {
      const res = await authApi.me()
      this.userInfo = res.data
    },
    /** 更新个人资料（昵称/邮箱/手机/头像），成功后同步本地 userInfo */
    async updateProfile(data: Record<string, unknown>) {
      const res = await authApi.updateProfile(data)
      this.userInfo = res.data
    },
    /** 修改密码：后端已吊销全部凭证，成功后清空本地登录态（页面负责跳转登录页） */
    async changePassword(old_password: string, new_password: string) {
      await authApi.changePassword(old_password, new_password)
      this.$reset()
    },
    async logout() {
      try {
        await authApi.logout(this.refreshToken)
      } catch {
        /* 忽略登出接口异常 */
      }
      // 多标签页随登出清空（避免换账号看到旧标签）
      useTagsStore().resetTags()
      this.$reset()
    },
  },
  persist: {
    key: 'fb-user',
    pick: ['accessToken', 'refreshToken', 'userInfo'],
  },
})
