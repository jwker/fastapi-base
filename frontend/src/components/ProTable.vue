<script setup lang="ts">
/**
 * 通用表格组件：分页 + 检索 + 操作按钮，配置化使用。
 *
 * props:
 *  - columns: 列配置 [{ prop, label, width?, formatter? }]
 *  - fetchApi: (params) => Promise<{ data: { total, items } }>
 *  - searchPlaceholder: 检索框占位
 *  - showSearch: 是否显示检索
 *  - rowKey: 行主键字段
 *  - actions: 操作按钮配置 [{ label, type?, permission?, show?, onClick(row), loading? }]
 *  - createLabel: 新增按钮文案，为空则不显示
 */
import { onMounted, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import type { ApiResponse, PageResult } from '@/types'

export interface ColumnConfig {
  prop: string
  label: string
  width?: string | number
  minWidth?: string | number
  formatter?: (row: Record<string, any>, value: any) => string | number
  slot?: string
}

export interface ActionConfig {
  label: string
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
  permission?: string
  show?: (row: Record<string, any>) => boolean
  /** 操作前弹出确认框的提示文案，如「确定删除该记录？」 */
  confirm?: string
  onClick: (row: Record<string, any>) => void
}

const props = withDefaults(
  defineProps<{
    columns: ColumnConfig[]
    fetchApi: (params: {
      page: number
      page_size: number
      keyword?: string
    }) => Promise<ApiResponse<PageResult<any>>>
    searchPlaceholder?: string
    showSearch?: boolean
    rowKey?: string
    actions?: ActionConfig[]
    createLabel?: string
    /** 新增按钮所需权限码，如 'user:create'；缺省则始终显示 */
    createPermission?: string
    onCreate?: () => void
    pageSize?: number
  }>(),
  {
    searchPlaceholder: '请输入关键字',
    showSearch: true,
    rowKey: 'id',
    actions: () => [],
    createLabel: '',
    createPermission: '',
    pageSize: 10,
  },
)

const emit = defineEmits<{ (e: 'refresh'): void }>()

const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(props.pageSize)
const keyword = ref('')

async function loadData() {
  loading.value = true
  try {
    const res = await props.fetchApi({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
    })
    list.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadData()
}

function handleReset() {
  keyword.value = ''
  page.value = 1
  loadData()
}

async function runAction(row: Record<string, any>, action: ActionConfig) {
  if (action.confirm) {
    try {
      await ElMessageBox.confirm(action.confirm, '提示', {
        type: 'warning',
        confirmButtonText: '确定',
        cancelButtonText: '取消',
      })
    } catch {
      return
    }
  }
  await action.onClick(row)
  loadData()
}

function handlePageChange(p: number) {
  page.value = p
  loadData()
}

function handleSizeChange(size: number) {
  pageSize.value = size
  page.value = 1
  loadData()
}

function visibleActions(row: Record<string, any>): ActionConfig[] {
  return props.actions.filter((a) => (a.show ? a.show(row) : true) && isPermitted(a))
}

function isPermitted(action: ActionConfig) {
  if (!action.permission) return true
  const userStore = useUserStore()
  if (userStore.isSuperuser) return true
  return userStore.permissions.includes(action.permission)
}

/** 新增按钮权限：配置了 createPermission 且当前用户无权限时隐藏 */
function canCreate() {
  if (!props.createPermission) return true
  const userStore = useUserStore()
  if (userStore.isSuperuser) return true
  return userStore.permissions.includes(props.createPermission)
}

onMounted(loadData)
watch(
  () => props.pageSize,
  (v) => {
    pageSize.value = v
    loadData()
  },
)

defineExpose({ loadData, refresh: loadData })
</script>

<template>
  <div class="pro-table">
    <div v-if="showSearch || createLabel" class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="keyword"
          :placeholder="searchPlaceholder"
          clearable
          style="width: 260px"
          @keyup.enter="handleSearch"
          @clear="handleReset"
        >
          <template #prefix
            ><el-icon><Search /></el-icon
          ></template>
        </el-input>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>
      <div class="toolbar-right">
        <el-button
          v-if="createLabel && canCreate()"
          type="primary"
          @click="onCreate"
        >
          <el-icon><Plus /></el-icon>{{ createLabel }}
        </el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="list" :row-key="rowKey" border stripe>
      <el-table-column
        v-for="col in columns"
        :key="col.prop"
        :prop="col.prop"
        :label="col.label"
        :width="col.width"
        :min-width="col.minWidth"
      >
        <template #default="{ row }">
          <slot v-if="col.slot" :name="col.slot" :row="row" />
          <template v-else-if="col.formatter">{{ col.formatter(row, row[col.prop]) }}</template>
          <template v-else>{{ row[col.prop] }}</template>
        </template>
      </el-table-column>

      <el-table-column v-if="actions.length" label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button
            v-for="(action, i) in visibleActions(row)"
            :key="i"
            :type="action.type || 'primary'"
            link
            size="small"
            @click="runAction(row, action)"
          >
            {{ action.label }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
