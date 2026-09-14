/**
 * 多标签页 store：visitedViews（标签列表）+ cachedViews（keep-alive 缓存名单）。
 *
 * 约定：
 * - affix：固定标签（首个菜单/仪表盘），不可关闭、不参与"关闭全部"
 * - componentName：页面组件名（路由 meta 注入，与 defineOptions name 一致），
 *   keep-alive include 靠它匹配——关闭标签时从 cachedViews 同步移除（解除缓存）
 * - 不持久化：刷新后仅当前页 + affix 由 layout 重建（RuoYi 同款）
 */
import { defineStore } from 'pinia'
import type { RouteLocationNormalizedLoaded } from 'vue-router'
import type { MenuItem } from '@/types'

export interface TagView {
  path: string
  fullPath: string
  title: string
  affix: boolean
  keepAlive: boolean
  componentName?: string
  query?: Record<string, unknown>
}

function toView(route: RouteLocationNormalizedLoaded): TagView {
  const meta = route.meta as Record<string, unknown>
  return {
    path: route.path,
    fullPath: route.fullPath,
    title: (meta.title as string) || '未命名',
    affix: meta.affix === true,
    keepAlive: meta.noCache !== true,
    componentName: (meta.componentName as string) || undefined,
    query: { ...route.query },
  }
}

export const useTagsStore = defineStore('tags', {
  state: () => ({
    visitedViews: [] as TagView[],
    /** keep-alive include 名单（组件 name），从 visitedViews 派生 */
    cachedViews: [] as string[],
  }),

  getters: {
    affixTags: (s) => s.visitedViews.filter((v) => v.affix),
  },

  actions: {
    /** 从菜单树找第一个页面（顶层单页面或目录下第一个页面），作为固定标签 */
    initAffixTags(menus: MenuItem[]) {
      const find = (nodes: MenuItem[]): MenuItem | undefined => {
        for (const m of nodes) {
          if (m.component !== 'Layout') return m
          const sub = find(m.children ?? [])
          if (sub) return sub
        }
        return undefined
      }
      const first = find(menus)
      if (!first) return
      const componentName =
        first.component && first.component !== 'Layout' ? first.component : undefined
      const existing = this.visitedViews.find((v) => v.path === first.path)
      if (existing) {
        // 已有同 path（如挂载时先 addView 过）→ 升级为 affix 并置顶，避免重复标签
        if (!existing.affix) {
          existing.affix = true
          existing.keepAlive = true
          if (componentName) existing.componentName = componentName
          this.visitedViews = [existing, ...this.visitedViews.filter((v) => v !== existing)]
          this.syncCache()
        }
        return
      }
      this.visitedViews.unshift({
        path: first.path,
        fullPath: first.path,
        title: first.name,
        affix: true,
        keepAlive: true,
        componentName,
      })
    },

    /** 路由变化时添加标签；同 path 复用并刷新 query/fullPath */
    addView(route: RouteLocationNormalizedLoaded) {
      const view = toView(route)
      const existing = this.visitedViews.find((v) => v.path === view.path)
      if (existing) {
        existing.fullPath = view.fullPath
        existing.query = view.query
        return
      }
      this.visitedViews.push(view)
      this.syncCache()
    },

    /** 关闭单个标签（affix 不可关），同步解除缓存 */
    delView(view: TagView) {
      this.visitedViews = this.visitedViews.filter((v) => !(v.path === view.path && !v.affix))
      this.syncCache()
    },

    /** 关闭其他（保留 affix 与目标） */
    delOthersViews(view: TagView) {
      this.visitedViews = this.visitedViews.filter((v) => v.affix || v.path === view.path)
      this.syncCache()
    },

    /** 关闭全部（保留 affix） */
    delAllViews() {
      this.visitedViews = this.visitedViews.filter((v) => v.affix)
      this.syncCache()
    },

    /** 登出/权限重置时清空 */
    resetTags() {
      this.visitedViews = []
      this.cachedViews = []
    },

    /** 从 visitedViews 重算缓存名单（关闭标签自动解除缓存） */
    syncCache() {
      const names = new Set<string>()
      this.visitedViews.forEach((v) => {
        if (v.keepAlive && v.componentName) names.add(v.componentName)
      })
      this.cachedViews = [...names]
    },
  },
})
