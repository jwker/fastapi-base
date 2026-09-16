/** 后端统一响应结构：{ code, message, data }，code=0 成功 */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserInfo {
  id: number
  username: string
  nickname: string
  email: string
  phone: string
  avatar: string
  is_superuser: boolean
  permissions: string[]
  roles: string[]
}

export interface LoginResult {
  tokens: TokenPair
  user: UserInfo
}

export interface MenuItem {
  id: number
  parent_id: number | null
  name: string
  path: string
  component: string
  icon: string
  sort_order: number
  is_visible: boolean
  permission_code: string | null
  children: MenuItem[]
}

export interface PageResult<T> {
  total: number
  items: T[]
}

export interface UserRecord {
  id: number
  username: string
  nickname: string
  email: string
  phone: string
  status: number
  avatar: string
  is_superuser: boolean
  last_login_at: string | null
  created_at: string
  role_ids: number[]
}

export interface RoleRecord {
  id: number
  name: string
  code: string
  description: string
  status: number
  created_at: string
  permission_ids: number[]
  menu_ids: number[]
}

export interface PermissionRecord {
  id: number
  name: string
  code: string
  resource: string
  action: string
  description: string
  created_at: string
}

export interface AuditLogRecord {
  id: number
  user_id: number | null
  username: string
  module: string
  action: string
  method: string
  path: string
  request_body: string
  response_status: number
  ip: string
  user_agent: string
  created_at: string
}

export interface FileRecord {
  id: number
  url: string
  name: string
  size: number
  mime_type: string
  /** 来源（程序自动打标）：avatar=头像 / manual=文件管理页手动传 */
  source: string
  remark: string
  created_by: number | null
  created_by_name: string
  created_at: string
}

// ---------- 数据字典 ----------
export interface DictTypeRecord {
  id: number
  name: string
  type: string
  remark: string
  created_at: string
  item_count: number
}

export interface DictItemRecord {
  id: number
  type_id: number
  label: string
  value: string
  sort: number
  is_default: boolean
  status: number
  remark: string
  created_at: string
}

// ---------- 系统参数 ----------
export interface ConfigRecord {
  id: number
  key: string
  value: string
  value_type: string
  remark: string
  created_at: string
  updated_at: string
}

/** 业务取用字典项（GET /dicts/type/{type}） */export interface DictOption {
  label: string
  value: string
}

// ---------- 通知公告 ----------
export interface AnnouncementRecord {
  id: number
  title: string
  content: string
  type: string
  status: number
  is_top: boolean
  expire_time: string | null
  publish_time: string | null
  created_by: number | null
  created_by_name: string
  created_at: string
  updated_at: string
}

/** 用户端公告列表项（不含正文） */
export interface AnnouncementSimple {
  id: number
  title: string
  type: string
  is_top: boolean
  publish_time: string | null
}
