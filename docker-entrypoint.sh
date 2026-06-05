#!/bin/sh
set -e

# 执行数据库迁移
pnpm db:migrate:prod

# 检查 Config 表是否为空，为空则执行初始化 SQL
ROW_COUNT=$(sqlite3 data/prod.db "SELECT COUNT(*) FROM Config;" 2>/dev/null || echo "0")
if [ "$ROW_COUNT" -eq "0" ]; then
    echo "Config table is empty, running init.sql..."
    sqlite3 data/prod.db < sql/init.sql
    echo "Initialization completed."
fi

# 安装爬虫的 Python 依赖（如果存在 requirements.txt）
if [ -f /app/crawlers/requirements.txt ]; then
    echo "Installing crawler dependencies..."
    pip3 install -r /app/crawlers/requirements.txt --break-system-packages --quiet
    echo "Crawler dependencies installed."
fi

# 启动应用
exec node dist/main
