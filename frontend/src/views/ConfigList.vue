<script setup lang="ts">
defineOptions({ name: 'ConfigList' })
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ProTable, { type ActionConfig, type ColumnConfig } from '@/components/ProTable.vue'
import ProForm, { type ProFormField } from '@/components/ProForm.vue'
import { configApi } from '@/api'

const tableRef = ref<InstanceType<typeof ProTable>>()

const valueTypeLabel: Record<string, string> = {
  string: '字符串',
  int: '整数',
  bool: '布尔',
}

const columns: ColumnConfig[] = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'key', label: '配置键', minWidth: 150 },
  { prop: 'value', label: '配置值', minWidth: 160 },
  {
    prop: 'value_type',
    label: '类型',
    width: 90,
    formatter: (row: any) => valueTypeLabel[row.value_type] ?? row.value_type,
  },
  { prop: 'remark', label: '备注', minWidth: 160 },
  { prop: 'updated_at', label: '更新时间', width: 170 },
]

const actions: ActionConfig[] = [
  {
    label: '编辑',
    permission: 'config:write',
    onClick: (row: any) => openDialog(row),
  },
  {
    label: '删除',
    type: 'danger',
    permission: 'config:write',
    confirm: '确定删除该参数？',
    onClick: async (row: any) => {
      await configApi.remove(row.id)
      ElMessage.success('删除成功')
    },
  },
]

// ---------- 参数表单 ----------
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({ key: '', value: '', value_type: 'string', remark: '' })

const fields: ProFormField[] = [
  {
    prop: 'key',
    label: '配置键',
    required: true,
    placeholder: '如 site_name（小写字母/数字/下划线）',
    // 编辑模式键不可改（与业务标识一致性）
    disabled: () => !!editingId.value,
  },
  { prop: 'value', label: '配置值', required: true, placeholder: '如 FastAPI Base' },
  {
    prop: 'value_type',
    label: '类型',
    type: 'select',
    options: [
      { label: '字符串', value: 'string' },
      { label: '整数', value: 'int' },
      { label: '布尔', value: 'bool' },
    ],
  },
  { prop: 'remark', label: '备注', type: 'textarea', rows: 2 },
]

function openDialog(row?: any) {
  if (row) {
    editingId.value = row.id
    Object.assign(form, { key: row.key, value: row.value, value_type: row.value_type, remark: row.remark })
  } else {
    editingId.value = null
    Object.assign(form, { key: '', value: '', value_type: 'string', remark: '' })
  }
  dialogVisible.value = true
}

async function submitForm() {
  saving.value = true
  try {
    if (editingId.value) {
      await configApi.update(editingId.value, { value: form.value, value_type: form.value_type, remark: form.remark })
      ElMessage.success('更新成功')
    } else {
      await configApi.create({ ...form })
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
        :fetch-api="(p: any) => configApi.list(p)"
        search-placeholder="搜索配置键 / 备注"
        create-label="新增参数"
        create-permission="config:write"
        :on-create="() => openDialog()"
      />
    </el-card>

    <!-- 新增/编辑（ProForm） -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑参数' : '新增参数'" width="460px">
      <ProForm
        v-model="form"
        :fields="fields"
        :mode="editingId ? 'edit' : 'create'"
        :submit-loading="saving"
        @submit="submitForm"
        @cancel="dialogVisible = false"
      />
    </el-dialog>
  </div>
</template>
