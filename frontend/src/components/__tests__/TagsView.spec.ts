/**
 * TagsView 组件测试：标签渲染、高亮、点击切换、关闭跳转、右键菜单动作。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import TagsView from '@/components/TagsView.vue'
import { useTagsStore } from '@/stores/tags'
import type { MenuItem } from '@/types'

if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}

const pushMock = vi.fn()
let routeMock: Record<string, any> = { path: '/dashboard', fullPath: '/dashboard', query: {}, meta: { title: '仪表盘' } }

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
  useRoute: () => routeMock,
}))

const wrappers: VueWrapper[] = []
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
})

let pinia: ReturnType<typeof createPinia>
beforeEach(() => {
  vi.clearAllMocks()
  pinia = createPinia()
  setActivePinia(pinia)
  routeMock = { path: '/dashboard', fullPath: '/dashboard', query: {}, meta: { title: '仪表盘' } }
})

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
    children: [
      { id: 3, name: '用户管理', component: 'UserList', path: '/users', parent_id: 2, icon: '', sort_order: 1, is_visible: true, permission_code: '', children: [] },
      { id: 4, name: '字典管理', component: 'DictList', path: '/dicts', parent_id: 2, icon: '', sort_order: 2, is_visible: true, permission_code: '', children: [] }
    ],
  },
]

function mountTags() {
  const wrapper = mount(TagsView, { global: { plugins: [pinia, ElementPlus] } })
  wrappers.push(wrapper)
  return wrapper
}

describe('TagsView 渲染与切换', () => {
  it('渲染 affix + 访问过的标签，当前页高亮', async () => {
    const s = useTagsStore()
    s.initAffixTags(menus)
    s.addView({ path: '/users', fullPath: '/users', query: {}, meta: { title: '用户管理', componentName: 'UserList' } } as any)
    const wrapper = mountTags()
    await nextTick()

    const items = wrapper.findAll('.tags-item')
    expect(items).toHaveLength(2)
    expect(items[0].text()).toContain('仪表盘')
    expect(items[1].text()).toContain('用户管理')
    expect(items[0].classes()).toContain('active')
  })

  it('点击标签 → router.push(fullPath)', async () => {
    const s = useTagsStore()
    s.initAffixTags(menus)
    s.addView({ path: '/users', fullPath: '/users', query: {}, meta: { title: '用户管理', componentName: 'UserList' } } as any)
    const wrapper = mountTags()
    await nextTick()

    await wrapper.findAll('.tags-item')[1].trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/users')
  })

  it('affix 标签无关闭按钮；普通标签有关闭按钮', async () => {
    const s = useTagsStore()
    s.initAffixTags(menus)
    s.addView({ path: '/users', fullPath: '/users', query: {}, meta: { title: '用户管理', componentName: 'UserList' } } as any)
    const wrapper = mountTags()
    await nextTick()

    const items = wrapper.findAll('.tags-item')
    expect(items[0].find('.tags-close').exists()).toBe(false)
    expect(items[1].find('.tags-close').exists()).toBe(true)
  })
})

describe('TagsView 关闭', () => {
  it('关闭非当前标签：仅移除，不跳转', async () => {
    const s = useTagsStore()
    s.initAffixTags(menus)
    s.addView({ path: '/users', fullPath: '/users', query: {}, meta: { title: '用户管理', componentName: 'UserList' } } as any)
    const wrapper = mountTags()
    await nextTick()

    await wrapper.findAll('.tags-close')[0].trigger('click')
    await flushPromises()
    expect(s.visitedViews.map((v) => v.path)).toEqual(['/dashboard'])
    expect(pushMock).not.toHaveBeenCalled()
  })

  it('关闭当前标签：移除并跳相邻（右侧优先）', async () => {
    const s = useTagsStore()
    s.initAffixTags(menus)
    s.addView({ path: '/users', fullPath: '/users', query: {}, meta: { title: '用户管理', componentName: 'UserList' } } as any)
    s.addView({ path: '/dicts', fullPath: '/dicts', query: {}, meta: { title: '字典管理', componentName: 'DictList' } } as any)
    routeMock = { path: '/users', fullPath: '/users', query: {}, meta: { title: '用户管理' } }
    const wrapper = mountTags()
    await nextTick()

    // 用户管理是 [1]，关闭它 → 跳右侧字典管理
    await wrapper.findAll('.tags-close')[0].trigger('click')
    await flushPromises()
    expect(s.visitedViews.map((v) => v.path)).toEqual(['/dashboard', '/dicts'])
    expect(pushMock).toHaveBeenCalledWith('/dicts')
  })
})

describe('TagsView 右键菜单', () => {
  function openContextMenu(wrapper: VueWrapper, itemIdx: number) {
    return wrapper.findAll('.tags-item')[itemIdx].trigger('contextmenu')
  }

  it('右键显示菜单；点"关闭其他"只保留目标+affix', async () => {
    const s = useTagsStore()
    s.initAffixTags(menus)
    s.addView({ path: '/users', fullPath: '/users', query: {}, meta: { title: '用户管理', componentName: 'UserList' } } as any)
    s.addView({ path: '/dicts', fullPath: '/dicts', query: {}, meta: { title: '字典管理', componentName: 'DictList' } } as any)
    routeMock = { path: '/dicts', fullPath: '/dicts', query: {}, meta: { title: '字典管理' } }
    const wrapper = mountTags()
    await nextTick()

    // 右键"字典管理"标签（[2]）
    await openContextMenu(wrapper, 2)
    expect(wrapper.find('.context-menu').exists()).toBe(true)

    await wrapper.findAll('.context-item').find((i) => i.text() === '关闭其他')!.trigger('click')
    await flushPromises()
    expect(s.visitedViews.map((v) => v.path)).toEqual(['/dashboard', '/dicts'])
    expect(wrapper.find('.context-menu').exists()).toBe(false)
  })

  it('点"关闭全部"保留 affix；当前页不在列表时跳 affix', async () => {
    const s = useTagsStore()
    s.initAffixTags(menus)
    s.addView({ path: '/users', fullPath: '/users', query: {}, meta: { title: '用户管理', componentName: 'UserList' } } as any)
    routeMock = { path: '/users', fullPath: '/users', query: {}, meta: { title: '用户管理' } }
    const wrapper = mountTags()
    await nextTick()

    await openContextMenu(wrapper, 1)
    await wrapper.findAll('.context-item').find((i) => i.text() === '关闭全部')!.trigger('click')
    await flushPromises()
    expect(s.visitedViews.map((v) => v.path)).toEqual(['/dashboard'])
    expect(pushMock).toHaveBeenCalledWith('/dashboard')
  })

  it('刷新：调用 inject reload', async () => {
    const reloadMock = vi.fn()
    const s = useTagsStore()
    s.initAffixTags(menus)
    const wrapper = mount(TagsView, {
      global: {
        plugins: [pinia, ElementPlus],
        provide: { reload: reloadMock },
      },
    })
    wrappers.push(wrapper)
    await nextTick()

    await openContextMenu(wrapper, 0)
    await wrapper.findAll('.context-item').find((i) => i.text() === '刷新')!.trigger('click')
    await nextTick()
    expect(reloadMock).toHaveBeenCalled()
  })
})
