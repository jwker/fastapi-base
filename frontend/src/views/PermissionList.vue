<script setup lang="ts">
defineOptions({ name: 'PermissionList' })
import ProTable, { type ColumnConfig } from '@/components/ProTable.vue'
import { permissionApi } from '@/api'

const columns: ColumnConfig[] = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'name', label: '权限名称', minWidth: 120 },
  { prop: 'code', label: '权限编码', minWidth: 160 },
  { prop: 'resource', label: '资源', width: 100 },
  { prop: 'action', label: '操作', width: 100 },
  { prop: 'description', label: '描述', minWidth: 140 },
]
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <ProTable
        :columns="columns"
        :fetch-api="permissionApi.list"
        search-placeholder="搜索权限名称 / 编码 / 资源"
        :show-search="true"
      />
    </el-card>
  </div>
</template>
