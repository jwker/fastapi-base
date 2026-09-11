import { defineStore } from 'pinia'
import { authApi } from '@/api'
import type { UserInfo } from '@/types'

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
      try {
        const res = await authApi.refresh(this.refreshToken)
        this.accessToken = res.data.access_token
        this.refreshToken = res.data.refresh_token
        return true
      } catch {
        return false
      }
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
      this.$reset()
    },
  },
  persist: {
    key: 'fb-user',
    pick: ['accessToken', 'refreshToken', 'userInfo'],
  },
})
