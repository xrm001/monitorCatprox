@echo off
chcp 65001 >nul
echo.
echo 正在停止旧的服务...
echo.

REM 查找并停止占用5000端口的Python进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo 停止进程 PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 2 /nobreak >nul

echo.
echo 正在启动服务端...
echo.

python monitor_server.py