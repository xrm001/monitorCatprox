@echo off
chcp 65001 >nul
cls
echo.
echo ========================================
echo    Catprox 设备监控系统启动脚本
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
echo [2/2] 启动监控系统...
echo ========================================
echo.
echo 提示: 启动后请打开浏览器访问:
echo       http://localhost:5000
echo.
echo 按 Ctrl+C 可停止监控
echo ========================================
echo.

python main.py

echo.
echo ========================================
echo 监控系统已停止
echo ========================================
pause
