<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ProTable, { type ActionConfig, type ColumnConfig } from '@/components/ProTable.vue'
import ProForm, { type ProFormField } from '@/components/ProForm.vue'
import FileUpload from '@/components/FileUpload.vue'
import { roleApi, userApi } from '@/api'
import type { RoleRecord } from '@/types'

const tableRef = ref<InstanceType<typeof ProTable>>()

const columns: ColumnConfig[] = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'avatar', label: '头像', width: 70, slot: 'avatar' },
  { prop: 'username', label: '用户名', minWidth: 120 },
  { prop: 'nickname', label: '昵称', minWidth: 120 },
  { prop: 'email', label: '邮箱', minWidth: 160 },
  {
    prop: 'status',
    label: '状态',
    width: 90,
    slot: 'status',
  },
  {
    prop: 'role_ids',
    label: '角色',
    minWidth: 140,
    slot: 'roles',
  },
  {
    prop: 'created_at',
    label: '创建时间',
    minWidth: 160,
    formatter: (_r, v) => (v ? new Date(v).toLocaleString() : '-'),
  },
]

const actions: ActionConfig[] = [
  {
    label: '编辑',
    permission: 'user:update',
    onClick: (row) => openDialog(row),
  },
  {
    label: '删除',
    type: 'danger',
    permission: 'user:delete',
    confirm: '确定删除该用户？',
    show: (row) => !row.is_superuser,
    onClick: async (row) => {
      await userApi.remove(row.id)
    },
  },
]

// 角色选项（编辑/创建弹窗用）
const roleOptions = ref<RoleRecord[]>([])
function roleName(id: number) {
  return roleOptions.value.find((r) => r.id === id)?.name ?? `#${id}`
}
async function loadRoles() {
  const res = await roleApi.list({ page: 1, page_size: 100 })
  roleOptions.value = res.data.items
}

// 弹窗表单（ProForm 配置驱动：防线校验/模式感知/回填由组件处理）
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({
  username: '',
  nickname: '',
  email: '',
  phone: '',
  password: '',
  status: 1,
  role_ids: [] as number[],
  avatar: '',
})

const userFields = computed<ProFormField[]>(() => [
  {
    prop: 'username',
    label: '用户名',
    required: true,
    placeholder: '登录用户名',
    disabled: () => !!editingId.value,
  },
  { prop: 'nickname', label: '昵称' },
  { prop: 'email', label: '邮箱' },
  { prop: 'phone', label: '手机号' },
  { prop: 'avatar', label: '头像', type: 'slot' },
  {
    prop: 'role_ids',
    label: '角色',
    type: 'select',
    multiple: true,
    placeholder: '选择角色（可多选）',
    options: roleOptions.value.map((r) => ({ label: `${r.name}（${r.code}）`, value: r.id })),
  },
  {
    prop: 'password',
    label: '密码',
    type: 'input',
    inputType: 'password',
    // 两种模式都显示，但仅新增必填
    required: (m) => m === 'create',
    placeholder: (m) => (m === 'create' ? '至少 6 位' : '留空则不修改'),
  },
  {
    prop: 'status',
    label: '状态',
    type: 'switch',
    activeValue: 1,
    inactiveValue: 0,
    activeText: '启用',
    inactiveText: '禁用',
  },
])

function openDialog(row?: any) {
  if (row) {
    editingId.value = row.id
    Object.assign(form, {
      username: row.username,
      nickname: row.nickname,
      email: row.email,
      phone: row.phone,
      password: '',
      status: row.status,
      role_ids: [...(row.role_ids ?? [])],
      avatar: row.avatar || '',
    })
  } else {
    editingId.value = null
    Object.assign(form, {
      username: '',
      nickname: '',
      email: '',
      phone: '',
      password: '',
      status: 1,
      role_ids: [],
      avatar: '',
    })
  }
  dialogVisible.value = true
}

async function submit() {
  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      nickname: form.nickname,
      email: form.email,
      phone: form.phone,
      status: form.status,
      role_ids: form.role_ids,
      avatar: form.avatar,
    }
    if (form.password) payload.password = form.password
    if (editingId.value) {
      await userApi.update(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await userApi.create({ ...payload, username: form.username, password: form.password })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    tableRef.value?.refresh()
  } finally {
    saving.value = false
  }
}

onMounted(loadRoles)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <ProTable
        ref="tableRef"
        :columns="columns"
        :fetch-api="userApi.list"
        :actions="actions"
        create-label="新增用户"
        create-permission="user:create"
        search-placeholder="搜索用户名 / 昵称"
        :on-create="() => openDialog()"
      >
        <template #avatar="{ row }">
          <el-avatar :size="30" :src="row.avatar || undefined">{{ (row.nickname || row.username || '?').slice(0, 1) }}</el-avatar>
        </template>
        <template #status="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'">{{
            row.status === 1 ? '启用' : '禁用'
          }}</el-tag>
        </template>
        <template #roles="{ row }">
          <template v-if="row.role_ids && row.role_ids.length">
            <el-tag v-for="rid in row.role_ids" :key="rid" size="small" style="margin-right: 4px">
              {{ roleName(rid) }}
            </el-tag>
          </template>
          <span v-else class="no-role">未分配</span>
        </template>
      </ProTable>
    </el-card>

    <!-- 用户新增/编辑弹窗（ProForm：字段配置驱动 + 防线校验 + 插槽头像 + footer） -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑用户' : '新增用户'" width="480px">
      <ProForm
        v-model="form"
        :fields="userFields"
        :mode="editingId ? 'edit' : 'create'"
        :submit-loading="saving"
        @submit="submit"
        @cancel="dialogVisible = false"
      >
        <template #avatar="{ model }">
          <FileUpload
            v-model="model.avatar"
            accept=".jpg,.jpeg,.png,.gif,.webp,.svg"
            :max-size-mb="5"
            source="avatar"
            tip="支持 jpg/png/gif/webp/svg，不超过 5MB"
          />
        </template>
      </ProForm>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.no-role {
  color: var(--fb-text-secondary);
  font-size: 12px;
}
</style>
