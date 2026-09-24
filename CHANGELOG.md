# Changelog

本项目所有值得记录的变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本 SemVer](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 待发布

- 开源准备：MIT License、生产环境启动校验（防默认密钥/密码上线）、README 界面预览与跟进更新说明

## [0.1.0] - 2026-09-24

首个开源版本。FastAPI + Vue3 全栈脚手架，功能齐备、测试与 CI 完整。

### 新增

- **认证与安全**
  - JWT 双 Token：Access（15 分钟）+ Refresh（7 天，存 Redis），支持自动续期与重放原请求
  - 登出黑名单、登录失败锁定（5 次 / 10 分钟，Redis 滑动窗口）、接口限流
- **权限体系（RBAC）**
  - 用户 / 角色 / 权限 / 菜单四要素，动态菜单路由（登录后由后端下发）
  - 按钮级权限指令 `v-permission`
- **系统能力**
  - 操作日志（审计）：全链路记录，支持导出
  - 字典管理、系统参数配置（进程内缓存 + 写失效）
  - 文件管理：上传 / 下载 / 预览，来源标注（头像 / 手动上传）
  - 通知公告：发布 / 下线 / 置顶 / 过期，管理端 + 用户端列表与详情
- **部署与工程化**
  - Docker Compose + Nginx（SPA + Gzip + 反向代理）一键编排，支持三种启动方式（全 Docker / 混合 / 纯本地）
  - GitHub Actions 四阶段 CI：Backend lint+test / Frontend lint+test+build / E2E（Playwright）/ Docker Build
  - 测试体系：后端 pytest 106 例 + 前端 Vitest 106 例 + E2E 6 例
