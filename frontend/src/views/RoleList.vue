<script setup lang="ts">
defineOptions({ name: 'RoleList' })
import { nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ProTable, { type ActionConfig, type ColumnConfig } from '@/components/ProTable.vue'
import ProForm, { type ProFormField } from '@/components/ProForm.vue'
import { menuApi, permissionApi, roleApi } from '@/api'
import { useDict } from '@/composables/useDict'
import type { MenuItem, PermissionRecord, RoleRecord } from '@/types'

const tableRef = ref<InstanceType<typeof ProTable>>()
// 状态文案从字典取（sys_status）
const { getLabel: statusLabel } = useDict('sys_status')

const columns: ColumnConfig[] = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'name', label: '角色名称', minWidth: 120 },
  { prop: 'code', label: '编码', minWidth: 120 },
  { prop: 'description', label: '描述', minWidth: 160 },
  {
    prop: 'status',
    label: '状态',
    width: 90,
    slot: 'status',
  },
]

const actions: ActionConfig[] = [
  {
    label: '权限',
    permission: 'role:update',
    onClick: (row) => openPermissionDialog(row),
  },
  {
    label: '菜单',
    permission: 'role:update',
    onClick: (row) => openMenuDialog(row),
  },
  {
    label: '编辑',
    permission: 'role:update',
    onClick: (row) => openDialog(row),
  },
  {
    label: '删除',
    type: 'danger',
    permission: 'role:delete',
    confirm: '确定删除该角色？',
    show: (row) => !['super_admin', 'admin', 'user'].includes(row.code),
    onClick: async (row) => {
      await roleApi.remove(row.id)
    },
  },
]

// 基础表单（ProForm 配置驱动：校验防线/模式感知/回填由组件处理）
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({ name: '', code: '', description: '' })

const roleFields: ProFormField[] = [
  { prop: 'name', label: '角色名称', required: true },
  {
    prop: 'code',
    label: '编码',
    required: true,
    placeholder: '如 auditor',
    // 编辑模式编码不可改（与业务标识一致性）
    disabled: () => !!editingId.value,
  },
  { prop: 'description', label: '描述', type: 'textarea', rows: 2 },
]

function openDialog(row?: any) {
  if (row) {
    editingId.value = row.id
    Object.assign(form, { name: row.name, code: row.code, description: row.description })
  } else {
    editingId.value = null
    Object.assign(form, { name: '', code: '', description: '' })
  }
  dialogVisible.value = true
}

async function submit() {
  saving.value = true
  try {
    if (editingId.value) {
      await roleApi.update(editingId.value, { ...form })
      ElMessage.success('更新成功')
    } else {
      await roleApi.create({ ...form })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    tableRef.value?.refresh()
  } finally {
    saving.value = false
  }
}

// 权限分配
const permDialogVisible = ref(false)
const permRole = ref<RoleRecord | null>(null)
const permSelected = ref<number[]>([])
const allPermissions = ref<PermissionRecord[]>([])

async function openPermissionDialog(row: any) {
  permRole.value = row
  permSelected.value = [...row.permission_ids]
  if (!allPermissions.value.length) {
    const res = await permissionApi.list({ page_size: 200 })
    allPermissions.value = res.data.items
  }
  permDialogVisible.value = true
}

async function submitPermissions() {
  await roleApi.assignPermissions(permRole.value!.id, permSelected.value)
  ElMessage.success('权限分配成功')
  permDialogVisible.value = false
  tableRef.value?.refresh()
}

// 菜单分配
const menuDialogVisible = ref(false)
const menuRole = ref<RoleRecord | null>(null)
const menuSelected = ref<number[]>([])
const menuTree = ref<MenuItem[]>([])
const menuTreeRef = ref()

async function openMenuDialog(row: any) {
  menuRole.value = row
  menuSelected.value = [...(row.menu_ids ?? [])]
  const res = await menuApi.tree()
  menuTree.value = res.data
  menuDialogVisible.value = true
  // 数据与勾选状态就绪后回显：只勾叶子节点，父节点由联动自动半选
  await nextTick()
  const leafIds = new Set<number>()
  const collect = (nodes: MenuItem[]) => {
    for (const n of nodes) {
      if (n.children && n.children.length) collect(n.children)
      else leafIds.add(n.id)
    }
  }
  collect(menuTree.value)
  menuTreeRef.value?.setCheckedKeys(menuSelected.value.filter((id) => leafIds.has(id)))
}

async function submitMenus() {
  const checked: number[] = []
  const walk = (nodes: MenuItem[]) => {
    for (const n of nodes) {
      checked.push(n.id)
      if (n.children?.length) walk(n.children)
    }
  }
  walk(menuTree.value)
  // el-tree 只给叶子/选中节点，这里用 getCheckedKeys + 半选
  const checkedKeys = (menuTreeRef.value?.getCheckedKeys() ?? []) as number[]
  const halfKeys = (menuTreeRef.value?.getHalfCheckedKeys() ?? []) as number[]
  await roleApi.assignMenus(menuRole.value!.id, [...checkedKeys, ...halfKeys])
  ElMessage.success('菜单分配成功')
  menuDialogVisible.value = false
  tableRef.value?.refresh()
}

onMounted(() => {
  /* 空实现：数据由 ProTable 拉取 */
})
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <ProTable
        ref="tableRef"
        :columns="columns"
        :fetch-api="roleApi.list"
        :actions="actions"
        create-label="新增角色"
        create-permission="role:create"
        search-placeholder="搜索角色名称 / 编码"
        :on-create="() => openDialog()"
      >
        <template #status="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'">{{
            statusLabel(row.status)
          }}</el-tag>
        </template>
      </ProTable>
    </el-card>

    <!-- 角色基础表单（ProForm：字段配置驱动 + 防线校验 + 取消/确定 footer） -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑角色' : '新增角色'" width="460px">
      <ProForm
        v-model="form"
        :fields="roleFields"
        :mode="editingId ? 'edit' : 'create'"
        :submit-loading="saving"
        @submit="submit"
        @cancel="dialogVisible = false"
      />
    </el-dialog>

    <!-- 权限分配 -->
    <el-dialog v-model="permDialogVisible" :title="`分配权限 - ${permRole?.name}`" width="560px">
      <el-checkbox-group v-model="permSelected" class="perm-group">
        <el-checkbox v-for="p in allPermissions" :key="p.id" :value="p.id" class="perm-item">
          {{ p.name }} <span class="perm-code">{{ p.code }}</span>
        </el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="permDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPermissions">保存</el-button>
      </template>
    </el-dialog>

    <!-- 菜单分配 -->
    <el-dialog v-model="menuDialogVisible" :title="`分配菜单 - ${menuRole?.name}`" width="480px">
      <el-tree
        ref="menuTreeRef"
        :data="menuTree"
        show-checkbox
        node-key="id"
        :props="{ label: 'name', children: 'children' }"
        default-expand-all
      />
      <template #footer>
        <el-button @click="menuDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitMenus">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.perm-group {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.perm-item {
  width: 200px;
  margin-right: 0 !important;
}

.perm-code {
  color: var(--fb-text-secondary);
  font-size: 12px;
  margin-left: 4px;
}
</style>
