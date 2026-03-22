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
    "stockCount": 1580,     // Number: 存栏数
    "healthRate": 99.2,     // Number: 健康率 (百分比)
    "averageTemp": 38.4,    // Number: 平均体温
    "alertCount": 2         // Number: 今日报警总数
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
