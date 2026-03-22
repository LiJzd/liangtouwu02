# Bugfix Requirements Document

## Introduction

Spring Boot后端项目存在多个严重错误,导致应用无法正常运行。主要问题包括:
1. ~~CameraService接口完全缺失~~ ✅ 已修复
2. ~~DailyBriefingService.java中导入路径错误~~ ✅ 已修复
3. ~~重复的API端点映射~~ ✅ 已修复
4. MyBatis Mapper参数绑定错误 - DailyBriefingMapper.xml中使用arg0而非命名参数
5. AI服务端点404错误 - 需要确认AI服务是否运行

## Bug Analysis

### 已修复的问题 ✅

#### 1. 重复端点映射
- 问题: DashboardController 和 AnalysisController 都映射了 `/dashboard/stats`
- 解决: 从 AnalysisController 中删除重复端点

#### 2. 缺少 /api 前缀
- 问题: 前端请求 `/api/cameras` 但后端没有 `/api` 前缀
- 解决: 在 application.yml 中添加 `server.servlet.context-path: /api`

### 当前待修复问题 🔧

#### 3. MyBatis 参数绑定错误

**Current Behavior (Defect)**

3.1 WHEN 调用 DailyBriefingMapper.findHistory(limit) 时 THEN 抛出异常 "Parameter 'arg0' not found. Available parameters are [limit, param1]"

3.2 WHEN 调用 DailyBriefingMapper.findByDate(date) 时 THEN 可能抛出类似的参数绑定异常

**Expected Behavior (Correct)**

3.3 WHEN 调用 DailyBriefingMapper.findHistory(limit) 时 THEN 应该使用 #{limit} 参数成功执行查询

3.4 WHEN 调用 DailyBriefingMapper.findByDate(date) 时 THEN 应该使用 #{date} 参数成功执行查询

**解决方案**: ✅ 已修复 - 将 XML 中的 #{arg0} 改为 #{limit} 和 #{date}

#### 4. AI 服务连接问题

**Current Behavior (Defect)**

4.1 WHEN Spring Boot 调用 http://localhost:8000/api/v1/inspection/briefing 时 THEN 返回 404 Not Found

4.2 WHEN 生成每日简报时 THEN 无法获取 AI 分析结果

**Expected Behavior (Correct)**

4.3 WHEN Spring Boot 调用 AI 服务时 THEN 应该成功返回简报数据

4.4 WHEN AI 服务运行在 localhost:8000 时 THEN 端点 /api/v1/inspection/briefing 应该可访问

**可能原因**:
- AI 服务(FastAPI)没有运行
- AI 服务运行在不同的端口
- 端点路径配置不匹配

**检查步骤**:
1. 确认 AI 服务是否运行: 访问 http://localhost:8000/docs
2. 检查端点是否存在: POST /api/v1/inspection/briefing
3. 如果服务未运行,执行启动脚本

### Unchanged Behavior (Regression Prevention)

5.1 WHEN 其他 Mapper 接口被调用时 THEN 系统应该继续正常工作

5.2 WHEN 其他 API 端点被访问时 THEN 系统应该继续正常工作

5.3 WHEN 数据库查询执行时 THEN 系统应该继续正常工作
