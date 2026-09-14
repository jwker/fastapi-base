<script setup lang="ts">
defineOptions({ name: 'DictList' })
import { reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ProTable, { type ActionConfig, type ColumnConfig } from '@/components/ProTable.vue'
import ProForm, { type ProFormField } from '@/components/ProForm.vue'
import { clearDictCache } from '@/composables/useDict'
import { dictApi } from '@/api'
import type { DictItemRecord, DictTypeRecord } from '@/types'

const tableRef = ref<InstanceType<typeof ProTable>>()

const columns: ColumnConfig[] = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'name', label: '字典名称', minWidth: 130 },
  { prop: 'type', label: '编码', minWidth: 130 },
  { prop: 'item_count', label: '项数', width: 70 },
  { prop: 'remark', label: '备注', minWidth: 160 },
  { prop: 'created_at', label: '创建时间', width: 170 },
]

const actions: ActionConfig[] = [
  {
    label: '数据',
    onClick: (row: any) => openItemDialog(row),
  },
  {
    label: '编辑',
    permission: 'dict:write',
    onClick: (row: any) => openDialog(row),
  },
  {
    label: '删除',
    type: 'danger',
    permission: 'dict:write',
    confirm: '确定删除该字典类型？其下所有字典项将一并删除。',
    onClick: async (row: any) => {
      await dictApi.removeType(row.id)
      // 类型删除后清空全局字典缓存，业务页下次取用重新拉取
      clearDictCache()
    },
  },
]

// ---------- 字典类型表单 ----------
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({ name: '', type: '', remark: '' })

const typeFields: ProFormField[] = [
  { prop: 'name', label: '字典名称', required: true, placeholder: '如 文件来源' },
  {
    prop: 'type',
    label: '类型编码',
    required: true,
    placeholder: '如 file_source（小写字母/数字/下划线）',
  },
  { prop: 'remark', label: '备注', type: 'textarea', rows: 2 },
]

function openDialog(row?: any) {
  if (row) {
    editingId.value = row.id
    Object.assign(form, { name: row.name, type: row.type, remark: row.remark })
  } else {
    editingId.value = null
    Object.assign(form, { name: '', type: '', remark: '' })
  }
  dialogVisible.value = true
}

async function submitType() {
  saving.value = true
  try {
    if (editingId.value) {
      await dictApi.updateType(editingId.value, { ...form })
      ElMessage.success('更新成功')
    } else {
      await dictApi.createType({ ...form })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    tableRef.value?.refresh()
  } finally {
    saving.value = false
  }
}

// ---------- 字典项管理 ----------
const itemDialogVisible = ref(false)
const currentType = ref<DictTypeRecord | null>(null)
const itemList = ref<DictItemRecord[]>([])
const itemLoading = ref(false)

// 项编辑弹窗
const itemFormVisible = ref(false)
const itemEditingId = ref<number | null>(null)
const itemSaving = ref(false)
const itemForm = reactive({ label: '', value: '', sort: 0, status: 1 })

const itemFields: ProFormField[] = [
  { prop: 'label', label: '显示文案', required: true, placeholder: '如 头像' },
  { prop: 'value', label: '存储值', required: true, placeholder: '如 avatar' },
  { prop: 'sort', label: '排序', type: 'number', min: 0 },
  {
    prop: 'status',
    label: '启用',
    type: 'switch',
    activeValue: 1,
    inactiveValue: 0,
    activeText: '启用',
    inactiveText: '禁用',
  },
]

async function openItemDialog(row: DictTypeRecord) {
  currentType.value = row
  itemDialogVisible.value = true
  await loadItems(row.id)
}

async function loadItems(typeId: number) {
  itemLoading.value = true
  try {
    const res = await dictApi.items(typeId)
    itemList.value = res.data
  } finally {
    itemLoading.value = false
  }
}

function openItemForm(item?: DictItemRecord) {
  if (item) {
    itemEditingId.value = item.id
    Object.assign(itemForm, { label: item.label, value: item.value, sort: item.sort, status: item.status })
  } else {
    itemEditingId.value = null
    Object.assign(itemForm, { label: '', value: '', sort: 0, status: 1 })
  }
  itemFormVisible.value = true
}

async function submitItem() {
  itemSaving.value = true
  try {
    if (itemEditingId.value) {
      await dictApi.updateItem(itemEditingId.value, { ...itemForm })
      ElMessage.success('更新成功')
    } else {
      await dictApi.createItem(currentType.value!.id, { ...itemForm })
      ElMessage.success('创建成功')
    }
    itemFormVisible.value = false
    await loadItems(currentType.value!.id)
    // 改动字典项后清缓存，业务页下次取用看到新文案
    clearDictCache()
  } finally {
    itemSaving.value = false
  }
}

async function removeItem(item: DictItemRecord) {
  try {
    await ElMessageBox.confirm(`确定删除字典项「${item.label}」？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  await dictApi.removeItem(item.id)
  ElMessage.success('删除成功')
  await loadItems(currentType.value!.id)
  clearDictCache()
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
        :fetch-api="(p: any) => dictApi.types(p)"
        search-placeholder="搜索字典名称 / 编码"
        create-label="新增字典"
        create-permission="dict:write"
        :on-create="() => openDialog()"
      />
    </el-card>

    <!-- 字典类型新增/编辑（ProForm） -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑字典类型' : '新增字典类型'" width="480px">
      <ProForm
        v-model="form"
        :fields="typeFields"
        :mode="editingId ? 'edit' : 'create'"
        :submit-loading="saving"
        @submit="submitType"
        @cancel="dialogVisible = false"
      />
    </el-dialog>

    <!-- 字典项管理 -->
    <el-dialog v-model="itemDialogVisible" :title="`字典数据 - ${currentType?.name ?? ''}（${currentType?.type ?? ''}）`" width="640px">
      <div class="item-toolbar">
        <el-button v-permission="'dict:write'" type="primary" size="small" @click="openItemForm()">
          新增数据
        </el-button>
      </div>
      <el-table v-loading="itemLoading" :data="itemList" border size="small">
        <el-table-column prop="label" label="显示文案" min-width="100" />
        <el-table-column prop="value" label="存储值" min-width="100" />
        <el-table-column prop="sort" label="排序" width="60" />
        <el-table-column prop="is_default" label="默认" width="70">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" size="small" type="success">默认</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">{{
              row.status === 1 ? '启用' : '禁用'
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="120" />
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button v-permission="'dict:write'" link type="primary" size="small" @click="openItemForm(row)">
              编辑
            </el-button>
            <el-button v-permission="'dict:write'" link type="danger" size="small" @click="removeItem(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 字典项新增/编辑（ProForm） -->
    <el-dialog v-model="itemFormVisible" :title="itemEditingId ? '编辑字典数据' : '新增字典数据'" width="440px">
      <ProForm
        v-model="itemForm"
        :fields="itemFields"
        :mode="itemEditingId ? 'edit' : 'create'"
        :submit-loading="itemSaving"
        @submit="submitItem"
        @cancel="itemFormVisible = false"
      />
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.item-toolbar {
  margin-bottom: 12px;
}
</style>
