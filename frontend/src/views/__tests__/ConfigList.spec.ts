/**
 * 参数设置页测试。
 *
 * 覆盖：
 * - 列表渲染：请求 /configs 并渲染 key/value/类型标签
 * - 新增：打开弹窗 → 必填被 ProForm 防线拦截 → 填完 create 调用 + 刷新
 * - 删除：确认弹窗 → remove 调用
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus, { ElMessageBox } from 'element-plus'
import ConfigList from '@/views/ConfigList.vue'
import { configApi } from '@/api'
import { useUserStore } from '@/stores/user'

// el-table 依赖 ResizeObserver（jsdom 未实现），缺失时表格不渲染行
if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}

vi.mock('@/api', () => ({
  configApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() },
}))

const wrappers: VueWrapper[] = []
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
})

beforeEach(() => {
  vi.clearAllMocks()
})

function mountList() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useUserStore()
  store.userInfo = {
    id: 1,
    username: 'admin',
    nickname: '管理员',
    email: '',
    avatar: '',
    is_superuser: true,
    permissions: ['config:read', 'config:write'],
    roles: [],
  } as any
  ;(configApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
    code: 0,
    data: {
      total: 2,
      items: [
        {
          id: 1,
          key: 'site_name',
          value: 'FastAPI Base',
          value_type: 'string',
          remark: '站点名称',
          created_at: '2026-09-16 12:00:00',
          updated_at: '2026-09-16 12:00:00',
        },
        {
          id: 2,
          key: 'upload_max_size',
          value: '10',
          value_type: 'int',
          remark: '上传大小上限（MB）',
          created_at: '2026-09-16 12:00:00',
          updated_at: '2026-09-16 12:00:00',
        },
      ],
    },
  })
  const wrapper = mount(ConfigList, {
    global: { plugins: [pinia, ElementPlus] },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('参数设置页', () => {
  it('渲染：请求配置列表并展示 key/value/类型标签', async () => {
    const wrapper = mountList()
    await flushPromises()
    await nextTick()

    expect(configApi.list).toHaveBeenCalled()
    const text = wrapper.text()
    expect(text).toContain('site_name')
    expect(text).toContain('FastAPI Base')
    expect(text).toContain('upload_max_size')
    expect(text).toContain('整数') // value_type=int 的类型标签
  })

  it('新增：必填被防线拦截 → 填完 create 调用并刷新', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(configApi.create as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })

    await wrapper.findAll('button').find((b) => b.text().includes('新增参数'))!.trigger('click')
    await nextTick()

    const keyInput = wrapper.find('input[placeholder="如 site_name（小写字母/数字/下划线）"]')
    const valueInput = wrapper.find('input[placeholder="如 FastAPI Base"]')
    expect(keyInput.exists()).toBe(true)
    expect(valueInput.exists()).toBe(true)

    // 不填必填直接提交 → ProForm 防线拦截，不调 API
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()
    expect(configApi.create).not.toHaveBeenCalled()

    // 填 key/value 后提交
    await keyInput.setValue('login_fail_limit')
    await valueInput.setValue('5')
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()

    expect(configApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ key: 'login_fail_limit', value: '5', value_type: 'string' }),
    )
    // 提交后刷新列表
    expect(configApi.list).toHaveBeenCalledTimes(2)
  })

  it('删除：确认弹窗 → remove 调用并刷新', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(configApi.remove as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })
    const confirmSpy = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as any)

    const delBtns = wrapper.findAll('button').filter((b) => b.text().includes('删除'))
    // 跳过 jsdom 幽灵空行按钮，取第一个数据行（id=1 的 site_name）
    await delBtns[1].trigger('click')
    await flushPromises()

    expect(confirmSpy).toHaveBeenCalled()
    expect(configApi.remove).toHaveBeenCalledWith(1)
    expect(configApi.list).toHaveBeenCalledTimes(2)
    confirmSpy.mockRestore()
  })
})
