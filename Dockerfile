# ==================== 构建阶段 ====================
FROM docker.1ms.run/node:24-alpine AS builder

# 安装构建工具（better-sqlite3 需要编译原生模块）
RUN apk add --no-cache python3 make g++ \
  && npm install -g pnpm@10.34.1

WORKDIR /app

# 先复制包管理文件，利用缓存层
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# 安装依赖（包括 devDependencies，构建需要）
RUN pnpm install --frozen-lockfile

# 复制 Prisma schema 和配置文件，并生成客户端
COPY prisma ./prisma/
COPY prisma.config.ts ./prisma.config.ts
RUN pnpm db:generate

# 复制源代码和配置文件
COPY tsconfig.json tsconfig.build.json nest-cli.json ./
COPY src ./src

# 构建 NestJS 应用
RUN pnpm build

# ==================== 生产阶段 ====================
FROM docker.1ms.run/node:24-alpine AS production

# 安装 pnpm 和 sqlite3（用于执行初始化 SQL）
RUN apk add --no-cache sqlite \
  && npm install -g pnpm@10.34.1

WORKDIR /app

# 从构建阶段复制必要文件
COPY --from=builder /app/package.json /app/pnpm-lock.yaml /app/pnpm-workspace.yaml ./
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/prisma ./prisma
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/prisma.config.ts ./prisma.config.ts

# env 目录直接从构建上下文复制（不需要经过 builder）
COPY env ./env

# 复制初始化 SQL 和启动脚本
COPY sql ./sql
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x docker-entrypoint.sh

# 设置环境变量
ENV NODE_ENV=production
ENV PORT=3000

# 暴露端口
EXPOSE 3000

# 健康检查（访问根路径）
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:3000/ || exit 1

# 使用启动脚本
CMD ["./docker-entrypoint.sh"]
