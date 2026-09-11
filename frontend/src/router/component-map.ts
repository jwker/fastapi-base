/**
 * 菜单 component 字段 → 实际组件 映射表。
 * 后端菜单数据里的 component 名称在前端通过此表解析。
 */
import type { Component } from 'vue'

const modules = import.meta.glob('@/views/**/*.vue')

const builtin: Record<string, Component> = {
  Layout: () => import('@/layouts/Index.vue'),
}

export function resolveComponent(name: string): Component | undefined {
  if (builtin[name]) return builtin[name]
  // 视图约定：views/{name}.vue
  const match = Object.keys(modules).find((p) => p.endsWith(`/${name}.vue`))
  if (match) return modules[match]
  return undefined
}
