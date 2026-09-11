/**
 * 动态路由生成测试：任意层级菜单 → 扁平化路由。
 */
import { describe, it, expect, vi } from 'vitest'
import { generateRoutes } from '@/router/dynamic'
import type { MenuItem } from '@/types'

vi.mock('@/router/component-map', () => ({
  resolveComponent: (name: string) => (name ? { name } : undefined),
}))

const menus: MenuItem[] = [
  {
    id: 1,
    parent_id: null,
    name: '仪表盘',
    path: '/dashboard',
    component: 'Dashboard',
    icon: 'Odometer',
    sort_order: 0,
    is_visible: true,
    permission_code: null,
    children: [],
  },
  {
    id: 2,
    parent_id: null,
    name: '系统管理',
    path: '/system',
    component: 'Layout',
    icon: 'Setting',
    sort_order: 1,
    is_visible: true,
    permission_code: null,
    children: [
      {
        id: 3,
        parent_id: 2,
        name: '用户管理',
        path: '/users',
        component: 'UserList',
        icon: 'User',
        sort_order: 0,
        is_visible: true,
        permission_code: 'user:read',
        children: [],
      },
      // 三级结构：目录(订单管理) > 子目录(订单中心) > 页面(订单列表)
      {
        id: 10,
        parent_id: 2,
        name: '订单管理',
        path: '/orders',
        component: 'Layout',
        icon: 'Tickets',
        sort_order: 1,
        is_visible: true,
        permission_code: null,
        children: [
          {
            id: 11,
            parent_id: 10,
            name: '订单中心',
            path: '/orders/center',
            component: 'Layout',
            icon: 'Folder',
            sort_order: 0,
            is_visible: true,
            permission_code: null,
            children: [
              {
                id: 12,
                parent_id: 11,
                name: '订单列表',
                path: '/orders/list',
                component: 'OrderList',
                icon: 'Document',
                sort_order: 0,
                is_visible: true,
                permission_code: 'order:read',
                children: [],
              },
            ],
          },
        ],
      },
    ],
  },
]

describe('generateRoutes（任意层级）', () => {
  it('单页面顶级菜单（仪表盘）挂 Layout，页面作为子路由', () => {
    const routes = generateRoutes(menus)
    const dashboard = routes.find((r) => r.path === '/dashboard')!
    expect(dashboard.component).toHaveProperty('name', 'Layout')
    expect(dashboard.children).toHaveLength(1)
    expect(dashboard.children![0].component).toHaveProperty('name', 'Dashboard')
  })

  it('分组菜单：Layout 容器 + 扁平化页面路由', () => {
    const routes = generateRoutes(menus)
    const system = routes.find((r) => r.path === '/system')!
    expect(system.component).toHaveProperty('name', 'Layout')
    // 三级目录的叶子页面被扁平收集，直接挂在顶层 Layout 下
    const paths = system.children!.map((c) => c.path)
    expect(paths).toContain('/users')
    expect(paths).toContain('/orders/list')
    // 中间目录（订单管理/订单中心）不生成独立路由
    expect(paths).not.toContain('/orders')
    expect(paths).not.toContain('/orders/center')
    // 三级页面的路由名基于菜单 id，唯一
    const orderList = system.children!.find((c) => c.path === '/orders/list')!
    expect(orderList.name).toBe('menu-12')
  })
})
