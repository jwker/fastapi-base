import request from '@/utils/request'
import type {
  ApiResponse,
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
