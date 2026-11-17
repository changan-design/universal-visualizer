#!/bin/sh
# 单端口启动：沙箱注入 PORT 环境变量，缺省 3000
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-3000}"
