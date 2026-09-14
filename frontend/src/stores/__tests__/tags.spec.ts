/**
 * tags store 测试：标签增删、affix 固定、缓存名单同步、关闭其他/全部、登出清空。
 */
import { describe, expect, it, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useTagsStore } from '@/stores/tags'
import type { RouteLocationNormalizedLoaded } from 'vue-router'
import type { MenuItem } from '@/types'

function mkRoute(overrides: Record<string, unknown> = {}): RouteLocationNormalizedLoaded {
  return {
    path: '/dashboard',
    fullPath: '/dashboard',
    query: {},
    meta: { title: '仪表盘' },
    ...overrides,
  } as unknown as RouteLocationNormalizedLoaded
}

const menus: MenuItem[] = [
  { id: 1, name: '仪表盘', component: 'Dashboard', path: '/dashboard', parent_id: 0, icon: '', sort_order: 1, is_visible: true, permission_code: '', children: [] },
  {
    id: 2,
    name: '系统管理',
    component: 'Layout',
    path: '/system',
    parent_id: 0,
    icon: '',
    sort_order: 2,
    is_visible: true,
    permission_code: '',
    children: [{ id: 3, name: '用户管理', component: 'UserList', path: '/users', parent_id: 2, icon: '', sort_order: 1, is_visible: true, permission_code: '', children: [] }],
  },
]

describe('tags store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('addView 添加标签；同 path 复用不重复', () => {
    const s = useTagsStore()
    s.addView(mkRoute())
    s.addView(mkRoute())
    expect(s.visitedViews).toHaveLength(1)

    s.addView(mkRoute({ path: '/users', fullPath: '/users?page=2', meta: { title: '用户管理', componentName: 'UserList' } }))
    expect(s.visitedViews).toHaveLength(2)
    expect(s.visitedViews[1].title).toBe('用户管理')
  })

  it('addView 同步 cachedViews（keep-alive include 名单）', () => {
    const s = useTagsStore()
    s.addView(mkRoute({ meta: { title: '用户管理', componentName: 'UserList' } }))
    expect(s.cachedViews).toEqual(['UserList'])
  })

  it('initAffixTags 固定首个菜单（目录下取第一个页面）', () => {
    const s = useTagsStore()
    s.initAffixTags(menus)
    expect(s.affixTags).toHaveLength(1)
    expect(s.affixTags[0]).toMatchObject({ path: '/dashboard', affix: true })

    // 幂等
    s.initAffixTags(menus)
    expect(s.affixTags).toHaveLength(1)
  })

  it('先 addView 后 initAffixTags：同 path 升级为 affix，不产生重复标签', () => {
    const s = useTagsStore()
    s.addView(mkRoute())
    expect(s.visitedViews).toHaveLength(1)
    expect(s.visitedViews[0].affix).toBe(false)

    s.initAffixTags(menus)
    expect(s.visitedViews).toHaveLength(1)
    expect(s.visitedViews[0]).toMatchObject({ path: '/dashboard', affix: true })
    expect(s.visitedViews[0].componentName).toBe('Dashboard')
  })

  it('delView 关闭标签并同步解除缓存；affix 不可关', () => {
    const s = useTagsStore()
    s.initAffixTags(menus)
    s.addView(mkRoute({ path: '/users', fullPath: '/users', meta: { title: '用户管理', componentName: 'UserList' } }))
    expect(s.visitedViews).toHaveLength(2)

    s.delView({ path: '/users', fullPath: '/users', title: '用户管理', affix: false, keepAlive: true, componentName: 'UserList' })
    expect(s.visitedViews).toHaveLength(1)
    // affix（Dashboard）仍在缓存名单，被关的 UserList 已解除
    expect(s.cachedViews).toEqual(['Dashboard'])

    // affix 关不掉
    s.delView(s.affixTags[0])
    expect(s.visitedViews).toHaveLength(1)
  })

  it('delOthersViews 保留 affix 与目标', () => {
    const s = useTagsStore()
    s.initAffixTags(menus)
    s.addView(mkRoute({ path: '/users', fullPath: '/users', meta: { title: '用户管理', componentName: 'UserList' } }))
    s.addView(mkRoute({ path: '/dicts', fullPath: '/dicts', meta: { title: '字典管理', componentName: 'DictList' } }))

    s.delOthersViews({ path: '/dicts', fullPath: '/dicts', title: '字典管理', affix: false, keepAlive: true, componentName: 'DictList' })
    expect(s.visitedViews.map((v) => v.path)).toEqual(['/dashboard', '/dicts'])
    expect(s.cachedViews).toEqual(['Dashboard', 'DictList'])
  })

  it('delAllViews 保留 affix', () => {
    const s = useTagsStore()
    s.initAffixTags(menus)
    s.addView(mkRoute({ path: '/users', fullPath: '/users', meta: { title: '用户管理', componentName: 'UserList' } }))
    s.delAllViews()
    expect(s.visitedViews.map((v) => v.path)).toEqual(['/dashboard'])
  })

  it('resetTags 清空全部（登出）', () => {
    const s = useTagsStore()
    s.initAffixTags(menus)
    s.addView(mkRoute({ path: '/users', fullPath: '/users', meta: { title: '用户管理', componentName: 'UserList' } }))
    s.resetTags()
    expect(s.visitedViews).toEqual([])
    expect(s.cachedViews).toEqual([])
  })

  it('noCache 页面不进入缓存名单', () => {
    const s = useTagsStore()
    s.addView(mkRoute({ meta: { title: '个人中心', componentName: 'Profile', noCache: true } }))
    expect(s.visitedViews).toHaveLength(1)
    expect(s.cachedViews).toEqual([])
  })
})
