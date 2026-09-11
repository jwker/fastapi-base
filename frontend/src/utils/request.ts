import axios, { AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
  withCredentials: false,
})

// 请求拦截器：自动携带 Access Token
service.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const userStore = useUserStore()
  if (userStore.accessToken) {
    config.headers.Authorization = `Bearer ${userStore.accessToken}`
  }
  return config
})

// 响应拦截器：业务码判断 + 自动刷新 + 统一错误提示
service.interceptors.response.use(
  async (response) => {
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) return body
      // 业务错误
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message))
    }
    return body
  },
  async (error: AxiosError) => {
    const userStore = useUserStore()
    const status = error.response?.status
    const config = error.config as (AxiosRequestConfig & { _retried?: boolean }) | undefined

    // 401 且未重试过 → 尝试刷新 Token
    // 排除 refresh / logout 请求本身，避免刷新失败时无限递归
    const isLogoutRequest = config?.url?.includes('/auth/logout')
    const isRefreshRequest = config?.url?.includes('/auth/refresh')
    if (
      status === 401 &&
      config &&
      !config._retried &&
      !isLogoutRequest &&
      !isRefreshRequest &&
      userStore.refreshToken
    ) {
      config._retried = true
      try {
        const ok = await userStore.refreshTokens()
        if (ok) {
          return service(config) // 用新 token 重放原请求
        }
      } catch {
        /* 刷新失败走登出 */
      }
      userStore.logout()
      router.push('/login')
      return Promise.reject(error)
    }

    // 401 且不可刷新（refresh/logout 请求）→ 清理本地登录态
    if (status === 401 && (isLogoutRequest || isRefreshRequest)) {
      userStore.$reset()
      router.push('/login')
      return Promise.reject(error)
    }

    if (status === 403) {
      ElMessage.error((error.response?.data as any)?.message || '没有权限')
    } else if (status === 429) {
      ElMessage.error('请求过于频繁，请稍后再试')
    } else if (status && status >= 400 && status < 500) {
      // 400/404 等：取后端业务错误信息（登录失败、用户名已存在、资源不存在等）
      ElMessage.error((error.response?.data as any)?.message || '请求失败')
    } else if (status && status >= 500) {
      ElMessage.error('服务器开小差了，请稍后再试')
    }
    return Promise.reject(error)
  },
)

/**
 * 类型化请求封装：拦截器已把响应解包为 body（ApiResponse<T>），
 * 这里用 axios 第二个泛型参数让 TS 类型与运行时一致。
 */
const http = {
  get: <T>(url: string, config?: AxiosRequestConfig) => service.get<T, T>(url, config),
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    service.post<T, T>(url, data, config),
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    service.put<T, T>(url, data, config),
  delete: <T>(url: string, config?: AxiosRequestConfig) => service.delete<T, T>(url, config),
}

export default http
