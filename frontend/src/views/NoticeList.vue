<script setup lang="ts">
defineOptions({ name: 'NoticeList' })
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ProTable, { type ActionConfig, type ColumnConfig } from '@/components/ProTable.vue'
import ProForm, { type ProFormField } from '@/components/ProForm.vue'
import { announcementApi } from '@/api'

const tableRef = ref<InstanceType<typeof ProTable>>()

const typeLabel: Record<string, string> = { notice: '通知', announcement: '公告' }
const statusLabel: Record<number, { text: string; tag: string }> = {
  0: { text: '草稿', tag: 'info' },
  1: { text: '已发布', tag: 'success' },
  2: { text: '已下线', tag: 'warning' },
}

const columns: ColumnConfig[] = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'title', label: '标题', minWidth: 180 },
  {
    prop: 'type',
    label: '类型',
    width: 90,
    formatter: (row: any) => typeLabel[row.type] ?? row.type,
  },
  {
    prop: 'status',
    label: '状态',
    width: 90,
    slot: 'status',
  },
  {
    prop: 'is_top',
    label: '置顶',
    width: 80,
    formatter: (row: any) => (row.is_top ? '置顶' : ''),
  },
  { prop: 'publish_time', label: '发布时间', width: 170 },
  { prop: 'expire_time', label: '过期时间', width: 170 },
  { prop: 'created_by_name', label: '发布人', width: 100 },
]

const actions: ActionConfig[] = [
  {
    label: '编辑',
    permission: 'announce:write',
    onClick: (row: any) => openDialog(row),
  },
  {
    label: '发布',
    type: 'success',
    permission: 'announce:write',
    show: (row: any) => row.status !== 1,
    confirm: '确定发布该公告？发布后用户端立即可见',
    onClick: async (row: any) => {
      await announcementApi.publish(row.id)
      ElMessage.success('发布成功')
      tableRef.value?.refresh()
    },
  },
  {
    label: '下线',
    type: 'warning',
    permission: 'announce:write',
    show: (row: any) => row.status === 1,
    confirm: '确定下线该公告？下线后用户端不再显示',
    onClick: async (row: any) => {
      await announcementApi.offline(row.id)
      ElMessage.success('已下线')
      tableRef.value?.refresh()
    },
  },
  {
    label: '删除',
    type: 'danger',
    permission: 'announce:write',
    confirm: '确定删除该公告？',
    onClick: async (row: any) => {
      await announcementApi.remove(row.id)
      ElMessage.success('删除成功')
    },
  },
]

// ---------- 公告表单 ----------
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({
  title: '',
  content: '',
  type: 'notice',
  is_top: false,
  expire_time: null as string | null,
})

const fields: ProFormField[] = [
  { prop: 'title', label: '标题', required: true, placeholder: '公告标题' },
  {
    prop: 'type',
    label: '类型',
    type: 'select',
    options: [
      { label: '通知', value: 'notice' },
      { label: '公告', value: 'announcement' },
    ],
  },
  { prop: 'content', label: '正文', type: 'textarea', rows: 4, required: true, placeholder: '公告正文（纯文本）' },
  { prop: 'is_top', label: '置顶', type: 'switch', activeText: '置顶优先展示' },
  { prop: 'expire_time', label: '过期时间', type: 'slot', slot: 'expireTime' },
]

function openDialog(row?: any) {
  if (row) {
    editingId.value = row.id
    Object.assign(form, {
      title: row.title,
      content: row.content,
      type: row.type,
      is_top: row.is_top,
      expire_time: row.expire_time,
    })
  } else {
    editingId.value = null
    Object.assign(form, { title: '', content: '', type: 'notice', is_top: false, expire_time: null })
  }
  dialogVisible.value = true
}

async function submitForm() {
  saving.value = true
  try {
    if (editingId.value) {
      await announcementApi.update(editingId.value, { ...form })
      ElMessage.success('更新成功')
    } else {
      await announcementApi.create({ ...form })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    tableRef.value?.refresh()
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <ProTable
        ref="tableRef"
        row-key="id"
        :columns="columns"
        :actions="actions"
        :fetch-api="(p: any) => announcementApi.list(p)"
        search-placeholder="搜索公告标题 / 正文"
        create-label="新增公告"
        create-permission="announce:write"
        :on-create="() => openDialog()"
      >
        <template #status="{ row }">
          <el-tag :type="(statusLabel[row.status]?.tag as any) || 'info'" size="small">
            {{ statusLabel[row.status]?.text ?? row.status }}
          </el-tag>
        </template>
      </ProTable>
    </el-card>

    <!-- 新增/编辑（ProForm） -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑公告' : '新增公告'" width="560px">
      <ProForm
        v-model="form"
        :fields="fields"
        :mode="editingId ? 'edit' : 'create'"
        :submit-loading="saving"
        @submit="submitForm"
        @cancel="dialogVisible = false"
      >
        <template #expireTime>
          <el-date-picker
            v-model="form.expire_time"
            type="datetime"
            placeholder="留空 = 永不过期"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </template>
      </ProForm>
    </el-dialog>
  </div>
</template>
