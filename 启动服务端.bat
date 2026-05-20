@echo off
chcp 65001 >nul
cls
echo.
echo ========================================
echo    Catprox 监控系统 - 服务端启动
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python环境
    echo 请先安装Python 3.8+
    echo.
    pause
    exit /b 1
)

echo [√] Python环境检测成功
echo.
echo [1/2] 检查依赖包...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo [!] 检测到缺少依赖,正在安装...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [错误] 依赖安装失败
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [√] 依赖安装成功
) else (
    echo [√] 依赖包已安装
)

echo.
echo [2/2] 启动服务端监控...
echo ========================================
echo.
echo 提示: 启动后请打开浏览器访问:
echo       http://localhost:5000
echo.
echo 重要: 将你的局域网IP告诉同事
echo       让他们修改 monitor_client.py 中的 SERVER_IP
echo.
echo 按 Ctrl+C 可停止监控
echo ========================================
echo.

python monitor_server.py

echo.
echo ========================================
echo 监控系统已停止
echo ========================================
pause
