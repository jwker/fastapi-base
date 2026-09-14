/**
 * 动态路由生成：菜单树 → vue-router 路由。
 *
 * 架构约定（支持任意层级菜单）：
 * - 菜单树只用于渲染侧边栏（任意层级，由 MenuNodes 递归渲染）
 * - 路由「扁平化」：所有页面组件统一挂在顶层 Layout 路由下（绝对路径）
 * - component 为 'Layout' 的节点视为「目录容器」，不生成独立路由，只递归下钻收集页面
 *   —— 避免深层嵌套 Layout 导致布局套布局
 * - 顶层单页面（如仪表盘）包一层 Layout，页面作为 path:'' 子路由
 */
import type { RouteRecordRaw } from 'vue-router'
import type { MenuItem } from '@/types'
import { resolveComponent } from './component-map'

export function generateRoutes(menus: MenuItem[]): RouteRecordRaw[] {
  const routes: RouteRecordRaw[] = []
  const layoutComp = resolveComponent('Layout')
  if (!layoutComp) return routes

  for (const top of menus) {
    if (top.component === 'Layout') {
      // 目录容器：扁平收集其下所有页面（任意层级）
      const children: RouteRecordRaw[] = []
      const collect = (nodes: MenuItem[]) => {
        for (const m of nodes) {
          if (m.component === 'Layout') {
            collect(m.children ?? []) // 子目录：继续下钻
            continue
          }
          const comp = resolveComponent(m.component)
          if (!comp) continue
          children.push({
            path: m.path,
            name: `menu-${m.id}`,
            component: comp,
            meta: {
              title: m.name,
              icon: m.icon,
              menuId: m.id,
              permission: m.permission_code ?? undefined,
              // keep-alive include 匹配组件名（页面 defineOptions name 与此一致）
              componentName: m.component,
            },
          })
        }
      }
      collect(top.children ?? [])
      routes.push({
        path: top.path,
        name: `menu-${top.id}`,
        component: layoutComp,
        meta: { title: top.name, icon: top.icon, menuId: top.id },
        children,
      })
    } else {
      // 顶层单页面：包一层 Layout，页面作为 '' 子路由继承父路径
      const comp = resolveComponent(top.component)
      if (!comp) continue
      routes.push({
        path: top.path,
        name: `menu-${top.id}`,
        component: layoutComp,
        meta: { title: top.name, icon: top.icon, menuId: top.id },
        children: [
          {
            path: '',
            name: `menu-page-${top.id}`,
            component: comp,
            meta: { title: top.name, icon: top.icon, menuId: top.id, componentName: top.component },
          },
        ],
      })
    }
  }
  return routes
}
