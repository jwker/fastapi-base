<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ProTable, { type ActionConfig, type ColumnConfig } from '@/components/ProTable.vue'
import { roleApi, userApi } from '@/api'
import type { RoleRecord } from '@/types'

const tableRef = ref<InstanceType<typeof ProTable>>()

const columns: ColumnConfig[] = [
  { prop: 'id', label: 'ID', width: 70 },
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

// 弹窗表单
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  username: '',
  nickname: '',
  email: '',
  phone: '',
  password: '',
  status: 1,
  role_ids: [] as number[],
})

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
    })
  }
  dialogVisible.value = true
}

async function submit() {
  if (!form.username || (!editingId.value && !form.password)) {
    ElMessage.warning('用户名和密码必填')
    return
  }
  const payload: Record<string, unknown> = {
    nickname: form.nickname,
    email: form.email,
    phone: form.phone,
    status: form.status,
    role_ids: form.role_ids,
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

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑用户' : '新增用户'" width="480px">      <el-form label-width="70px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="!!editingId" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_ids" multiple clearable placeholder="选择角色（可多选）" style="width: 100%">
            <el-option
              v-for="role in roleOptions"
              :key="role.id"
              :label="`${role.name}（${role.code}）`"
              :value="role.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="密码" :required="!editingId">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editingId ? '留空则不修改' : '至少 6 位'"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="form.status"
            :active-value="1"
            :inactive-value="0"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.no-role {
  color: var(--fb-text-secondary);
  font-size: 12px;
}
</style>
