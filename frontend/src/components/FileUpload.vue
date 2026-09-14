<script setup lang="ts">
/**
 * 通用文件上传组件：基于 el-upload 封装。
 * - v-model 绑定文件/图片 URL（可上传，也可直接粘贴 URL）
 * - 上传成功后自动把 URL 写入 v-model
 * - 支持图片预览 / 文件链接展示
 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fileApi } from '@/api'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    /** el-upload 的 accept，如 ".jpg,.png,.pdf" */
    accept?: string
    /** 大小上限（MB），前端预校验，后端仍兜底 */
    maxSizeMb?: number
    tip?: string
    /** 来源打标（程序自动带，用户不可选）：avatar=头像 / manual=手动素材 */
    source?: string
  }>(),
  { modelValue: '', accept: '', maxSizeMb: 5, tip: '', source: 'manual' },
)
const emit = defineEmits<{ (e: 'update:modelValue', url: string): void }>()

const uploading = ref(false)
const urlInput = computed({
  get: () => props.modelValue || '',
  set: (v: string) => emit('update:modelValue', v),
})

const isImage = (url: string) => /\.(png|jpe?g|gif|webp|svg)$/i.test(url.split('?')[0])

async function handleChange(option: { raw?: File }) {
  const file = option.raw
  if (!file) return
  if (file.size > props.maxSizeMb * 1024 * 1024) {
    ElMessage.error(`文件大小不能超过 ${props.maxSizeMb}MB`)
    return
  }
  uploading.value = true
  try {
    const res = await fileApi.upload(file, props.source)
    emit('update:modelValue', res.data.url)
    ElMessage.success('上传成功')
  } catch {
    /* 拦截器已统一提示 */
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="file-upload">
    <div class="row">
      <el-upload
        :show-file-list="false"
        :accept="accept"
        :auto-upload="false"
        :disabled="uploading"
        :on-change="handleChange"
      >
        <el-button :loading="uploading" size="small">
          {{ modelValue ? '重新上传' : '选择文件' }}
        </el-button>
      </el-upload>
      <el-input
        v-model="urlInput"
        class="url-input"
        placeholder="或直接粘贴文件/图片 URL"
        clearable
      />
    </div>
    <div v-if="modelValue" class="file-preview">
      <el-image v-if="isImage(modelValue)" :src="modelValue" fit="cover" class="preview-img" />
      <a v-else :href="modelValue" target="_blank" class="file-link">
        {{ modelValue.split('/').pop() }}
      </a>
    </div>
    <div v-if="tip" class="tip">{{ tip }}</div>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.url-input {
  max-width: 280px;
}
.file-preview {
  margin-top: 8px;
}
.preview-img {
  width: 64px;
  height: 64px;
  border-radius: 6px;
  border: 1px solid var(--el-border-color-lighter);
}
.file-link {
  font-size: 12px;
  color: var(--el-color-primary);
}
.tip {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
