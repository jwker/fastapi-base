/**
 * 字典取用 hook：useDict('file_source') → options（喂 el-select/下拉）+ getLabel(value)（取文案）。
 *
 * - 模块级缓存：同一 type 只请求一次，跨组件/跨页面共享（管理后台单人操作场景足够）
 * - refresh()：管理页改完字典后强制重拉（删除缓存 + 重新请求）
 * - getLabel 未命中时回退显示原始值（字典被删/未配置时不崩）
 */
import { ref } from 'vue'
import { dictApi } from '@/api'
import type { DictOption } from '@/types'

const cache = new Map<string, DictOption[]>()
/** 进行中的请求（并发挂载时共享同一请求，避免重复拉取） */
const inflight = new Map<string, Promise<void>>()

/** 测试用：清空模块级缓存（vitest 跨用例隔离） */
export function clearDictCache() {
  cache.clear()
  inflight.clear()
}

export function useDict(type: string) {
  const options = ref<DictOption[]>(cache.get(type) ?? [])
  const loading = ref(false)

  function load(): Promise<void> {
    if (cache.has(type)) {
      options.value = cache.get(type)!
      return Promise.resolve()
    }
    if (!inflight.has(type)) {
      inflight.set(
        type,
        (async () => {
          loading.value = true
          try {
            const res = await dictApi.byType(type)
            const list = res.data ?? []
            cache.set(type, list)
            options.value = list
          } finally {
            loading.value = false
            inflight.delete(type)
          }
        })(),
      )
    }
    return inflight.get(type)!
  }

  /** value → 显示文案；未命中回退原始值 */
  function getLabel(value: unknown): string {
    const v = String(value ?? '')
    return options.value.find((o) => o.value === v)?.label ?? v
  }

  /** 强制重拉（管理页改动后调用） */
  async function refresh() {
    cache.delete(type)
    await load()
  }

  load()
  return { options, loading, getLabel, refresh }
}
