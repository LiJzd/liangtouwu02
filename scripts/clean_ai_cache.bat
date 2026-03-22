@echo off
chcp 65001 >nul
echo ========================================
echo 清理 AI 服务缓存和临时文件
echo ========================================
echo.

cd ai-service

echo [1/5] 清理 Python 缓存...
if exist "__pycache__" rd /s /q "__pycache__" 2>nul
if exist "v1\__pycache__" rd /s /q "v1\__pycache__" 2>nul
if exist "v1\logic\__pycache__" rd /s /q "v1\logic\__pycache__" 2>nul
if exist "v1\objects\__pycache__" rd /s /q "v1\objects\__pycache__" 2>nul
if exist "v1\common\__pycache__" rd /s /q "v1\common\__pycache__" 2>nul
if exist "pig_rag\__pycache__" rd /s /q "pig_rag\__pycache__" 2>nul
if exist "pig_rag\math_engine\__pycache__" rd /s /q "pig_rag\math_engine\__pycache__" 2>nul
echo 完成

echo [2/5] 清理日志文件...
if exist "logs\algorithm.log" del /q "logs\algorithm.log" 2>nul
if exist "botpy.log*" del /q "botpy.log*" 2>nul
echo 完成

echo [3/5] 清理临时文件...
if exist "*.pyc" del /q "*.pyc" 2>nul
if exist ".pytest_cache" rd /s /q ".pytest_cache" 2>nul
echo 完成

echo [4/5] 清理重复的数据库...
if exist "pig_lifecycle_chroma_db" (
    echo 保留 pig_lifecycle_chroma_db
)
echo 完成

echo [5/5] 清理重复的模型目录...
if exist "yolo模型" (
    echo 发现重复的 YOLO 模型目录
    echo 模型已移至 resources/assets/
    rd /s /q "yolo模型" 2>nul
)
echo 完成

cd ..

echo.
echo ========================================
echo 清理完成
echo ========================================
echo.
pause
