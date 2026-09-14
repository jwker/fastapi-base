/* global File */
/**
 * 文件管理页测试。
 *
 * 覆盖：
 * - 列表渲染：请求 /files 并渲染缩略图/文件名/大小/来源标签/备注/上传人
 * - 上传：选择文件 → 逐个调 upload(source=manual, remark) → 成功后刷新列表
 * - 复制 URL：点击复制写入 clipboard
 * - 删除：确认弹窗 → remove → 刷新；无 file:delete 权限不显示删除按钮
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus, { ElMessageBox } from 'element-plus'
import FileManager from '@/views/FileManager.vue'
import { fileApi } from '@/api'
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
  fileApi: { upload: vi.fn(), list: vi.fn(), remove: vi.fn() },
}))

const wrappers: VueWrapper[] = []
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
})

function mountList(isSuperuser = true, permissions: string[] = []) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useUserStore()
  store.userInfo = {
    id: 1,
    username: 'admin',
    nickname: '管理员',
    email: '',
    avatar: '',
    is_superuser: isSuperuser,
    permissions,
    roles: [],
  } as any
  const wrapper = mount(FileManager, {
    global: { plugins: [pinia, ElementPlus] },
  })
  wrappers.push(wrapper)
  return { wrapper }
}

const pageData = {
  code: 0,
  message: 'ok',
  data: {
    total: 2,
    items: [
      {
        id: 1,
        url: '/uploads/202609/a1b2c3.png',
        name: 'avatar.png',
        size: 2048,
        mime_type: 'image/png',
        source: 'avatar',
        remark: '',
        created_by: 1,
        created_by_name: 'admin',
        created_at: '2026-09-14 10:00:00',
      },
      {
        id: 2,
        url: '/uploads/202609/d4e5f6.pdf',
        name: '合同.pdf',
        size: 5 * 1024 * 1024,
        mime_type: 'application/pdf',
        source: 'manual',
        remark: '供应商合同',
        created_by: 1,
        created_by_name: 'admin',
        created_at: '2026-09-14 11:00:00',
      },
    ],
  },
}

beforeEach(() => {
  // 清空调用记录（实现由各测试按需设置），避免跨测试累积导致 toHaveBeenCalledTimes 误判
  vi.clearAllMocks()
  ;(fileApi.list as ReturnType<typeof vi.fn>).mockResolvedValue(pageData)
})

describe('FileManager 列表渲染', () => {
  it('请求列表并渲染文件名/大小/来源/备注/上传人', async () => {
    const { wrapper } = mountList()
    await flushPromises()
    await nextTick()

    expect(fileApi.list).toHaveBeenCalled()
    const text = wrapper.text()
    expect(text).toContain('avatar.png')
    expect(text).toContain('2.0 KB')
    expect(text).toContain('5.0 MB')
    expect(text).toContain('头像') // source=avatar 的来源标签
    expect(text).toContain('素材') // source=manual 的来源标签
    expect(text).toContain('供应商合同')
    // 路径列展示完整 url
    expect(text).toContain('/uploads/202609/a1b2c3.png')
    expect(text).toContain('admin')
  })

  it('非图片显示文件图标而非缩略图', async () => {
    const { wrapper } = mountList()
    await flushPromises()
    // 列表第二个文件是 PDF：渲染文件图标
    const ico = wrapper.findAll('.file-ico')
    expect(ico.length).toBeGreaterThanOrEqual(1)
  })
})

describe('FileManager 上传', () => {
  it('选文件后弹窗确认，点确定才带 source=manual 和备注上传并刷新', async () => {
    const { wrapper } = mountList()
    await flushPromises()
    ;(fileApi.upload as ReturnType<typeof vi.fn>).mockResolvedValue({
      code: 0,
      data: { url: '/uploads/202609/new.png' },
    })

    const input = wrapper.find('input[type="file"]')
    const fakeFile = new File([new Uint8Array(64)], 'banner.png', { type: 'image/png' })
    Object.defineProperty(input.element, 'files', {
      value: [fakeFile],
      configurable: true,
    })
    await input.trigger('change')
    await flushPromises()

    // 选完不立即上传，弹窗出现（含文件列表），备注可填
    expect(fileApi.upload).not.toHaveBeenCalled()
    expect(wrapper.find('.pending-item').text()).toContain('banner.png')

    const remarkInput = wrapper.find('input[placeholder*="可选"]')
    await remarkInput.setValue('首页轮播图')
    const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes('确定上传'))
    await confirmBtn!.trigger('click')
    await flushPromises()

    expect(fileApi.upload).toHaveBeenCalledWith(fakeFile, 'manual', '首页轮播图')
    expect(fileApi.list).toHaveBeenCalledTimes(2) // 初始 + 上传后刷新
  })

  it('弹窗点取消不上传', async () => {
    const { wrapper } = mountList()
    await flushPromises()

    const input = wrapper.find('input[type="file"]')
    const f1 = new File([new Uint8Array(1)], 'a.png', { type: 'image/png' })
    Object.defineProperty(input.element, 'files', {
      value: [f1],
      configurable: true,
    })
    await input.trigger('change')
    await flushPromises()

    const cancelBtn = wrapper.findAll('button').find((b) => b.text().includes('取消'))
    await cancelBtn!.trigger('click')
    await flushPromises()

    expect(fileApi.upload).not.toHaveBeenCalled()
  })

  it('上传失败的单文件不阻塞其余文件', async () => {
    const { wrapper } = mountList()
    await flushPromises()
    ;(fileApi.upload as ReturnType<typeof vi.fn>)
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce({ code: 0, data: { url: '/uploads/202609/ok.png' } })

    const input = wrapper.find('input[type="file"]')
    const f1 = new File([new Uint8Array(1)], 'a.png', { type: 'image/png' })
    const f2 = new File([new Uint8Array(1)], 'b.png', { type: 'image/png' })
    Object.defineProperty(input.element, 'files', {
      value: [f1, f2],
      configurable: true,
    })
    await input.trigger('change')
    await flushPromises()

    const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes('确定上传'))
    await confirmBtn!.trigger('click')
    await flushPromises()

    expect(fileApi.upload).toHaveBeenCalledTimes(2)
    expect(fileApi.list).toHaveBeenCalledTimes(2)
  })
})

describe('FileManager 复制与删除', () => {
  it('点击复制 URL 写入 clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    // jsdom 的 navigator.clipboard 默认不存在，defineProperty 注入
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    })
    const { wrapper } = mountList()
    await flushPromises()

    // jsdom 下 el-table 会渲染一组绑定空 row 的"幽灵"操作按钮（AuditLogList 同款现象），
    // 取第 2 个（第一个数据行）验证真实行数据
    const copyBtns = wrapper
      .findAll('button')
      .filter((b) => b.text().includes('复制 URL'))
    await copyBtns[1].trigger('click')
    await flushPromises()

    expect(writeText).toHaveBeenCalledWith('/uploads/202609/a1b2c3.png')
  })

  it('点击删除经确认后调用 remove 并刷新', async () => {
    const confirm = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as any)
    ;(fileApi.remove as ReturnType<typeof vi.fn>).mockResolvedValue({ code: 0 })
    const { wrapper } = mountList()
    await flushPromises()

    // 同上：跳过 jsdom 幽灵按钮，取第一个数据行（id=1 的 avatar.png）
    const delBtns = wrapper
      .findAll('button')
      .filter((b) => b.text().includes('删除'))
    await delBtns[1].trigger('click')
    await flushPromises()

    expect(confirm).toHaveBeenCalled()
    expect(fileApi.remove).toHaveBeenCalledWith(1)
    expect(fileApi.list).toHaveBeenCalledTimes(2)
  })

  it('无 file:delete 权限时不显示删除按钮', async () => {
    const { wrapper } = mountList(false, [])
    await flushPromises()
    const delBtn = wrapper.findAll('button').find((b) => b.text().includes('删除'))
    expect(delBtn).toBeUndefined()
  })
})
