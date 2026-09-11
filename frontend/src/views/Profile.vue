<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const userStore = useUserStore()
const permissionStore = usePermissionStore()
const username = computed(() => userStore.userInfo?.username || '')

// ---------- 基本资料 ----------
const profileFormRef = ref<FormInstance>()
const profileSaving = ref(false)
const profileForm = reactive({
  nickname: userStore.userInfo?.nickname || '',
  email: userStore.userInfo?.email || '',
  phone: userStore.userInfo?.phone || '',
  avatar: userStore.userInfo?.avatar || '',
})

const profileRules: FormRules = {
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
}

async function saveProfile() {
  // 提交前防线：不依赖 el-form 校验时机，保证必填与格式
  if (!profileForm.nickname.trim()) {
    ElMessage.error('请输入昵称')
    return
  }
  const email = profileForm.email.trim()
  if (!email) {
    ElMessage.error('请输入邮箱')
    return
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    ElMessage.error('邮箱格式不正确')
    return
  }
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return
  profileSaving.value = true
  try {
    await userStore.updateProfile({ ...profileForm })
    ElMessage.success('资料更新成功')
  } catch {
    /* 错误已由拦截器提示 */
  } finally {
    profileSaving.value = false
  }
}

// ---------- 修改密码 ----------
const pwdFormRef = ref<FormInstance>()
const pwdSaving = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '', confirm_password: '' })

const pwdRules: FormRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码长度 6-128 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== pwdForm.new_password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function savePassword() {
  // 提交前防线：不依赖 el-form 校验时机（vitest 环境 el-form 校验会空转），
  // 保证"非空/长度/两次一致"在提交瞬间被拦截
  const { old_password, new_password, confirm_password } = pwdForm
  if (!old_password || !new_password || !confirm_password) {
    ElMessage.error('请填写完整密码信息')
    return
  }
  if (new_password.length < 6 || new_password.length > 128) {
    ElMessage.error('新密码长度需为 6-128 位')
    return
  }
  if (new_password !== confirm_password) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  const valid = await pwdFormRef.value?.validate().catch(() => false)
  if (!valid) return
  pwdSaving.value = true
  try {
    await userStore.changePassword(pwdForm.old_password, pwdForm.new_password)
    ElMessage.success('密码修改成功，请重新登录')
    permissionStore.reset()
    router.push('/login')
  } catch {
    /* 错误已由拦截器提示 */
  } finally {
    pwdSaving.value = false
  }
}
</script>

<template>
  <div class="page-container profile-page">
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never" header="基本资料">
          <el-form
            ref="profileFormRef"
            :model="profileForm"
            :rules="profileRules"
            label-width="80px"
            class="profile-form"
          >
            <el-form-item label="用户名">
              <el-input :model-value="username" disabled />
            </el-form-item>
            <el-form-item label="昵称" prop="nickname">
              <el-input v-model="profileForm.nickname" maxlength="50" placeholder="昵称" />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="profileForm.email" maxlength="100" placeholder="邮箱" />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="profileForm.phone" maxlength="20" placeholder="手机号" />
            </el-form-item>
            <el-form-item label="头像">
              <el-input v-model="profileForm.avatar" maxlength="255" placeholder="头像图片地址（URL）" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="profileSaving" @click="saveProfile">
                保存资料
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never" header="修改密码">
          <el-form
            ref="pwdFormRef"
            :model="pwdForm"
            :rules="pwdRules"
            label-width="80px"
            class="profile-form"
          >
            <el-form-item label="原密码" prop="old_password">
              <el-input
                v-model="pwdForm.old_password"
                type="password"
                show-password
                placeholder="原密码"
              />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input
                v-model="pwdForm.new_password"
                type="password"
                show-password
                placeholder="至少 6 位"
              />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm_password">
              <el-input
                v-model="pwdForm.confirm_password"
                type="password"
                show-password
                placeholder="再次输入新密码"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="pwdSaving" @click="savePassword">
                修改密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.profile-page {
  .profile-form {
    max-width: 420px;
  }
}
</style>
