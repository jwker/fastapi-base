<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { usePermissionStore } from '@/stores/permission'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const permissionStore = usePermissionStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const appTitle = import.meta.env.VITE_APP_TITLE

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await userStore.login(form.username, form.password)
    permissionStore.reset() // 强制重新拉取菜单
    ElMessage.success('登录成功')
    router.push((route.query.redirect as string) || '/')
  } catch {
    /* 错误已由拦截器提示 */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-title">
        <el-icon :size="28" color="#409eff"><Platform /></el-icon>
        <h2>{{ appTitle }}</h2>
        <p>全栈脚手架 · 前后端分离</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" clearable>
            <template #prefix
              ><el-icon><User /></el-icon
            ></template>
          </el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" show-password>
            <template #prefix
              ><el-icon><Lock /></el-icon
            ></template>
          </el-input>
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          style="width: 100%"
          :loading="loading"
          @click="handleLogin"
        >
          登 录
        </el-button>
      </el-form>

      <div class="login-tip">默认超管：admin / admin123</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f3b5f 0%, #409eff 100%);
}

.login-card {
  width: 380px;
  background: var(--fb-bg-card);
  border-radius: 12px;
  padding: 40px 36px 24px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}

.login-title {
  text-align: center;
  margin-bottom: 28px;

  h2 {
    margin: 10px 0 4px;
    font-size: 20px;
  }

  p {
    color: var(--fb-text-secondary);
    font-size: 13px;
  }
}

.login-tip {
  margin-top: 20px;
  text-align: center;
  color: var(--fb-text-secondary);
  font-size: 12px;
}
</style>
