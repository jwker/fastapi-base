<script setup lang="ts">
/**
 * 递归菜单节点组：支持任意层级。
 * 只输出 el-sub-menu / el-menu-item（el-menu 不可嵌套，由 SidebarMenu 提供根 el-menu）。
 * 通过文件名自引用实现递归（Vue 3.3+）。
 */
import { useRouter } from 'vue-router'
import type { MenuItem } from '@/types'

defineProps<{ menus: MenuItem[] }>()

const router = useRouter()
</script>

<template>
  <template v-for="menu in menus" :key="menu.id">
    <el-sub-menu v-if="menu.children && menu.children.length" :index="menu.path">
      <template #title>
        <el-icon><component :is="menu.icon || 'Menu'" /></el-icon>
        <span>{{ menu.name }}</span>
      </template>
      <!-- 任意层级递归 -->
      <MenuNodes :menus="menu.children" />
    </el-sub-menu>

    <el-menu-item v-else :index="menu.path" @click="router.push(menu.path)">
      <el-icon><component :is="menu.icon || 'Menu'" /></el-icon>
      <template #title>{{ menu.name }}</template>
    </el-menu-item>
  </template>
</template>
