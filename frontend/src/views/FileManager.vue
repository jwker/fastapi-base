<script setup lang="ts">
defineOptions({ name: 'FileManager' })
/**
 * 文件管理（素材库）：上传（带备注）/ 列表 / 搜索 / 复制 URL / 删除。
 * - 权限：列表 file:read（菜单控制入口），删除 file:delete
 * - 来源：程序自动打标，头像 avatar / 本页 manual
 */
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ProTable, { type ColumnConfig } from '@/components/ProTable.vue'
import { fileApi } from '@/api'
import { useDict } from '@/composables/useDict'
import type { FileRecord } from '@/types'
import { useUserStore } from '@/stores/user'

const tableRef = ref<InstanceType<typeof ProTable>>()
const userStore = useUserStore()

const canDelete = computed(
  () => userStore.isSuperuser || userStore.permissions.includes('file:delete'),
)

// ---------- 上传（选文件 → 弹窗确认 → 逐个上传） ----------
const uploading = ref(false)
const remark = ref('')
const pendingFiles = ref<File[]>([])
const uploadDialogVisible = ref(false)

// 来源文案从字典取（file_source），tag 颜色保留页面配置（字典只管文案）
const sourceType: Record<string, 'success' | 'info' | 'warning' | 'primary'> = {
  avatar: 'info',
  manual: 'primary',
}
const { getLabel: sourceLabel } = useDict('file_source')

function formatSize(bytes: number) {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function sourceOf(file: FileRecord) {
  return { label: sourceLabel(file.source), type: sourceType[file.source] ?? 'info' }
}

function doUpload() {
  // 通过隐藏 input 选取文件（多个），选完不立即上传，弹窗确认后再传
  fileInput.value?.click()
}

const fileInput = ref<HTMLInputElement | null>(null)

async function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  if (!files.length) return
  pendingFiles.value = files
  remark.value = ''
  uploadDialogVisible.value = true
}

async function confirmUpload() {
  const r = remark.value.trim()
  const total = pendingFiles.value.length
  uploading.value = true
  try {
    let ok = 0
    for (const f of pendingFiles.value) {
      try {
        await fileApi.upload(f, 'manual', r)
        ok += 1
      } catch {
        /* 单文件失败继续（拦截器已提示） */
      }
    }
    pendingFiles.value = []
    remark.value = ''
    uploadDialogVisible.value = false
    if (ok > 0) {
      ElMessage.success(total === ok ? `成功上传 ${ok} 个文件` : `上传完成：${ok}/${total} 成功`)
      tableRef.value?.refresh()
    }
  } finally {
    uploading.value = false
  }
}

// ---------- 复制 URL / 删除 ----------
async function copyUrl(row: FileRecord) {
  try {
    await navigator.clipboard.writeText(row.url)
    ElMessage.success('URL 已复制，可粘贴到头像/其他表单使用')
  } catch {
    ElMessage.warning('复制失败，请手动复制：' + row.url)
  }
}

async function remove(row: FileRecord) {
  await ElMessageBox.confirm(
    `确定删除「${row.name}」吗？文件记录与磁盘文件将一并删除，不可恢复。`,
    '删除确认',
    { confirmButtonText: '删除', cancelButtonText: '取消', confirmButtonType: 'danger', type: 'warning' },
  )
  try {
    await fileApi.remove(row.id)
    ElMessage.success('删除成功')
    tableRef.value?.refresh()
  } catch (e: any) {
    if (e === 'cancel' || e === 'close') return
  }
}

// ---------- 表格 ----------
const columns: ColumnConfig[] = [
  { prop: 'url', label: '预览', width: 70, slot: 'thumb' },
  { prop: 'name', label: '文件名', minWidth: 180 },
  { prop: 'url', label: '路径', minWidth: 220, slot: 'url' },
  {
    prop: 'size',
    label: '大小',
    width: 90,
    formatter: (_r, v) => formatSize(v),
  },
  { prop: 'mime_type', label: '类型', width: 110, slot: 'type' },
  { prop: 'source', label: '来源', width: 90, slot: 'source' },
  { prop: 'remark', label: '备注', minWidth: 120 },
  { prop: 'created_by_name', label: '上传人', width: 100 },
  {
    prop: 'created_at',
    label: '上传时间',
    minWidth: 150,
    formatter: (_r, v) => (v ? new Date(v).toLocaleString() : '-'),
  },
  { prop: 'op', label: '操作', width: 170, slot: 'op' },
]
</script>

<template>
  <div class="page-container">
    <el-card shadow="never" class="upload-card">
      <div class="upload-row">
        <input
          ref="fileInput"
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.gif,.webp,.svg,.pdf,.doc,.docx,.xls,.xlsx"
          style="display: none"
          @change="onPick"
        />
        <el-button type="primary" @click="doUpload">选择文件上传</el-button>
      </div>
      <div class="upload-tip">支持 jpg/png/gif/webp/svg/pdf/doc/docx/xls/xlsx，单个不超过 5MB</div>
    </el-card>

    <el-dialog v-model="uploadDialogVisible" title="上传文件" width="480px">
      <el-form label-width="60px">
        <el-form-item label="备注">
          <el-input
            v-model="remark"
            placeholder="可选，如：首页轮播图"
            clearable
            :disabled="uploading"
          />
        </el-form-item>
        <el-form-item label="文件">
          <div class="pending-list">
            <div v-for="(f, i) in pendingFiles" :key="i" class="pending-item">
              <span class="pending-name">{{ f.name }}</span>
              <span class="pending-size">{{ formatSize(f.size) }}</span>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="uploading" @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="confirmUpload">
          {{ uploading ? '上传中…' : '确定上传' }}
        </el-button>
      </template>
    </el-dialog>

    <el-card shadow="never">
      <ProTable
        ref="tableRef"
        :columns="columns"
        :fetch-api="fileApi.list"
        search-placeholder="搜索文件名 / 备注"
      >
        <template #thumb="{ row }">
          <el-image
            v-if="/\.(png|jpe?g|gif|webp|svg)$/i.test(row.url)"
            :src="row.url"
            :preview-src-list="[row.url]"
            fit="cover"
            class="thumb-img"
            preview-teleported
          />
          <span v-else class="file-ico">📄</span>
        </template>
        <template #type="{ row }">
          <span class="mime">{{ (row.mime_type || row.url.split('.').pop() || '未知').slice(0, 30) }}</span>
        </template>
        <template #url="{ row }">
          <el-tooltip :content="row.url" placement="top">
            <span class="path-cell">{{ row.url }}</span>
          </el-tooltip>
        </template>
        <template #source="{ row }">
          <el-tag :type="sourceOf(row).type" size="small">{{ sourceOf(row).label }}</el-tag>
        </template>
        <template #op="{ row }">
          <el-button link type="primary" size="small" @click="copyUrl(row)">复制 URL</el-button>
          <el-button
            v-if="canDelete"
            link
            type="danger"
            size="small"
            @click="remove(row)"
          >
            删除
          </el-button>
        </template>
      </ProTable>
    </el-card>
  </div>
</template>

<style scoped>
.upload-card {
  margin-bottom: 16px;
}
.upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.upload-tip {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.pending-list {
  max-height: 220px;
  overflow-y: auto;
  width: 100%;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  padding: 4px 8px;
}
.pending-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px dashed var(--el-border-color-lighter);
}
.pending-item:last-child {
  border-bottom: none;
}
.pending-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pending-size {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  flex-shrink: 0;
  margin-left: 12px;
}
.path-cell {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}
.thumb-img {
  width: 44px;
  height: 44px;
  border-radius: 4px;
  display: block;
}
.file-ico {
  font-size: 22px;
  line-height: 44px;
}
.mime {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  word-break: break-all;
}
</style>
