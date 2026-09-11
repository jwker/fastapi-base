<script setup lang="ts">
import { useRoute } from 'vue-router'
import type { MenuItem } from '@/types'
import MenuNodes from './MenuNodes.vue'

defineProps<{ menus: MenuItem[]; collapsed: boolean }>()

const route = useRoute()
</script>

<template>
  <el-menu
    :default-active="route.path"
    :collapse="collapsed"
    :collapse-transition="false"
    background-color="transparent"
  >
    <!-- 任意层级由 MenuNodes 递归渲染 -->
    <MenuNodes :menus="menus" />
  </el-menu>
</template>
