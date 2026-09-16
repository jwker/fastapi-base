<script setup lang="ts">
defineOptions({ name: 'Announcements' })
import { onMounted, ref } from 'vue'
import { announcementApi } from '@/api'
import type { AnnouncementSimple } from '@/types'

const loading = ref(false)
const list = ref<AnnouncementSimple[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

const typeLabel: Record<string, string> = { notice: '通知', announcement: '公告' }

async function load() {
  loading.value = true
  try {
    const res = await announcementApi.publicList({ page: page.value, page_size: pageSize.value })
    list.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

// ---------- 详情 ----------
const drawerVisible = ref(false)
const detailTitle = ref('')
const detailContent = ref('')
const detailMeta = ref<{ type: string; publish_time: string | null }>({ type: 'notice', publish_time: null })

async function openDetail(row: AnnouncementSimple) {
  const res = await announcementApi.publicDetail(row.id)
  detailTitle.value = res.data.title
  detailContent.value = res.data.content
  detailMeta.value = { type: res.data.type, publish_time: res.data.publish_time }
  drawerVisible.value = true
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <span style="font-weight: 600">公告</span>
      </template>

      <el-table v-loading="loading" :data="list" border stripe @row-click="openDetail">
        <el-table-column prop="title" label="标题" min-width="240">
          <template #default="{ row }">
            <el-tag v-if="row.is_top" type="danger" size="small" style="margin-right: 6px">置顶</el-tag>
            <span>{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.type === 'announcement' ? 'primary' : 'info'" size="small">
              {{ typeLabel[row.type] ?? row.type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="publish_time" label="发布时间" width="180" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        style="margin-top: 12px; justify-content: flex-end"
        @current-change="load"
      />
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerVisible" :title="detailTitle" size="520px">
      <div style="color: #909399; font-size: 12px; margin-bottom: 12px">
        <el-tag :type="detailMeta.type === 'announcement' ? 'primary' : 'info'" size="small" style="margin-right: 8px">
          {{ typeLabel[detailMeta.type] ?? detailMeta.type }}
        </el-tag>
        {{ detailMeta.publish_time || '' }}
      </div>
      <div style="white-space: pre-wrap; word-break: break-word; line-height: 1.7">
        {{ detailContent }}
      </div>
    </el-drawer>
  </div>
</template>
