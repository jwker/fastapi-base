/**
 * useDict hook 测试。
 *
 * 覆盖：首次加载请求一次、模块级缓存复用、getLabel 映射/未命中回退、refresh 重拉。
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { clearDictCache, useDict } from '@/composables/useDict'
import { dictApi } from '@/api'

vi.mock('@/api', () => ({
  dictApi: { byType: vi.fn() },
}))

beforeEach(() => {
  vi.clearAllMocks()
  clearDictCache()
})

const mockData = [
  { label: '启用', value: '1', sort: 1, is_default: true },
  { label: '禁用', value: '0', sort: 2, is_default: false },
]

describe('useDict', () => {
  it('首次加载请求一次并填充 options', async () => {
    ;(dictApi.byType as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockData })
    const { options, loading } = useDict('sys_status')
    expect(loading.value).toBe(true)
    await vi.waitFor(() => expect(options.value.length).toBe(2))
    expect(dictApi.byType).toHaveBeenCalledWith('sys_status')
    expect(options.value[0]).toEqual(mockData[0])
  })

  it('模块级缓存：同一 type 二次 useDict 不再请求', async () => {
    ;(dictApi.byType as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockData })
    useDict('sys_status')
    await vi.waitFor(() => expect(useDict('sys_status').options.value.length).toBe(2))
    useDict('sys_status')
    expect(dictApi.byType).toHaveBeenCalledTimes(1)
  })

  it('getLabel 映射 value → 文案；未命中回退原始值', async () => {
    ;(dictApi.byType as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockData })
    const { getLabel } = useDict('sys_status')
    await vi.waitFor(() => expect(getLabel('1')).toBe('启用'))
    expect(getLabel('0')).toBe('禁用')
    expect(getLabel('99')).toBe('99')
    expect(getLabel(null)).toBe('')
  })

  it('refresh 删除缓存并重拉', async () => {
    ;(dictApi.byType as ReturnType<typeof vi.fn>).mockResolvedValue({ data: mockData })
    const { getLabel, refresh } = useDict('file_source')
    await vi.waitFor(() => expect(getLabel('1')).toBe('启用'))

    ;(dictApi.byType as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [{ label: '正常', value: '1', sort: 1, is_default: true }],
    })
    await refresh()
    expect(dictApi.byType).toHaveBeenCalledTimes(2)
    expect(getLabel('1')).toBe('正常')
  })
})
