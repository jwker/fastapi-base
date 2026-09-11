# ---------- 前端多阶段构建 ----------
FROM node:22-alpine AS builder

WORKDIR /app
RUN corepack enable
ENV CI=true

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# ---------- Nginx 运行镜像 ----------
FROM nginx:alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
