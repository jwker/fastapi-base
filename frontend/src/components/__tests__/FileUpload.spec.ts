/* global File */
/**
 * FileUpload 通用上传组件测试。
 *
 * 覆盖：
 * - 上传成功：触发 fileApi.upload，URL 写入 v-model
 * - 超大小前端预校验：不调接口，直接提示
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus, { ElMessage } from 'element-plus'
import FileUpload from '@/components/FileUpload.vue'
import { fileApi } from '@/api'

vi.mock('@/api', () => ({
  fileApi: { upload: vi.fn() },
}))

function mountUpload(props: Record<string, unknown> = {}) {
  return mount(FileUpload, {
    props: { modelValue: '', ...props },
    global: { plugins: [ElementPlus] },
  })
}

describe('FileUpload 通用上传', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('渲染：选择文件按钮 + URL 输入框', () => {
    const wrapper = mountUpload()
    expect(wrapper.text()).toContain('选择文件')
    expect(wrapper.find('input[placeholder*="URL"]').exists()).toBe(true)
  })

  it('上传成功：调用 fileApi.upload，URL 通过 update:modelValue 传出', async () => {
    vi.mocked(fileApi.upload).mockResolvedValue({
      code: 0,
      message: '上传成功',
      data: { url: '/uploads/202609/abc.png', name: 'a.png', size: 10 },
    } as any)
    const wrapper = mountUpload()
    const file = new File(['x'], 'a.png', { type: 'image/png' })

    // 触发 el-upload 的 on-change prop（组件内部传入的 option 含 raw 原始文件）
    const upload = wrapper.findComponent({ name: 'ElUpload' })
    ;(upload.vm as any).$props.onChange({ raw: file })
    await flushPromises()

    expect(fileApi.upload).toHaveBeenCalledTimes(1)
    expect(fileApi.upload).toHaveBeenCalledWith(file)
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['/uploads/202609/abc.png'])
  })

  it('超大小：前端预校验拦截，不调接口', async () => {
    const errorSpy = vi.spyOn(ElMessage, 'error').mockImplementation((() => undefined) as any)
    const wrapper = mountUpload({ maxSizeMb: 1 })
    // 构造 2MB 假文件（File.size 无法直接赋值，用 defineProperty）
    const file = new File(['x'.repeat(1024)], 'big.png', { type: 'image/png' })
    Object.defineProperty(file, 'size', { value: 2 * 1024 * 1024 })

    const upload = wrapper.findComponent({ name: 'ElUpload' })
    ;(upload.vm as any).$props.onChange({ raw: file })
    await flushPromises()

    expect(fileApi.upload).not.toHaveBeenCalled()
    expect(errorSpy).toHaveBeenCalled()
  })
})
