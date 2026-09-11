import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { usePermissionStore } from '@/stores/permission'
import { generateRoutes } from './dynamic'

// 本地固定路由：无需权限
const constantRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('@/views/error/403.vue'),
    meta: { title: '无权限' },
  },
  {
    path: '/404',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '未找到' },
  },
  {
    // 个人中心：所有登录用户可用，不走后端菜单权限
    path: '/profile',
    name: 'Profile',
    component: () => import('@/layouts/Index.vue'),
    meta: { title: '个人中心' },
    children: [
      {
        path: '',
        name: 'ProfilePage',
        component: () => import('@/views/Profile.vue'),
        meta: { title: '个人中心' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes: constantRoutes,
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()
  const permissionStore = usePermissionStore()
  document.title = to.meta.title
    ? `${String(to.meta.title)} - ${import.meta.env.VITE_APP_TITLE}`
    : import.meta.env.VITE_APP_TITLE

  // 登录页直接放行
  if (to.path === '/login') {
    if (userStore.isLoggedIn) return '/'
    return true
  }

  // 未登录 → 登录页
  if (!userStore.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // 已登录但动态路由未加载 → 加载菜单并注册路由
  if (!permissionStore.routesLoaded) {
    try {
      await permissionStore.fetchMenus()
      // 清理可能残留的动态路由（如登出后再登录，旧路由仍在内存 router 上）
      router.getRoutes().forEach((r) => {
        if (r.name && String(r.name).startsWith('menu-')) {
          router.removeRoute(r.name)
        }
      })
      const dynamicRoutes = generateRoutes(permissionStore.menus)
      dynamicRoutes.forEach((r) => router.addRoute(r))
      // 根路径 → 第一个菜单（精确匹配优先于 catch-all 通配）；无菜单则 403
      if (!router.hasRoute('RootRedirect')) {
        router.addRoute({
          path: '/',
          name: 'RootRedirect',
          redirect: permissionStore.menus[0]?.path || '/403',
        })
      }
      // 兜底 404 放在最后（name 用 CatchAll，避免与 /404 路由的 NotFound 混淆）
      if (!router.hasRoute('CatchAll')) {
        router.addRoute({ path: '/:pathMatch(.*)*', name: 'CatchAll', redirect: '/404' })
      }
      return { ...to, replace: true } // 重新进入以匹配新路由
    } catch {
      userStore.logout()
      return { path: '/login' }
    }
  }

  return true
})

export default router
