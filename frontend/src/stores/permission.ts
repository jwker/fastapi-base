import { defineStore } from 'pinia'
import { menuApi } from '@/api'
import type { MenuItem } from '@/types'

interface PermissionState {
  menus: MenuItem[]
  routesLoaded: boolean
}

/**
 * 动态路由状态：不做持久化。
 * 动态路由注册在内存 router 实例上，刷新即丢失；
 * 若持久化 routesLoaded=true，刷新后守卫会跳过重新注册 → 页面空白。
 * 每次刷新都应重新拉取菜单（保证权限最新）并重新注册路由。
 */
export const usePermissionStore = defineStore('permission', {
  state: (): PermissionState => ({
    menus: [],
    routesLoaded: false,
  }),
  actions: {
    /** 拉取当前用户可访问菜单树 */
    async fetchMenus() {
      const res = await menuApi.my()
      this.menus = res.data
      this.routesLoaded = true
    },
    reset() {
      this.menus = []
      this.routesLoaded = false
    },
  },
})
