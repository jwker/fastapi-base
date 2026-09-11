import request from '@/utils/request'
import type {
  ApiResponse,
  AuditLogRecord,
  LoginResult,
  MenuItem,
  PageResult,
  PermissionRecord,
  RoleRecord,
  TokenPair,
  UserRecord,
} from '@/types'

// ---------- 认证 ----------
export const authApi = {
  login: (username: string, password: string) =>
    request.post<ApiResponse<LoginResult>>('/auth/login', { username, password }),
  refresh: (refresh_token: string) =>
    request.post<ApiResponse<TokenPair>>('/auth/refresh', { refresh_token }),
  logout: (refresh_token?: string) =>
    request.post<ApiResponse<null>>('/auth/logout', refresh_token ? { refresh_token } : {}),
  me: () => request.get<ApiResponse<import('@/types').UserInfo>>('/auth/me'),
  changePassword: (old_password: string, new_password: string) =>
    request.post<ApiResponse<null>>('/auth/change-password', { old_password, new_password }),
  updateProfile: (data: Record<string, unknown>) =>
    request.put<ApiResponse<import('@/types').UserInfo>>('/auth/profile', data),
}

// ---------- 用户 ----------
export const userApi = {
  list: (params: { page: number; page_size: number; keyword?: string }) =>
    request.get<ApiResponse<PageResult<UserRecord>>>('/users', { params }),
  create: (data: Partial<UserRecord> & { username: string; password: string }) =>
    request.post<ApiResponse<UserRecord>>('/users', data),
  update: (id: number, data: Record<string, unknown>) =>
    request.put<ApiResponse<UserRecord>>(`/users/${id}`, data),
  remove: (id: number) => request.delete<ApiResponse<null>>(`/users/${id}`),
}

// ---------- 角色 ----------
export const roleApi = {
  list: (params: { page: number; page_size: number; keyword?: string }) =>
    request.get<ApiResponse<PageResult<RoleRecord>>>('/roles', { params }),
  create: (data: { name: string; code: string; description?: string; status?: number }) =>
    request.post<ApiResponse<RoleRecord>>('/roles', data),
  update: (id: number, data: Record<string, unknown>) =>
    request.put<ApiResponse<RoleRecord>>(`/roles/${id}`, data),
  assignPermissions: (id: number, permission_ids: number[]) =>
    request.put<ApiResponse<RoleRecord>>(`/roles/${id}/permissions`, { permission_ids }),
  assignMenus: (id: number, menu_ids: number[]) =>
    request.put<ApiResponse<RoleRecord>>(`/roles/${id}/menus`, { menu_ids }),
  remove: (id: number) => request.delete<ApiResponse<null>>(`/roles/${id}`),
}

// ---------- 权限 ----------
export const permissionApi = {
  list: (params: { page?: number; page_size?: number; keyword?: string }) =>
    request.get<ApiResponse<PageResult<PermissionRecord>>>('/permissions', { params }),
}

// ---------- 菜单 ----------
export const menuApi = {
  tree: () => request.get<ApiResponse<MenuItem[]>>('/menus/tree'),
  my: () => request.get<ApiResponse<MenuItem[]>>('/menus/my'),
  create: (data: Partial<MenuItem> & { name: string; path: string }) =>
    request.post<ApiResponse<MenuItem>>('/menus', data),
  update: (id: number, data: Record<string, unknown>) =>
    request.put<ApiResponse<MenuItem>>(`/menus/${id}`, data),
  remove: (id: number) => request.delete<ApiResponse<null>>(`/menus/${id}`),
}

// ---------- 统计 ----------
export interface StatsOverview {
  user_count: number
  role_count: number
  permission_count: number
  menu_count: number
}

export const statsApi = {
  overview: () => request.get<ApiResponse<StatsOverview>>('/stats/overview'),
}

// ---------- 操作审计日志 ----------
export interface AuditLogQuery {
  page: number
  page_size: number
  keyword?: string
  username?: string
  module?: string
  action?: string
  status?: number
  start_time?: string
  end_time?: string
}

export const auditLogApi = {
  list: (params: AuditLogQuery) =>
    request.get<ApiResponse<PageResult<AuditLogRecord>>>('/audit-logs', { params }),
  export: (params: AuditLogQuery) =>
    request.get<Blob>('/audit-logs/export', { params, responseType: 'blob' }),
  remove: (params: AuditLogQuery & { end_time: string }) =>
    request.delete<ApiResponse<{ deleted: number }>>('/audit-logs', { params }),
}
