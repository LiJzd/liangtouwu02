@echo off
chcp 65001 > nul
setlocal
echo ==========================================
echo   掌上明猪 AI 算法中枢 - 启动脚本
echo ==========================================

:: 自动定位项目目录
set "PROJECT_ROOT=%~dp0"
set "AI_DIR=%PROJECT_ROOT%两头乌ai端"

if not exist "%AI_DIR%" (
    echo [错误] 找不到目录: %AI_DIR%
    echo 请确保脚本位于项目根目录下。
    pause
    exit /b 1
)

cd /d "%AI_DIR%"
echo 工作目录: %cd%

:: 检查 Python 路径
set "PYTHON_EXE=C:\Users\lost\.conda\envs\ai_competition\python.exe"
if not exist "%PYTHON_EXE%" (
    echo [错误] 找不到指定环境的 Python: %PYTHON_EXE%
    pause
    exit /b 1
)

echo 正在启动 AI 服务...
"%PYTHON_EXE%" main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [严重错误] AI 服务异常退出 (错误码: %ERRORLEVEL%)
    pause
)
