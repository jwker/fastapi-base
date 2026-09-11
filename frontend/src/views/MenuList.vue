<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { menuApi } from '@/api'
import type { MenuItem } from '@/types'

const loading = ref(false)
const rawTree = ref<MenuItem[]>([])
const keyword = ref('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
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
  if (!form.name || !form.path) {
    ElMessage.warning('名称和路径必填')
    return
  }
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

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑菜单' : '新增菜单'" width="520px">
      <el-form label-width="90px">
        <el-form-item label="父级菜单">
          <el-select
            v-model="form.parent_id"
            clearable
            placeholder="不选则为顶级菜单"
            style="width: 100%"
          >
            <el-option
              v-for="opt in parentOptions"
              :key="opt.id"
              :label="opt.label"
              :value="opt.id"
              :disabled="opt.id === editingId"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="菜单名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="路由路径" required>
          <el-input v-model="form.path" placeholder="/users" />
        </el-form-item>
        <el-form-item label="组件">
          <el-input v-model="form.component" placeholder="UserList / Layout" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="Element Plus 图标名，如 User" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="可见">
          <el-switch v-model="form.is_visible" />
        </el-form-item>
        <el-form-item label="权限码">
          <el-input v-model="form.permission_code" placeholder="如 user:read，留空则登录可见" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
