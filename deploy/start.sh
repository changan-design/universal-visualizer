#!/bin/sh
# 单端口启动：托管平台通过 PORT 环境变量注入端口；缺省 3000
PORT="${PORT:-3000}"
PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
echo "[start] using $PY on port $PORT"
exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
