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
