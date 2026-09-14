<script setup lang="ts">
defineOptions({ name: 'Dashboard' })
import { computed, onMounted, ref } from 'vue'
import { statsApi } from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const nickname = computed(() => userStore.userInfo?.nickname || userStore.userInfo?.username || '')
const isSuper = computed(() => userStore.isSuperuser)
const date = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
  weekday: 'long',
})

const stats = ref([
  { label: '用户', value: '-', icon: 'User', color: '#409eff' },
  { label: '角色', value: '-', icon: 'Avatar', color: '#67c23a' },
  { label: '权限', value: '-', icon: 'Lock', color: '#e6a23c' },
  { label: '菜单', value: '-', icon: 'Menu', color: '#f56c6c' },
])

onMounted(async () => {
  // 统计数据仅超管可见，非超管不请求
  if (!userStore.isSuperuser) return
  try {
    const res = await statsApi.overview()
    const d = res.data
    stats.value = [
      { label: '用户', value: String(d.user_count), icon: 'User', color: '#409eff' },
      { label: '角色', value: String(d.role_count), icon: 'Avatar', color: '#67c23a' },
      { label: '权限', value: String(d.permission_count), icon: 'Lock', color: '#e6a23c' },
      { label: '菜单', value: String(d.menu_count), icon: 'Menu', color: '#f56c6c' },
    ]
  } catch {
    /* 统计加载失败保持占位 */
  }
})
</script>

<template>
  <div>
    <el-card class="welcome-card">
      <h2>欢迎回来，{{ nickname }}！</h2>
      <p>{{ date }}</p>
      <p class="desc">这是 FastAPI + Vue3 全栈脚手架，登录后菜单由后端动态下发。</p>
    </el-card>

    <el-row v-if="isSuper" :gutter="16" class="stats-row">
      <el-col v-for="s in stats" :key="s.label" :span="6">
        <el-card class="stat-card">
          <el-icon :size="28" :color="s.color"><component :is="s.icon" /></el-icon>
          <div>
            <div class="stat-value">{{ s.value }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.welcome-card {
  margin-bottom: 16px;

  h2 {
    margin-bottom: 8px;
  }

  .desc {
    margin-top: 8px;
    color: var(--fb-text-secondary);
    font-size: 13px;
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
}

.stat-label {
  font-size: 13px;
  color: var(--fb-text-secondary);
}
</style>
