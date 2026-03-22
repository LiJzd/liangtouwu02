@echo off
chcp 65001 >nul
echo ========================================
echo 启动所有服务
echo ========================================
echo.

echo [1/3] 启动后端 (Spring Boot)...
start "后端服务" cmd /k "cd backend && mvn spring-boot:run"
timeout /t 3 >nul

echo [2/3] 启动前端 (Vue 3)...
start "前端服务" cmd /k "cd frontend && npm run dev"
timeout /t 3 >nul

echo [3/3] 启动AI服务 (FastAPI)...
start "AI服务" cmd /k "cd ai-service && python main.py"

echo.
echo ========================================
echo 所有服务已启动
echo ========================================
echo.
echo 后端: http://localhost:8080
echo 前端: http://localhost:5173
echo AI服务: http://localhost:8000
echo.
pause
