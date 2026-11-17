@echo off
setlocal
title Universal Visualizer Launcher
set "ROOT=%~dp0"

REM ================= 检查 Python =================
where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未检测到 Python，请先安装 Python 3.9+ 并勾选 "Add to PATH"。
  pause
  exit /b 1
)

REM ================= [1/4] 后端虚拟环境 =================
cd /d "%ROOT%backend"
if not exist ".venv\Scripts\python.exe" (
  echo [1/4] 首次运行：创建 Python 虚拟环境 ...
  python -m venv .venv
  if errorlevel 1 (
    echo [错误] 虚拟环境创建失败，请检查 Python 安装。
    pause
    exit /b 1
  )
) else (
  echo [1/4] 虚拟环境已存在，跳过创建。
)

REM ================= [2/4] 安装后端依赖（仅首次） =================
if not exist ".venv\.deps_ok" (
  echo [2/4] 安装后端依赖（首次约 1-3 分钟）...
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  if errorlevel 1 (
    echo [提示] 国内镜像安装失败，改用官方源重试 ...
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
  )
  if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络后重试。
    pause
    exit /b 1
  )
  type nul > ".venv\.deps_ok"
) else (
  echo [2/4] 后端依赖已安装，跳过。
)

REM ================= [3/4] 前端依赖 =================
cd /d "%ROOT%frontend"
where npm >nul 2>nul
if errorlevel 1 (
  echo [错误] 未检测到 npm，请先安装 Node.js 18+ （https://nodejs.org）。
  pause
  exit /b 1
)
if not exist "node_modules" (
  echo [3/4] 首次运行：安装前端依赖（约 1-3 分钟）...
  call npm install
  if errorlevel 1 (
    echo [错误] 前端依赖安装失败，请检查网络后重试。
    pause
    exit /b 1
  )
) else (
  echo [3/4] 前端依赖已安装，跳过。
)

REM ================= [4/4] 启动服务并打开浏览器 =================
echo [4/4] 启动服务 ...
cd /d "%ROOT%backend"
start "UV-Backend-8000" cmd /k """.venv\Scripts\python.exe"" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
cd /d "%ROOT%frontend"
start "UV-Frontend-5173" cmd /k "npm run dev"

echo 等待服务就绪后打开浏览器 ...
timeout /t 10 >nul
start "" http://localhost:5173

echo.
echo ==================================================
echo   后端接口文档: http://localhost:8000/docs
echo   前端入口:     http://localhost:5173
echo   关闭弹出的两个命令行窗口即可停止服务。
echo ==================================================
pause
