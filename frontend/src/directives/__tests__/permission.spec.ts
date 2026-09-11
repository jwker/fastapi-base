/**
 * v-permission 指令单元测试。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent } from 'vue'

// mock 掉 Element Plus 以隔离测试
vi.mock('element-plus', () => ({}))

import permission from '@/directives/permission'
import { useUserStore } from '@/stores/user'

const TestButton = defineComponent({
  template: '<div><button v-permission="\'user:delete\'">删除</button></div>',
})

function mountWithPermission(permissions: string[], isSuperuser = false) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useUserStore()
  store.userInfo = {
    id: 1,
    username: 'tester',
    nickname: '',
    email: '',
    avatar: '',
    is_superuser: isSuperuser,
    permissions,
    roles: [],
  } as any
  const wrapper = mount(TestButton, {
    global: { plugins: [pinia], directives: { permission } },
  })
  return wrapper
}

describe('v-permission', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('拥有权限时保留元素', () => {
    const wrapper = mountWithPermission(['user:delete'])
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('无权限时移除元素', () => {
    const wrapper = mountWithPermission(['user:read'])
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('超管始终可见', () => {
    const wrapper = mountWithPermission([], true)
    expect(wrapper.find('button').exists()).toBe(true)
  })
})
