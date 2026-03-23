# 两头乌智慧养殖系统 - 接口文档

基础路径: `/api`
响应格式:
```json
{
  "code": 200,
  "data": "...",
  "message": "Success"
}
```

## 0. 认证与授权 (Authentication)

系统使用 JWT (JSON Web Token) 进行安全认证。

### 联调说明 (Frontend Dev Proxy)
前端开发环境通过 Vite 代理转发请求以避免跨域：
- 前端请求前缀：`/api`
- 代理目标后端：`http://localhost:8080`

### 登录 (Login)
用户登录并获取访问令牌。

- **方法**: `POST`
- **路径**: `/auth/login`
- **请求体**:
  ```json
  {
    "username": "admin",
    "password": "..."
  }
  ```
- **成功响应**:
  ```json
  {
    "code": 200,
    "data": {
      "token": "eyJhbGciOiJIUz...",
      "user": {
        "id": 9527,
        "name": "管理员",
        "role": "admin"
      }
    },
    "message": "Success"
  }
  ```
- **错误响应**: `401 Unauthorized` - 用户名或密码错误。

### 认证机制
- 客户端在登录成功后应将 `token` 存储在 `localStorage` 或 `HttpOnly Cookie` 中。
- 所有受保护的接口请求必须在 Header 中携带 Token：
  ```
  Authorization: Bearer <your_token_here>
  ```
- **Token 失效**: 当后端返回 `401 Unauthorized` 时，前端应清除本地 Token 并重定向至登录页。

---

## 1. 主控台 (Dashboard)

### 获取主控台统计数据
**[需认证]** 获取主控台的核心指标数据。

- **方法**: `GET`
- **路径**: `/dashboard/stats`
- **响应数据**:
  ```json
  {
    "averageTemp": 38.5,    // Number: 平均体温
    "activityLevel": 85,    // Number: 活跃度指数 (0-100)
    "alertCount": 3         // Number: 今日报警总数
  }
  ```

## 2. 实时监控 (Monitor)

### 获取摄像头列表
**[需认证]** 获取可用的监控摄像头列表及其状态。

- **方法**: `GET`
- **路径**: `/cameras`
- **响应数据**: 对象数组
  ```json
  [
    {
      "id": 1,              // Number: 摄像头 ID
      "name": "猪舍A - 北区", // String: 摄像头名称
      "status": "online",   // String: 'online' (在线) | 'offline' (离线)
      "location": "猪舍A"   // String: 物理位置
    }
  ]
  ```

## 3. 数据分析 (Analysis)

### 获取环境趋势
**[需认证]** 获取24小时环境数据（温度、湿度）。

- **方法**: `GET`
- **路径**: `/environment/trends`
- **响应数据**: 对象数组
  ```json
  [
    {
      "time": "0:00",       // String: 时间标签
      "temperature": 37.5,  // Number: 温度值
      "humidity": 55.2      // Number: 湿度值
    }
  ]
  ```

### 获取区域对比数据
**[需认证]** 获取各区域的平均温湿度对比数据。

- **方法**: `GET`
- **路径**: `/area/stats`
- **响应数据**: 对象数组
  ```json
  [
    { "name": "猪舍A", "temperature": 38.2, "humidity": 60 },
    { "name": "猪舍B", "temperature": 37.8, "humidity": 55 }
  ]
  ```

### 获取异常猪只排行榜
**[需认证]** 获取表现出异常行为或健康问题的猪只列表。

- **方法**: `GET`
- **路径**: `/pigs/abnormal`
- **响应数据**: 对象数组
  ```json
  [
    {
      "id": "PIG-001",      // String: 猪只编号
      "score": 95,          // Number: 风险/异常评分 (0-100)
      "issue": "体温过高"    // String: 主要问题描述
    }
  ]
  ```

## 4. 危险预警 (Alerts)

### 获取报警信息
**[需认证]** 获取系统报警列表，支持筛选。

- **方法**: `GET`
- **路径**: `/alerts`
- **查询参数**:
  - `search` (可选): String - 按猪只ID或类型搜索
  - `risk` (可选): String - 按风险等级筛选 ('Low', 'Medium', 'High', 'Critical')
  - `area` (可选): String - 按区域筛选 ('猪舍A', '猪舍B' 等)

- **响应数据**: 对象数组
  ```json
  [
    {
      "id": 1,                  // Number: 报警 ID
      "pigId": "PIG-001",       // String: 相关猪只 ID
      "area": "猪舍A",          // String: 位置
      "type": "发热",           // String: 报警类型
      "risk": "High",           // String: 风险等级
      "timestamp": "2023-..."   // String: 报警时间
    }
  ]
  ```

## 5. 用户与设置 (User & Settings)

### 切换猪场
(目前仅前端状态切换，未来可对接 API)
- **操作**: 顶部导航栏下拉菜单
- **功能**: 在不同猪场/基地之间切换上下文。

### 退出登录
- **操作**: 顶部导航栏用户头像下拉 -> 退出登录
- **功能**: 清除本地 Token，跳转至登录页。


---

## 6. AI Tool API (面向 AI Agent)

**设计原则**：
- 扁平化 DTO，避免嵌套超过 2 层
- 精简字段，只返回 AI 需要的核心数据
- 强制租户隔离，所有接口必须携带 `X-User-ID` Header
- 清晰的 Swagger 注解，让 LLM 能准确理解参数

**安全机制**：
- 拦截器强制校验 `X-User-ID` Header
- Service 层所有查询强制带 `user_id` 过滤
- 缺失 Header 返回 `401 Unauthorized`

### 6.1 列出猪只列表
**[需认证]** AI Agent 查询猪场内所有猪只的基础信息。

- **方法**: `POST`
- **路径**: `/api/v1/ai-tool/pigs/list`
- **请求头**:
  ```
  X-User-ID: user_123
  Content-Type: application/json
  ```
- **请求体**:
  ```json
  {
    "limit": 50,           // Number: 返回数量限制（默认 50）
    "abnormalOnly": false  // Boolean: 是否只返回异常猪只（默认 false）
  }
  ```
- **成功响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "total": 12,
      "pigs": [
        {
          "id": "PIG001",
          "breed": "金华两头乌",
          "currentWeight": 45.5,
          "dayAge": 120,
          "healthScore": 85,
          "issue": "体温偏高"
        }
      ]
    }
  }
  ```

### 6.2 查询猪只详细档案
**[需认证]** AI Agent 查询指定猪只的完整档案信息。

- **方法**: `POST`
- **路径**: `/api/v1/ai-tool/pigs/info`
- **请求头**:
  ```
  X-User-ID: user_123
  Content-Type: application/json
  ```
- **请求体**:
  ```json
  {
    "pigId": "PIG001",          // String: 猪只 ID（必填）
    "includeLifecycle": true    // Boolean: 是否包含生长周期数据（默认 true）
  }
  ```
- **成功响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "id": "PIG001",
      "breed": "金华两头乌",
      "currentWeight": 45.5,
      "dayAge": 120,
      "currentMonth": 4,
      "healthScore": 85,
      "issue": "体温偏高",
      "bodyTemp": 39.2,
      "activityLevel": 75,
      "lifecycle": [
        {"month": 1, "weight": 5.2, "dayAge": 30},
        {"month": 2, "weight": 12.8, "dayAge": 60},
        {"month": 3, "weight": 28.5, "dayAge": 90},
        {"month": 4, "weight": 45.5, "dayAge": 120}
      ]
    }
  }
  ```

### 6.3 查询异常猪只列表
**[需认证]** AI Agent 快速定位需要关注的异常个体。

- **方法**: `POST`
- **路径**: `/api/v1/ai-tool/pigs/abnormal`
- **请求头**:
  ```
  X-User-ID: user_123
  Content-Type: application/json
  ```
- **请求体**:
  ```json
  {
    "threshold": 60,  // Number: 健康评分阈值（默认 60）
    "limit": 20       // Number: 返回数量限制（默认 20）
  }
  ```
- **成功响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "count": 3,
      "pigs": [
        {
          "id": "PIG005",
          "healthScore": 75,
          "issue": "体温偏高",
          "bodyTemp": 39.8,
          "activityLevel": 45,
          "dayAge": 90
        }
      ]
    }
  }
  ```

### 6.4 获取猪场统计概览
**[需认证]** AI Agent 快速了解猪场整体状况。

- **方法**: `POST`
- **路径**: `/api/v1/ai-tool/farm/stats`
- **请求头**:
  ```
  X-User-ID: user_123
  Content-Type: application/json
  ```
- **请求体**:
  ```json
  {}  // 空对象即可
  ```
- **成功响应**:
  ```json
  {
    "code": 200,
    "message": "success",
    "data": {
      "totalPigs": 120,
      "abnormalCount": 5,
      "avgHealthScore": 82,
      "avgBodyTemp": 38.5,
      "avgActivityLevel": 75,
      "todayNewAbnormal": 2
    }
  }
  ```

### 6.5 安全说明

**租户隔离机制**：
1. 所有 AI Tool API 路径（`/api/v1/ai-tool/**`）必须携带 `X-User-ID` Header
2. 拦截器在请求到达 Controller 前强制校验 Header
3. Service 层所有 SQL 查询强制带 `user_id = #{userId}` 条件
4. 缺失 Header 返回 `401 Unauthorized`

**防止提示词注入越权**：
- AI Agent 无法通过修改 `pigId` 参数访问其他用户的数据
- 所有查询都在 SQL 层面强制过滤 `user_id`
- 即使 AI 被注入恶意提示词，也无法绕过租户隔离

**测试脚本**：
```bash
# 测试正常请求
curl -X POST "http://localhost:8080/api/v1/ai-tool/pigs/list" \
  -H "X-User-ID: demo_user_001" \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'

# 测试缺少 Header（应返回 401）
curl -X POST "http://localhost:8080/api/v1/ai-tool/pigs/list" \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'
```

---

## 附录：错误码说明

| 错误码 | 说明 |
|-------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（Token 失效或缺失 X-User-ID） |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
