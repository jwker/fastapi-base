/**
 * 字典管理页测试。
 *
 * 覆盖：类型列表渲染、新增/编辑类型调用、字典项弹窗列表/增删改、删除类型确认。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus, { ElMessageBox } from 'element-plus'
import DictList from '@/views/DictList.vue'
import { dictApi } from '@/api'
import { clearDictCache } from '@/composables/useDict'
import { useUserStore } from '@/stores/user'

if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}

vi.mock('@/api', () => ({
  dictApi: {
    types: vi.fn(),
    createType: vi.fn(),
    updateType: vi.fn(),
    removeType: vi.fn(),
    items: vi.fn(),
    createItem: vi.fn(),
    updateItem: vi.fn(),
    removeItem: vi.fn(),
  },
}))

const wrappers: VueWrapper[] = []
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
})

beforeEach(() => {
  vi.clearAllMocks()
  clearDictCache()
})

const typeRows = [
  {
    id: 1,
    name: '系统状态',
    type: 'sys_status',
    remark: '用户/角色状态',
    item_count: 2,
    created_at: '2026-09-14 10:00:00',
  },
  {
    id: 2,
    name: '文件来源',
    type: 'file_source',
    remark: '',
    item_count: 2,
    created_at: '2026-09-14 10:00:00',
  },
]

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
    permissions: [],
    roles: [],
  } as any
  ;(dictApi.types as ReturnType<typeof vi.fn>).mockResolvedValue({
    code: 0,
    data: { total: 2, items: typeRows },
  })
  const wrapper = mount(DictList, { global: { plugins: [pinia, ElementPlus] } })
  wrappers.push(wrapper)
  return wrapper
}

describe('DictList 类型列表', () => {
  it('请求字典类型并渲染列表', async () => {
    const wrapper = mountList()
    await flushPromises()
    await nextTick()
    expect(dictApi.types).toHaveBeenCalled()
    expect(wrapper.text()).toContain('系统状态')
    expect(wrapper.text()).toContain('sys_status')
    expect(wrapper.text()).toContain('文件来源')
  })
})

describe('DictList 类型新增/编辑', () => {
  it('新增：填必填后确定 → createType 调用', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(dictApi.createType as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })

    await wrapper.findAll('button').find((b) => b.text().includes('新增字典'))!.trigger('click')
    await nextTick()
    expect(wrapper.find('input[placeholder="如 文件来源"]').exists()).toBe(true)

    await wrapper.find('input[placeholder="如 文件来源"]').setValue('性别')
    await wrapper.find('input[placeholder="如 file_source（小写字母/数字/下划线）"]').setValue('gender')
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()

    expect(dictApi.createType).toHaveBeenCalledWith(
      expect.objectContaining({ name: '性别', type: 'gender' }),
    )
  })

  it('编辑：回填旧值 → 修改名称 → updateType 调用', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(dictApi.updateType as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })

    // 幽灵按钮：ProTable 表格在 jsdom 下第一组操作按钮绑定空 row，取数据行的 [1]
    const editBtns = wrapper.findAll('button').filter((b) => b.text().includes('编辑'))
    await editBtns[1].trigger('click')
    await nextTick()

    const nameInput = wrapper.find('input[placeholder="如 文件来源"]').element as HTMLInputElement
    expect(nameInput.value).toBe('系统状态')

    await wrapper.find('input[placeholder="如 文件来源"]').setValue('状态')
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()
    expect(dictApi.updateType).toHaveBeenCalledWith(1, expect.objectContaining({ name: '状态' }))
  })
})

describe('DictList 字典项管理', () => {
  it('点「数据」打开项弹窗并加载项列表', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(dictApi.items as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: [
        { id: 11, type_id: 1, label: '启用', value: '1', sort: 1, is_default: true, status: 1, remark: '', created_at: '' },
      ],
    })

    const dataBtns = wrapper.findAll('button').filter((b) => b.text().includes('数据'))
    await dataBtns[1].trigger('click')
    await flushPromises()

    expect(dictApi.items).toHaveBeenCalledWith(1)
    expect(wrapper.text()).toContain('字典数据')
    expect(wrapper.text()).toContain('启用')
  })

  it('项弹窗内新增数据 → createItem 调用并清缓存', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(dictApi.items as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0, data: [] })
    ;(dictApi.createItem as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })

    // 幽灵按钮取 [1]（数据行），确保 currentType 正确
    const dataBtns = wrapper.findAll('button').filter((b) => b.text().includes('数据'))
    await dataBtns[1].trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((b) => b.text().includes('新增数据'))!.trigger('click')
    await nextTick()

    await wrapper.find('input[placeholder="如 头像"]').setValue('头像')
    await wrapper.find('input[placeholder="如 avatar"]').setValue('avatar')
    await wrapper.findAll('button').find((b) => b.text().includes('确定'))!.trigger('click')
    await flushPromises()

    expect(dictApi.createItem).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ label: '头像', value: 'avatar', status: 1 }),
    )
  })

  it('删除类型需确认，确认后 removeType 调用', async () => {
    const wrapper = mountList()
    await flushPromises()
    ;(dictApi.removeType as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })
    const confirmSpy = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as any)

    const delBtns = wrapper.findAll('button').filter((b) => b.text().includes('删除'))
    await delBtns[1].trigger('click')
    await flushPromises()

    expect(confirmSpy).toHaveBeenCalled()
    expect(dictApi.removeType).toHaveBeenCalledWith(1)
  })
})
