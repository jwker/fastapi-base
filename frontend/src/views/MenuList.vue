<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ProForm, { type ProFormField } from '@/components/ProForm.vue'
import { menuApi } from '@/api'
import type { MenuItem } from '@/types'

const loading = ref(false)
const rawTree = ref<MenuItem[]>([])
const keyword = ref('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const parentOptions = ref<{ id: number; label: string }[]>([])

const form = reactive({
  parent_id: null as number | null,
  name: '',
  path: '',
  component: '',
  icon: '',
  sort_order: 0,
  is_visible: true,
  permission_code: '',
})

// 菜单弹窗字段（ProForm 配置驱动）
const menuFields = computed<ProFormField[]>(() => [
  {
    prop: 'parent_id',
    label: '父级菜单',
    type: 'select',
    placeholder: '不选则为顶级菜单',
    // 编辑时禁选自己，避免菜单成为自己的父级
    options: parentOptions.value.map((o) => ({
      label: o.label,
      value: o.id,
      disabled: o.id === editingId.value,
    })),
  },
  { prop: 'name', label: '菜单名称', required: true },
  { prop: 'path', label: '路由路径', required: true, placeholder: '/users' },
  { prop: 'component', label: '组件', placeholder: 'UserList / Layout' },
  { prop: 'icon', label: '图标', placeholder: 'Element Plus 图标名，如 User' },
  { prop: 'sort_order', label: '排序', type: 'number', min: 0 },
  { prop: 'is_visible', label: '可见', type: 'switch' },
  { prop: 'permission_code', label: '权限码', placeholder: '如 user:read，留空则登录可见' },
])

const tree = computed(() => {
  const kw = keyword.value.trim()
  if (!kw) return rawTree.value
  const filter = (nodes: MenuItem[]): MenuItem[] =>
    nodes
      .map((n) => ({ ...n, children: n.children ? filter(n.children) : [] }))
      .filter((n) => n.name.includes(kw) || (n.children?.length ?? 0) > 0)
  return filter(rawTree.value)
})

async function loadTree() {
  loading.value = true
  try {
    const res = await menuApi.tree()
    rawTree.value = res.data
  } finally {
    loading.value = false
  }
}

function flatten(nodes: MenuItem[]): { id: number; label: string }[] {
  const result: { id: number; label: string }[] = []
  const walk = (list: MenuItem[], depth: number) => {
    for (const n of list) {
      result.push({ id: n.id, label: `${'　'.repeat(depth)}${n.name}` })
      if (n.children?.length) walk(n.children, depth + 1)
    }
  }
  walk(nodes, 0)
  return result
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    parent_id: null,
    name: '',
    path: '',
    component: '',
    icon: '',
    sort_order: 0,
    is_visible: true,
    permission_code: '',
  })
  parentOptions.value = flatten(rawTree.value)
  dialogVisible.value = true
}

function openEdit(row: MenuItem) {
  editingId.value = row.id
  Object.assign(form, {
    parent_id: row.parent_id,
    name: row.name,
    path: row.path,
    component: row.component,
    icon: row.icon,
    sort_order: row.sort_order,
    is_visible: row.is_visible,
    permission_code: row.permission_code ?? '',
  })
  parentOptions.value = flatten(rawTree.value)
  dialogVisible.value = true
}

async function submit() {
  saving.value = true
  try {
    const payload = {
      ...form,
      parent_id: form.parent_id,
      permission_code: form.permission_code || null,
    }
    if (editingId.value) {
      await menuApi.update(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await menuApi.create(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadTree()
  } finally {
    saving.value = false
  }
}

async function remove(row: MenuItem) {
  try {
    await ElMessageBox.confirm(`确定删除菜单「${row.name}」？其子菜单将一并删除。`, '提示', {
      type: 'warning',
    })
  } catch {
    return
  }
  await menuApi.remove(row.id)
  ElMessage.success('删除成功')
  loadTree()
}

onMounted(loadTree)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input v-model="keyword" placeholder="搜索菜单名称" clearable style="width: 240px">
            <template #prefix
              ><el-icon><Search /></el-icon
            ></template>
          </el-input>
        </div>
        <div class="toolbar-right">
          <el-button v-permission="'menu:create'" type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon>新增菜单
          </el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="tree"
        row-key="id"
        border
        default-expand-all
        :tree-props="{ children: 'children' }"
      >
        <el-table-column prop="name" label="菜单名称" min-width="180" />
        <el-table-column prop="path" label="路由路径" min-width="140" />
        <el-table-column prop="component" label="组件" min-width="120" />
        <el-table-column prop="icon" label="图标" width="90" />
        <el-table-column prop="sort_order" label="排序" width="70" />
        <el-table-column prop="permission_code" label="权限码" min-width="120">
          <template #default="{ row }">
            <el-tag v-if="row.permission_code" size="small">{{ row.permission_code }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button
              v-permission="'menu:update'"
              link
              type="primary"
              size="small"
              @click="openEdit(row)"
              >编辑</el-button
            >
            <el-button
              v-permission="'menu:delete'"
              link
              type="danger"
              size="small"
              @click="remove(row)"
              >删除</el-button
            >
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 菜单新增/编辑弹窗（ProForm：字段配置驱动 + 防线校验 + footer） -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑菜单' : '新增菜单'" width="520px">
      <ProForm
        v-model="form"
        :fields="menuFields"
        :mode="editingId ? 'edit' : 'create'"
        :submit-loading="saving"
        label-width="90px"
        @submit="submit"
        @cancel="dialogVisible = false"
      />
    </el-dialog>
  </div>
</template>
