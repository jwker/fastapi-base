<script setup lang="ts">
defineOptions({ name: 'AuditLogList' })
/**
 * 操作审计日志：列表 + 筛选 + 详情抽屉 + 导出（audit:read）+ 导出后删除（audit:delete）。
 */
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ProTable, { type ColumnConfig } from '@/components/ProTable.vue'
import { auditLogApi } from '@/api'
import { useDict } from '@/composables/useDict'
import type { AuditLogRecord } from '@/types'
import { useUserStore } from '@/stores/user'

const tableRef = ref<InstanceType<typeof ProTable>>()
const userStore = useUserStore()
const exporting = ref(false)
const deleting = ref(false)

// ---------- 筛选条件 ----------
const filters = reactive({
  username: '',
  module: '',
  action: '',
  status: undefined as number | undefined,
  start_time: undefined as string | undefined,
  end_time: undefined as string | undefined,
})
const dateRange = ref<[string, string] | null>(null)

watch(dateRange, (val) => {
  // 范围选择器 value-format 为日期字符串，拼上起止时刻传给后端
  if (val && val[0] && val[1]) {
    filters.start_time = `${val[0]} 00:00:00`
    filters.end_time = `${val[1]} 23:59:59`
  } else {
    filters.start_time = undefined
    filters.end_time = undefined
  }
})

// ProTable 的 fetchApi 只认识 page/page_size/keyword，额外筛选通过 extraParams 函数现算透传
function getExtraParams() {
  const params: Record<string, unknown> = {}
  if (filters.username) params.username = filters.username
  if (filters.module) params.module = filters.module
  if (filters.action) params.action = filters.action
  if (filters.status !== undefined) params.status = filters.status
  if (filters.start_time) params.start_time = filters.start_time
  if (filters.end_time) params.end_time = filters.end_time
  return params
}

function search() {
  tableRef.value?.refresh()
}

function reset() {
  filters.username = ''
  filters.module = ''
  filters.action = ''
  filters.status = undefined
  dateRange.value = null
  tableRef.value?.refresh()
}

// ---------- 导出 + 导出后删除 ----------
// 可删除日志 = 有 audit:delete 权限（超管 '*' 通配）
const canDeleteLogs = computed(
  () => userStore.isSuperuser || userStore.permissions.includes('audit:delete'),
)

// 导出/删除共用同一组筛选；未填时间范围时 end_time 兜底为「当前时刻」，
// 保证删除边界 = 导出时刻（导出后新产生的日志不会被删）。
function getExportParams() {
  const params: Record<string, unknown> = getExtraParams()
  if (!params.end_time) {
    params.end_time = formatNow()
  }
  return params
}

function formatNow() {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function handleExport() {
  const params = getExportParams()
  exporting.value = true
  try {
    const blob = (await auditLogApi.export(params as any)) as Blob
    downloadBlob(blob, `audit-logs-${new Date().toISOString().slice(0, 19).replace(/[-:]/g, '')}.csv`)

    // 无删除权限：导出即结束
    if (!canDeleteLogs.value) {
      ElMessage.success('导出成功')
      return
    }
    // 有删除权限：弹窗询问是否删除已导出的日志（先统计预计条数）
    const res = await auditLogApi.list({ ...(params as any), page: 1, page_size: 1 })
    const total = res.data?.total ?? 0
    if (total === 0) {
      ElMessage.success('导出成功（当前筛选无数据）')
      return
    }
    await ElMessageBox.confirm(
      `导出成功，共 ${total} 条。是否删除已导出的日志？\n删除范围与导出一致（导出时间点之前），删除后不可恢复。`,
      '导出完成',
      { confirmButtonText: '删除', cancelButtonText: '保留', confirmButtonType: 'danger', type: 'warning' },
    )
    await doDelete(params)
  } catch (e: any) {
    // 用户取消删除：保留数据，不提示错误
    if (e === 'cancel' || e === 'close') return
    if (!e?.response) ElMessage.error(e?.message || '导出失败，请重试')
  } finally {
    exporting.value = false
  }
}

async function doDelete(params: Record<string, unknown>) {
  deleting.value = true
  try {
    const res = await auditLogApi.remove(params as any)
    ElMessage.success(res.message || `已删除 ${res.data?.deleted ?? 0} 条`)
    tableRef.value?.refresh()
  } catch {
    // 删除失败：已下载的 CSV 文件不受影响
  } finally {
    deleting.value = false
  }
}

// ---------- 字典 ----------
// 操作类型：文案从字典取（audit_action），tag 颜色保留页面配置
const actionType: Record<string, 'success' | 'warning' | 'danger' | 'primary' | 'info'> = {
  create: 'success',
  update: 'warning',
  delete: 'danger',
  login: 'primary',
  logout: 'info',
  other: 'info',
}
const { getLabel: actionLabel, options: actionOptions } = useDict('audit_action')
const methodMeta: Record<string, string> = {
  POST: 'primary',
  PUT: 'warning',
  PATCH: 'warning',
  DELETE: 'danger',
}
const moduleOptions = ['用户管理', '角色管理', '菜单管理', '权限管理', '认证', '文件管理', '操作日志']

// ---------- 表格 ----------
const columns: ColumnConfig[] = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'username', label: '操作人', minWidth: 100, slot: 'username' },
  { prop: 'module', label: '模块', width: 110 },
  { prop: 'action', label: '动作', width: 90, slot: 'action' },
  { prop: 'method', label: '方法', width: 80, slot: 'method' },
  { prop: 'path', label: '请求路径', minWidth: 160 },
  { prop: 'response_status', label: '状态', width: 80, slot: 'status' },
  { prop: 'ip', label: 'IP', width: 130 },
  {
    prop: 'created_at',
    label: '操作时间',
    minWidth: 160,
    formatter: (_r, v) => (v ? new Date(v).toLocaleString() : '-'),
  },
  { prop: 'op', label: '操作', width: 80, slot: 'detail' },
]

// 详情按钮不用 ProTable 的 actions（其操作列 fixed 会在测试环境产生克隆行），
// 用列内 slot 渲染，行为与普通列一致。

// ---------- 详情抽屉 ----------
const drawerVisible = ref(false)
const detail = ref<AuditLogRecord | null>(null)

function openDetail(row: any) {
  detail.value = row as AuditLogRecord
  drawerVisible.value = true
}

function fmtBody(body: string) {
  if (!body) return '（无请求参数）'
  try {
    return JSON.stringify(JSON.parse(body), null, 2)
  } catch {
    return body
  }
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-form :inline="true" class="filter-form" @submit.prevent>
        <el-form-item label="操作人">
          <el-input
            v-model="filters.username"
            placeholder="操作人"
            clearable
            style="width: 130px"
            @keyup.enter="search"
          />
        </el-form-item>
        <el-form-item label="模块">
          <el-select
            v-model="filters.module"
            placeholder="全部"
            clearable
            style="width: 130px"
          >
            <el-option v-for="m in moduleOptions" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item label="动作">
          <el-select
            v-model="filters.action"
            placeholder="全部"
            clearable
            style="width: 120px"
          >
            <el-option
              v-for="opt in actionOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="filters.status"
            placeholder="全部"
            clearable
            style="width: 120px"
          >
            <el-option label="2xx 成功" :value="200" />
            <el-option label="4xx 失败" :value="400" />
            <el-option label="5xx 异常" :value="500" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="reset">重置</el-button>
          <el-button type="success" :loading="exporting" @click="handleExport">
            导出 CSV
          </el-button>
        </el-form-item>
      </el-form>

      <ProTable
        ref="tableRef"
        :columns="columns"
        :fetch-api="auditLogApi.list"
        :extra-params="getExtraParams"
        :show-search="false"
      >
        <template #username="{ row }">
          <span>{{ row.username || '（匿名）' }}</span>
        </template>
        <template #action="{ row }">
          <el-tag :type="actionType[row.action] ?? 'info'" size="small">
            {{ actionLabel(row.action) }}
          </el-tag>
        </template>
        <template #method="{ row }">
          <el-tag :type="(methodMeta[row.method] as any) ?? 'info'" size="small" effect="plain">
            {{ row.method }}
          </el-tag>
        </template>
        <template #status="{ row }">
          <el-tag
            :type="row.response_status < 400 ? 'success' : row.response_status < 500 ? 'warning' : 'danger'"
            size="small"
            effect="plain"
          >
            {{ row.response_status }}
          </el-tag>
        </template>
        <template #detail="{ row }">
          <el-button link type="primary" size="small" @click="openDetail(row)">
            详情
          </el-button>
        </template>
      </ProTable>
    </el-card>

    <el-drawer v-model="drawerVisible" title="操作详情" size="520px">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="ID">{{ detail.id }}</el-descriptions-item>
          <el-descriptions-item label="操作人">
            {{ detail.username || '（匿名）' }}
          </el-descriptions-item>
          <el-descriptions-item label="模块">{{ detail.module }}</el-descriptions-item>
          <el-descriptions-item label="动作">
            {{ actionLabel(detail.action) }}
          </el-descriptions-item>
          <el-descriptions-item label="方法">{{ detail.method }}</el-descriptions-item>
          <el-descriptions-item label="请求路径">{{ detail.path }}</el-descriptions-item>
          <el-descriptions-item label="状态码">
            <el-tag
              :type="detail.response_status < 400 ? 'success' : 'danger'"
              size="small"
            >
              {{ detail.response_status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="IP">{{ detail.ip || '-' }}</el-descriptions-item>
          <el-descriptions-item label="User-Agent">
            {{ detail.user_agent || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="操作时间">
            {{ new Date(detail.created_at).toLocaleString() }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">请求参数（已脱敏）</el-divider>
        <pre class="body-pre">{{ fmtBody(detail.request_body) }}</pre>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.filter-form {
  margin-bottom: 4px;
}
.body-pre {
  margin: 0;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.6;
  max-height: 320px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
