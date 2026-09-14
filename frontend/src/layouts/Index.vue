<script setup lang="ts">
import { computed, provide, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import { usePermissionStore } from '@/stores/permission'
import { useTagsStore } from '@/stores/tags'
import SidebarMenu from './SidebarMenu.vue'
import TagsView from '@/components/TagsView.vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()
const permissionStore = usePermissionStore()
const tagsStore = useTagsStore()

// 刷新当前页：key 变化重建当前组件（keep-alive 缓存按 route.name+reloadKey 隔离）
const reloadKey = ref(0)
function reloadPage() {
  reloadKey.value += 1
}
provide('reload', reloadPage)

// 固定标签（首个菜单/仪表盘）——菜单已在路由守卫加载完，setup 同步初始化
// （保证 TagsView 挂载 addView 前 affix 已就位，避免重复标签）
tagsStore.initAffixTags(permissionStore.menus)

const sidebarWidth = computed(() => (appStore.sidebarCollapsed ? '64px' : '220px'))
const currentTitle = computed(() => (route.meta.title as string) || '')
const nickname = computed(() => userStore.userInfo?.nickname || userStore.userInfo?.username || '')
const isSuper = computed(() => userStore.isSuperuser)
const appTitle = import.meta.env.VITE_APP_TITLE

function handleCommand(cmd: string) {
  if (cmd === 'logout') handleLogout()
  else if (cmd === 'profile') router.push('/profile')
}

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
  } catch {
    return
  }
  await userStore.logout()
  permissionStore.reset()
  router.push('/login')
}
</script>

<template>
  <el-container class="layout">
    <el-aside :width="sidebarWidth" class="layout-aside">
      <div class="logo" @click="router.push('/')">
        <el-icon :size="22" color="#409eff"><Platform /></el-icon>
        <span v-show="!appStore.sidebarCollapsed" class="logo-title">{{ appTitle }}</span>
      </div>
      <el-scrollbar>
        <SidebarMenu :menus="permissionStore.menus" :collapsed="appStore.sidebarCollapsed" />
      </el-scrollbar>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div class="header-left">
          <el-icon class="collapse-btn" :size="18" @click="appStore.toggleSidebar()">
            <Expand v-if="appStore.sidebarCollapsed" />
            <Fold v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tooltip :content="appStore.theme === 'dark' ? '切换到亮色' : '切换到暗色'">
            <el-icon class="header-icon" :size="18" @click="appStore.toggleTheme()">
              <Moon v-if="appStore.theme === 'light'" />
              <Sunny v-else />
            </el-icon>
          </el-tooltip>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="28" class="user-avatar" :src="userStore.userInfo?.avatar || ''">{{
                nickname.charAt(0).toUpperCase()
              }}</el-avatar>
              <span class="user-name">{{ nickname }}</span>
              <el-tag v-if="isSuper" size="small" type="danger" style="margin-left: 6px"
                >超管</el-tag
              >
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="layout-main">
        <TagsView />
        <div class="layout-content">
          <router-view v-slot="{ Component }">
            <keep-alive :include="tagsStore.cachedViews">
              <component :is="Component" :key="String(route.name) + '-' + reloadKey" />
            </keep-alive>
          </router-view>
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped lang="scss">
.layout {
  height: 100%;
}

.layout-aside {
  background: var(--fb-bg-card);
  border-right: 1px solid var(--fb-border);
  transition: width 0.25s;
  overflow: hidden;
}

.logo {
  height: var(--fb-header-height);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  border-bottom: 1px solid var(--fb-border);
  white-space: nowrap;
}

.logo-title {
  font-weight: 700;
  font-size: 16px;
}

.layout-header {
  height: var(--fb-header-height);
  background: var(--fb-bg-card);
  border-bottom: 1px solid var(--fb-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.collapse-btn {
  cursor: pointer;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  cursor: pointer;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  outline: none;
}

.user-avatar {
  background: var(--fb-primary);
}

.user-name {
  margin-left: 8px;
  font-size: 14px;
}

.layout-main {
  background: var(--fb-bg);
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.layout-content {
  flex: 1;
  overflow: auto;
  padding: 16px;
}
</style>
