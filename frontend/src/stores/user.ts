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
