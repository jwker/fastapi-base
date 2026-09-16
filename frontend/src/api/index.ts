import request from '@/utils/request'
import type {
  AnnouncementRecord,
  AnnouncementSimple,
  ApiResponse,
  AuditLogRecord,
  ConfigRecord,
  DictItemRecord,
  DictOption,
  DictTypeRecord,
  FileRecord,
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

export const fileApi = {
  /** 上传文件（FormData，axios 自动带 multipart boundary），source 为来源打标 */
  upload: (file: File, source = 'manual', remark = '') => {
    const form = new FormData()
    form.append('file', file)
    if (source) form.append('source', source)
    if (remark) form.append('remark', remark)
    return request.post<ApiResponse<FileRecord>>('/files/upload', form)
  },
  /** 文件列表（分页 + 文件名/备注模糊搜索） */
  list: (params: { page: number; page_size: number; keyword?: string }) =>
    request.get<ApiResponse<PageResult<FileRecord>>>('/files', { params }),
  /** 删除文件（记录 + 磁盘文件） */
  remove: (id: number) => request.delete<ApiResponse<null>>(`/files/${id}`),
}

// ---------- 数据字典 ----------
export const dictApi = {
  /** 字典类型分页 */
  types: (params: { page: number; page_size: number; keyword?: string }) =>
    request.get<ApiResponse<PageResult<DictTypeRecord>>>('/dicts', { params }),
  createType: (data: { name: string; type: string; remark?: string }) =>
    request.post<ApiResponse<DictTypeRecord>>('/dicts', data),
  updateType: (id: number, data: { name?: string; type?: string; remark?: string }) =>
    request.put<ApiResponse<DictTypeRecord>>(`/dicts/${id}`, data),
  removeType: (id: number) => request.delete<ApiResponse<null>>(`/dicts/${id}`),
  /** 类型下字典项 */
  items: (typeId: number) =>
    request.get<ApiResponse<DictItemRecord[]>>(`/dicts/${typeId}/items`),
  createItem: (
    typeId: number,
    data: { label: string; value: string; sort?: number; is_default?: boolean; status?: number; remark?: string },
  ) => request.post<ApiResponse<DictItemRecord>>(`/dicts/${typeId}/items`, data),
  updateItem: (
    id: number,
    data: { label?: string; value?: string; sort?: number; is_default?: boolean; status?: number; remark?: string },
  ) => request.put<ApiResponse<DictItemRecord>>(`/dicts/items/${id}`, data),
  removeItem: (id: number) => request.delete<ApiResponse<null>>(`/dicts/items/${id}`),
  /** 业务取用：按类型编码取启用项 */
  byType: (code: string) => request.get<ApiResponse<DictOption[]>>(`/dicts/type/${code}`),
}

// ---------- 系统参数 ----------
export const configApi = {
  /** 参数分页 */
  list: (params: { page: number; page_size: number; keyword?: string }) =>
    request.get<ApiResponse<PageResult<ConfigRecord>>>('/configs', { params }),
  create: (data: { key: string; value: string; value_type?: string; remark?: string }) =>
    request.post<ApiResponse<ConfigRecord>>('/configs', data),
  update: (
    id: number,
    data: { value: string; value_type?: string; remark?: string },
  ) => request.put<ApiResponse<ConfigRecord>>(`/configs/${id}`, data),
  remove: (id: number) => request.delete<ApiResponse<null>>(`/configs/${id}`),
  /** 业务取用：按逗号分隔 key 批量读取（仅需登录） */
  byKeys: (keys: string[]) =>
    request.get<ApiResponse<Record<string, string>>>('/configs/by-key', {
      params: { keys: keys.join(',') },
    }),
}

// ---------- 通知公告 ----------
export const announcementApi = {
  /** 管理端分页 */
  list: (params: { page: number; page_size: number; keyword?: string }) =>
    request.get<ApiResponse<PageResult<AnnouncementRecord>>>('/announcements', { params }),
  create: (data: {
    title: string
    content: string
    type?: string
    is_top?: boolean
    expire_time?: string | null
  }) => request.post<ApiResponse<AnnouncementRecord>>('/announcements', data),
  update: (
    id: number,
    data: {
      title?: string
      content?: string
      type?: string
      is_top?: boolean
      expire_time?: string | null
    },
  ) => request.put<ApiResponse<AnnouncementRecord>>(`/announcements/${id}`, data),
  remove: (id: number) => request.delete<ApiResponse<null>>(`/announcements/${id}`),
  /** 发布（草稿→已发布，写 publish_time） */
  publish: (id: number) => request.put<ApiResponse<AnnouncementRecord>>(`/announcements/${id}/publish`),
  /** 下线（已发布→已下线） */
  offline: (id: number) => request.put<ApiResponse<AnnouncementRecord>>(`/announcements/${id}/offline`),
  /** 用户端列表（仅登录，已发布且未过期，置顶优先） */
  publicList: (params: { page: number; page_size: number }) =>
    request.get<ApiResponse<PageResult<AnnouncementSimple>>>('/announcements/public', { params }),
  /** 用户端详情（仅登录） */
  publicDetail: (id: number) =>
    request.get<ApiResponse<AnnouncementRecord>>(`/announcements/public/${id}`),
}
