# 前端开发规范

## 技术栈

Vue 3.5（Composition API + `<script setup>`）· Vite · TypeScript（严格模式）· Element Plus · Pinia · Vue Router 4 · Axios

## 目录约定

```
src/
├── api/          # 接口定义（按资源模块导出 xxxApi 对象）
├── router/       # 固定路由 + 动态路由生成（component-map 组件映射）
├── stores/       # Pinia：user（登录态）/ permission（菜单路由）/ app（主题布局）
├── directives/   # 自定义指令（v-permission）
├── components/   # 通用组件（ProTable）
├── layouts/      # 布局（侧边栏菜单递归组件）
├── views/        # 页面，菜单 component 字段与之对应（如 UserList.vue）
├── styles/       # 全局样式（CSS 变量 + 暗色主题）
└── types/        # 全局类型定义
```

## 约定

- 组件命名 PascalCase；页面文件名与后端菜单 `component` 字段一致
- 所有接口走 `src/api/`，禁止在页面直接写 axios
- 接口返回统一 `{ code, message, data }`，`code !== 0` 由拦截器统一提示
- 新增页面三步骤：① views 建组件 ② 后端 menus 表加菜单（permission_code 控制可见性）③ 分配角色菜单
- 按钮级权限用 `v-permission="'resource:action'"`，无权限自动移除元素

## 通用表格 ProTable 用法

```vue
<ProTable
  :columns="[{ prop: 'name', label: '名称' }]"
  :fetch-api="userApi.list"            <!-- (params) => Promise<{data:{total,items}}> -->
  :actions="[{ label: '编辑', permission: 'user:update', onClick: (row) => open(row) }]"
  create-label="新增用户"
  :on-create="openCreate"
/>
<!-- 自定义单元格：<template #slotName="{ row }"> -->
```

## 主题

- 亮/暗主题通过 `html.dark` + CSS 变量实现（`src/styles/index.scss`）
- 切换入口在顶栏，状态存 `appStore`（持久化）

## 质量要求

- `pnpm build` 必须通过（vue-tsc 严格检查）
- 提交前 eslint/prettier 格式化
- 新页面/组件补充测试（Vitest）
