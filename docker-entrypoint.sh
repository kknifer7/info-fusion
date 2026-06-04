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

# 启动应用
exec node dist/src/main
