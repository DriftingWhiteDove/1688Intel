@echo off
title 1688智选 — 启动助手
cd /d %~dp0

echo ========================================
echo     1688智选 — 启动助手
echo ========================================
echo.
echo 第一步：请确保 Chrome 已经登录 1688.com
echo.
echo 第二步：关闭所有 Chrome 窗口（重要！）
echo 按任意键继续...
pause >nul

echo 正在启动 Chrome（远程调试模式）...
start "" "chrome.exe" --remote-debugging-port=9222 --no-first-run
echo Chrome 已启动，请在 Chrome 中登录 1688.com（如果未登录）
echo.
echo 第三步：启动 1688智选 服务...
echo.

call venv\Scripts\activate.bat
uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
