# 数据库设计

## ER 关系

```
users ──< user_roles >── roles ──< role_permissions >── permissions
                              │
                              └──< role_menus >── menus (自引用树)
```

## 表结构

### users 用户表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | BIGINT PK | 主键 |
| username | VARCHAR(50) UNIQUE | 登录名 |
| password_hash | VARCHAR(255) | bcrypt 哈希 |
| nickname | VARCHAR(50) | 昵称 |
| email | VARCHAR(100) | 邮箱 |
| phone | VARCHAR(20) | 手机号 |
| avatar | VARCHAR(255) | 头像 URL |
| status | INT | 1 启用 / 0 禁用 |
| is_superuser | BOOLEAN | 超管标志（跳过权限校验） |
| last_login_at | TIMESTAMP | 最后登录时间 |
| created_at / updated_at | TIMESTAMP | 时间戳 |

### roles 角色表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | BIGINT PK | 主键 |
| name | VARCHAR(50) | 角色名称 |
| code | VARCHAR(50) UNIQUE | 角色编码（super_admin / admin / user） |
| description | VARCHAR(255) | 描述 |
| status | INT | 1 启用 / 0 禁用 |
| created_at / updated_at | TIMESTAMP | 时间戳 |

### permissions 权限表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | BIGINT PK | 主键 |
| name | VARCHAR(50) | 权限名称 |
| code | VARCHAR(100) UNIQUE | 权限码（`resource:action`） |
| resource | VARCHAR(50) | 资源（user / role / menu / permission） |
| action | VARCHAR(50) | 动作（create / read / update / delete / assign） |
| description | VARCHAR(255) | 描述 |
| created_at | TIMESTAMP | 时间戳 |

### menus 菜单表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | BIGINT PK | 主键 |
| parent_id | BIGINT FK→menus.id | 父菜单（NULL=顶级），级联删除 |
| name | VARCHAR(50) | 菜单名称 |
| path | VARCHAR(100) | 路由路径 |
| component | VARCHAR(100) | 前端组件名（如 UserList / Layout） |
| icon | VARCHAR(50) | 图标名 |
| sort_order | INT | 排序 |
| is_visible | BOOLEAN | 是否显示 |
| permission_code | VARCHAR(100) NULL | 关联权限码（空=登录可见） |
| created_at / updated_at | TIMESTAMP | 时间戳 |

### 关联表（复合主键，级联删除）

- `user_roles`：user_id + role_id
- `role_permissions`：role_id + permission_id
- `role_menus`：role_id + menu_id

## 预置数据（scripts/init_db.py，幂等）

- 权限 14 个：user/role/menu 各 4 个动作 + permission 2 个
- 角色 3 个：super_admin（超管）、admin（全量管理）、user（只读）
- 菜单：仪表盘 + 系统管理（用户/角色/权限/菜单）
- 超管：admin / admin123（可用环境变量覆盖）

## 迁移

```bash
cd backend
uv run alembic revision --autogenerate -m "描述"   # 生成迁移
uv run alembic upgrade head                        # 执行迁移
```

- SQLite 下主键自动映射为 INTEGER（保证自增）；PostgreSQL 为 BIGINT
- 生产迁移前需在测试环境验证
