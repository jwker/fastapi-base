<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Close } from '@element-plus/icons-vue'
import { useTagsStore, type TagView } from '@/stores/tags'

const route = useRoute()
const router = useRouter()
const tagsStore = useTagsStore()
// 由 layout provide：刷新当前页（key 重建）
const reload = inject<(key: string) => void>('reload')

// 路由变化 → 加标签（收敛在组件内，不挂全局钩子）
watch(
  () => route.fullPath,
  () => tagsStore.addView(route),
  { immediate: true },
)

const visitedViews = computed(() => tagsStore.visitedViews)

function isActive(view: TagView) {
  return view.path === route.path
}

function handleClick(view: TagView) {
  router.push(view.fullPath || view.path)
}

function getNextView(view: TagView): TagView | undefined {
  const list = tagsStore.visitedViews
  const idx = list.findIndex((v) => v.path === view.path)
  if (idx >= 0 && idx + 1 < list.length) return list[idx + 1] // 优先右侧
  if (idx > 0) return list[idx - 1] // 无右侧取左侧
  return list[0]
}

async function handleClose(view: TagView) {
  const wasActive = isActive(view)
  // 相邻标签在删除前定位（删除后列表里已无该 view）
  const next = getNextView(view)
  await tagsStore.delView(view)
  if (wasActive && next) router.push(next.fullPath || next.path)
}

// ---------- 右键菜单 ----------
const contextVisible = ref(false)
const contextX = ref(0)
const contextY = ref(0)
const contextView = ref<TagView | null>(null)

function openContext(e: MouseEvent, view: TagView) {
  contextView.value = view
  contextX.value = e.clientX
  contextY.value = e.clientY
  contextVisible.value = true
}

function refreshView() {
  reload?.('tags')
  contextVisible.value = false
}

async function closeView() {
  if (contextView.value) await handleClose(contextView.value)
  contextVisible.value = false
}

async function closeOthers() {
  const target = contextView.value
  if (!target) return
  tagsStore.delOthersViews(target)
  // 当前页不在保留列表（既非目标也非 affix）→ 跳目标
  if (!visitedViews.value.some((v) => isActive(v))) {
    router.push(target.fullPath || target.path)
  }
  contextVisible.value = false
}

async function closeAll() {
  tagsStore.delAllViews()
  // 当前页不在保留列表 → 跳 affix 或剩余第一个
  if (!visitedViews.value.some((v) => isActive(v))) {
    const target = tagsStore.affixTags[0] || tagsStore.visitedViews[0]
    if (target) router.push(target.fullPath || target.path)
  }
  contextVisible.value = false
}
</script>

<template>
  <div class="tags-view" @click="contextVisible = false">
    <el-scrollbar class="tags-scroll">
      <div class="tags-wrap">
        <div
          v-for="view in visitedViews"
          :key="view.path"
          class="tags-item"
          :class="{ active: isActive(view) }"
          @click="handleClick(view)"
          @contextmenu.prevent="openContext($event, view)"
        >
          <span class="tags-title">{{ view.title }}</span>
          <el-icon v-if="!view.affix" class="tags-close" @click.stop="handleClose(view)">
            <Close />
          </el-icon>
        </div>
      </div>
    </el-scrollbar>

    <!-- 右键菜单 -->
    <div
      v-if="contextVisible"
      class="context-menu"
      :style="{ left: contextX + 'px', top: contextY + 'px' }"
      @click.stop
    >
      <div class="context-item" @click="refreshView">刷新</div>
      <div v-if="contextView && !contextView.affix" class="context-item" @click="closeView">
        关闭
      </div>
      <div class="context-item" @click="closeOthers">关闭其他</div>
      <div class="context-item" @click="closeAll">关闭全部</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.tags-view {
  position: relative;
  border-bottom: 1px solid var(--fb-border);
  background: var(--fb-bg-card);
}

.tags-scroll {
  white-space: nowrap;
}

.tags-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
}

.tags-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 12px;
  line-height: 20px;
  border: 1px solid var(--fb-border);
  border-radius: 4px;
  cursor: pointer;
  color: var(--fb-text-secondary);
  background: var(--fb-bg-page);
  user-select: none;

  &:hover {
    color: var(--fb-text);
  }

  &.active {
    color: #fff;
    background: var(--fb-primary, #409eff);
    border-color: var(--fb-primary, #409eff);
  }
}

.tags-close {
  font-size: 12px;
  border-radius: 50%;
  padding: 1px;
  &:hover {
    background: rgba(255, 255, 255, 0.2);
  }
}

.context-menu {
  position: fixed;
  z-index: 3000;
  min-width: 110px;
  padding: 4px 0;
  background: var(--fb-bg-card);
  border: 1px solid var(--fb-border);
  border-radius: 6px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
}

.context-item {
  padding: 7px 14px;
  font-size: 13px;
  cursor: pointer;
  &:hover {
    background: var(--fb-bg-hover, rgba(0, 0, 0, 0.04));
  }
}
</style>
