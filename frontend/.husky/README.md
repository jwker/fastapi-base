# 前端 git hooks（lint-staged + husky 可选；此处为最小配置）
# 安装：pnpm add -D husky lint-staged && pnpm exec husky init
# 然后 .husky/pre-commit 内容：
#   pnpm exec lint-staged
# package.json 增加：
#   "lint-staged": { "src/**/*.{ts,vue}": ["eslint --fix", "prettier --write"] }
