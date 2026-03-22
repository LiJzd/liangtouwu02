# 两头乌后端代码结构及内部文件作用文档

## 项目概述

两头乌智能养殖系统后端是一个基于Spring Boot 3.x的多模块Maven项目，采用分层架构设计，为智能养殖系统提供完整的后端服务支持。

### 技术栈
- **Java版本**: Java 17
- **框架**: Spring Boot 3.2.1
- **ORM框架**: MyBatis 3.0.3
- **数据库**: MySQL 8.2.0
- **安全框架**: Spring Security + JWT (jjwt 0.11.5)
- **工具库**: Lombok 1.18.30
- **连接池**: Druid 1.2.20
- **缓存**: Redis
- **AI服务**: FastAPI (Python)

---

## 项目结构

```
两头乌后端/
├── pom.xml                                    # 父POM文件，管理所有子模块
├── liangtouwu-app/                            # 应用启动模块
│   ├── pom.xml
│   └── src/main/
│       ├── java/com/liangtouwu/app/
│       │   └── LiangtouwuApplication.java     # Spring Boot启动类
│       └── resources/
│           ├── application.yml                # 主配置文件
│           ├── application-dev.yml            # 开发环境配置
│           ├── application-prod.yml           # 生产环境配置
│           ├── application-test.yml           # 测试环境配置
│           ├── schema.sql                     # 数据库表结构
│           └── data.sql                       # 初始化数据
├── liangtouwu-domain/                         # 领域模型模块
│   ├── pom.xml
│   └── src/main/java/com/liangtouwu/domain/
│       ├── entity/                            # 实体类
│       ├── dto/                               # 数据传输对象
│       └── auth/                              # 认证相关类
├── liangtouwu-business/                       # 业务逻辑模块
│   ├── pom.xml
│   └── src/main/
│       ├── java/com/liangtouwu/business/
│       │   ├── controller/                    # 控制器层
│       │   ├── service/                       # 服务层
│       │   │   └── impl/                      # 服务实现
│       │   ├── mapper/                        # MyBatis Mapper接口
│       │   └── dto/                           # 业务DTO
│       └── resources/mapper/                  # MyBatis XML映射文件
├── liangtouwu-common/                         # 公共模块
│   ├── pom.xml
│   └── src/main/java/com/liangtouwu/common/
│       ├── response/                          # 统一响应封装
│       ├── security/                          # 安全配置
│       ├── exception/                         # 异常处理
│       └── util/                              # 工具类
├── cot_inference_service.py                   # AI推理服务（Python）
├── query_db.py                                # 数据库查询脚本
└── test_login.py                              # 登录测试脚本
```

---

## 模块详解

### 1. liangtouwu-app（应用启动模块）

**作用**: 项目的入口模块，负责启动Spring Boot应用，整合所有子模块。

**核心文件**:

- **LiangtouwuApplication.java**
  - Spring Boot应用主类
  - 配置组件扫描范围：`com.liangtouwu`
  - 配置MyBatis Mapper扫描：`com.liangtouwu.business.mapper`

- **application.yml**
  - 服务器上下文路径：`/api`
  - MyBatis配置：XML映射文件位置、驼峰命名转换
  - AI服务配置：FastAPI基础URL、连接超时、读取超时

- **schema.sql**
  - 定义数据库表结构：
    - `camera`: 摄像头信息表
    - `environment_trend`: 环境趋势数据表
    - `pig`: 猪只信息表
    - `alert`: 报警信息表
    - `sys_user`: 系统用户表

- **data.sql**
  - 初始化测试数据
  - 包含摄像头、环境数据、猪只信息、报警记录、用户账户

**依赖关系**: 依赖 liangtouwu-business 和 liangtouwu-common

---

### 2. liangtouwu-domain（领域模型模块）

**作用**: 定义系统的领域模型，包括实体类、DTO和认证相关类。

**核心文件**:

#### entity包（实体类）

- **Pig.java**
  - 猪只实体，对应数据库`pig`表
  - 字段：
    - `id`: 猪只编号（主键）
    - `score`: 风险/异常评分（0-100）
    - `issue`: 主要问题描述
    - `bodyTemp`: 体温（摄氏度）
    - `activityLevel`: 活跃度（0-100）

- **Alert.java**
  - 报警实体，对应数据库`alert`表
  - 字段：
    - `id`: 报警ID（主键）
    - `pigId`: 相关猪只ID
    - `area`: 发生位置
    - `type`: 报警类型（发热、受伤等）
    - `risk`: 风险等级（Low/Medium/High/Critical）
    - `timestamp`: 报警时间

- **Camera.java**
  - 摄像头实体，对应数据库`camera`表
  - 字段：
    - `id`: 摄像头ID
    - `name`: 摄像头名称
    - `status`: 状态（online/offline）
    - `location`: 位置

- **EnvironmentTrend.java**
  - 环境趋势实体，对应数据库`environment_trend`表
  - 字段：
    - `id`: 记录ID
    - `time`: 时间
    - `area`: 区域
    - `temperature`: 温度
    - `humidity`: 湿度

- **SysUser.java**
  - 系统用户实体，对应数据库`sys_user`表
  - 字段：
    - `id`: 用户ID
    - `username`: 用户名
    - `password`: 密码（加密）
    - `role`: 角色
    - `createdAt`: 创建时间

#### dto包（数据传输对象）

- **DashboardStats.java**
  - 仪表板统计数据
  - 字段：
    - `averageTemp`: 平均体温
    - `activityLevel`: 平均活跃度
    - `alertCount`: 报警数量

- **AreaStats.java**
  - 区域统计数据

#### auth包（认证相关）

- **LoginRequest.java**
  - 登录请求DTO
  - 字段：
    - `username`: 用户名
    - `password`: 密码

- **JwtResponse.java**
  - JWT响应DTO
  - 字段：
    - `token`: JWT令牌
    - `type`: 令牌类型
    - `username`: 用户名
    - `role`: 角色

**依赖关系**: 无依赖，被其他模块依赖

---

### 3. liangtouwu-business（业务逻辑模块）

**作用**: 实现核心业务逻辑，包括控制器、服务层和数据访问层。

**核心文件**:

#### controller包（控制器层）

- **AuthController.java**
  - 认证控制器
  - 端点：
    - `POST /api/auth/login`: 用户登录

- **DashboardController.java**
  - 仪表板控制器
  - 端点：
    - `GET /api/dashboard/stats`: 获取仪表板统计数据

- **MonitorController.java**
  - 监控控制器
  - 端点：
    - `GET /api/cameras`: 获取摄像头列表

- **AnalysisController.java**
  - 分析控制器
  - 端点：
    - `GET /api/environment/trends`: 获取环境趋势数据
    - `GET /api/area/stats`: 获取区域统计数据
    - `GET /api/pigs/abnormal`: 获取异常猪只列表

- **AlertController.java**
  - 报警控制器
  - 端点：
    - `GET /api/alerts`: 获取报警列表（支持搜索、风险等级、区域过滤）

- **InspectionController.java**
  - 检查报告控制器
  - 端点：
    - `POST /api/inspection/generate`: 生成检查报告（同步）
    - `POST /api/inspection/generate/stream`: 生成检查报告（流式）
    - `GET /api/inspection/health`: AI服务健康检查

#### service包（服务层）

- **AuthService.java / AuthServiceImpl.java**
  - 认证服务
  - 功能：用户登录、JWT令牌生成

- **DashboardService.java / DashboardServiceImpl.java**
  - 仪表板服务
  - 功能：计算平均体温、平均活跃度、今日报警数量

- **MonitorService.java / MonitorServiceImpl.java**
  - 监控服务
  - 功能：获取摄像头列表

- **AnalysisService.java / AnalysisServiceImpl.java**
  - 分析服务
  - 功能：获取环境趋势、区域统计、异常猪只

- **AlertService.java / AlertServiceImpl.java**
  - 报警服务
  - 功能：查询报警列表，支持多条件过滤

- **InspectionService.java / InspectionServiceImpl.java**
  - 检查报告服务
  - 功能：调用AI服务生成检查报告，支持同步和流式响应

#### mapper包（MyBatis Mapper接口）

- **PigMapper.java**
  - 猪只数据访问接口
  - 方法：
    - `findAbnormalPigs()`: 查找异常猪只
    - `getAverageBodyTemp()`: 获取平均体温
    - `getAverageActivityLevel()`: 获取平均活跃度

- **AlertMapper.java**
  - 报警数据访问接口
  - 方法：
    - `getAlerts()`: 查询报警列表
    - `countTodayAlerts()`: 统计今日报警数量

- **CameraMapper.java**
  - 摄像头数据访问接口

- **EnvironmentTrendMapper.java**
  - 环境趋势数据访问接口

- **SysUserMapper.java**
  - 用户数据访问接口

#### resources/mapper包（MyBatis XML映射文件）

- **PigMapper.xml**
  - 猪只SQL映射
  - 包含异常猪只查询、平均体温计算、平均活跃度计算

- **AlertMapper.xml**
  - 报警SQL映射
  - 包含报警列表查询、今日报警统计

- **CameraMapper.xml**
  - 摄像头SQL映射

- **EnvironmentTrendMapper.xml**
  - 环境趋势SQL映射

#### dto包（业务DTO）

- **InspectionGenerateRequest.java**
  - 检查报告生成请求
  - 字段：
    - `pigId`: 猪只ID
    - `behaviorEvent`: 行为事件
    - `iotEnvironment`: IoT环境数据

- **InspectionGenerateResponse.java**
  - 检查报告生成响应
  - 字段：
    - `code`: 状态码
    - `message`: 消息
    - `pigId`: 猪只ID
    - `report`: 报告内容
    - `error`: 错误信息
    - `metadata`: 元数据

**依赖关系**: 依赖 liangtouwu-domain 和 liangtouwu-common

---

### 4. liangtouwu-common（公共模块）

**作用**: 提供公共功能，包括统一响应封装、安全配置、异常处理和工具类。

**核心文件**:

#### response包（统一响应封装）

- **ApiResponse.java**
  - 统一API响应格式
  - 字段：
    - `code`: 状态码
    - `data`: 响应数据
    - `message`: 消息
  - 静态方法：
    - `success(T data)`: 成功响应
    - `error(int code, String message)`: 错误响应

#### security包（安全配置）

- **SecurityConfig.java**
  - Spring Security配置类
  - 功能：
    - 密码编码器配置（BCrypt）
    - CORS跨域配置
    - 安全过滤器链配置
    - 无状态会话管理
    - 禁用CSRF保护

- **JwtAuthenticationFilter.java**
  - JWT认证过滤器
  - 功能：拦截请求，验证JWT令牌

- **JwtUtils.java**
  - JWT工具类
  - 功能：生成JWT令牌、解析JWT令牌、验证令牌有效性

#### exception包（异常处理）

- **GlobalExceptionHandler.java**
  - 全局异常处理器
  - 功能：统一处理各类异常，返回格式化的错误响应

#### util包（工具类）

- **JwtUtils.java**
  - JWT令牌生成和解析工具

**依赖关系**: 依赖 liangtouwu-domain，被其他模块依赖

---

### 5. Python辅助脚本

#### cot_inference_service.py
**作用**: AI推理服务，基于多模态链式思维（CoT）生成诊断报告。

**核心组件**:

- **BehaviorAnalystAgent**: 行为分析代理
  - 解读行为事件（如扎堆、不进食）
  - 评估行为严重程度

- **EnvironmentIoTAgent**: 环境IoT代理
  - 评估环境温度和湿度
  - 判断环境风险等级

- **ChiefVeterinaryAgent**: 兽医代理
  - 使用RAG（检索增强生成）查询兽医知识库
  - 使用LLM生成诊断报告
  - 提供回退机制（当RAG/LLM不可用时）

- **MultimodalCommittee**: 多模态委员会
  - 协调各代理执行顺序
  - 管理超时和错误处理

**API端点**:
- `POST /api/v1/cot/diagnose`: 诊断端点

#### query_db.py
**作用**: 数据库查询辅助脚本

#### test_login.py
**作用**: 登录功能测试脚本

---

## 数据库设计

### 表结构

#### camera（摄像头表）
```sql
CREATE TABLE camera (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    location VARCHAR(255) NOT NULL
);
```

#### environment_trend（环境趋势表）
```sql
CREATE TABLE environment_trend (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    time VARCHAR(50) NOT NULL,
    area VARCHAR(255),
    temperature DECIMAL(5,2) NOT NULL,
    humidity DECIMAL(5,2) NOT NULL
);
```

#### pig（猪只表）
```sql
CREATE TABLE pig (
    id VARCHAR(50) PRIMARY KEY,
    score INT NOT NULL,
    issue VARCHAR(255),
    body_temp DECIMAL(4,2),
    activity_level INT
);
```

#### alert（报警表）
```sql
CREATE TABLE alert (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    pig_id VARCHAR(50),
    area VARCHAR(255),
    type VARCHAR(255),
    risk VARCHAR(50),
    timestamp VARCHAR(50) NOT NULL
);
```

#### sys_user（系统用户表）
```sql
CREATE TABLE sys_user (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## API接口文档

### 认证接口

#### 登录
- **URL**: `POST /api/auth/login`
- **请求体**:
```json
{
  "username": "admin",
  "password": "password"
}
```
- **响应**:
```json
{
  "code": 200,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "type": "Bearer",
    "username": "admin",
    "role": "admin"
  },
  "message": "Success"
}
```

### 仪表板接口

#### 获取统计数据
- **URL**: `GET /api/dashboard/stats`
- **响应**:
```json
{
  "code": 200,
  "data": {
    "averageTemp": 38.5,
    "activityLevel": 75,
    "alertCount": 5
  },
  "message": "Success"
}
```

### 监控接口

#### 获取摄像头列表
- **URL**: `GET /api/cameras`
- **响应**:
```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "name": "猪舍A - 北区",
      "status": "online",
      "location": "猪舍A"
    }
  ],
  "message": "Success"
}
```

### 分析接口

#### 获取环境趋势
- **URL**: `GET /api/environment/trends`
- **响应**:
```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "time": "0:00",
      "area": "猪舍A",
      "temperature": 37.5,
      "humidity": 55.2
    }
  ],
  "message": "Success"
}
```

#### 获取区域统计
- **URL**: `GET /api/area/stats`
- **响应**:
```json
{
  "code": 200,
  "data": [
    {
      "area": "猪舍A",
      "pigCount": 50,
      "alertCount": 2
    }
  ],
  "message": "Success"
}
```

#### 获取异常猪只
- **URL**: `GET /api/pigs/abnormal`
- **响应**:
```json
{
  "code": 200,
  "data": [
    {
      "id": "PIG-001",
      "score": 95,
      "issue": "体温过高",
      "bodyTemp": 40.5,
      "activityLevel": 60
    }
  ],
  "message": "Success"
}
```

### 报警接口

#### 获取报警列表
- **URL**: `GET /api/alerts`
- **查询参数**:
  - `search`: 搜索关键词
  - `risk`: 风险等级（Low/Medium/High/Critical）
  - `area`: 区域
- **响应**:
```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "pigId": "PIG-001",
      "area": "猪舍A",
      "type": "发热",
      "risk": "High",
      "timestamp": "2023-10-27 10:00:00"
    }
  ],
  "message": "Success"
}
```

### 检查报告接口

#### 生成检查报告（同步）
- **URL**: `POST /api/inspection/generate`
- **请求体**:
```json
{
  "pigId": "PIG-001",
  "behaviorEvent": "huddling_5_mins",
  "iotEnvironment": {
    "temperature": 25.0,
    "humidity": 60.0
  }
}
```
- **响应**:
```json
{
  "code": 200,
  "message": "Success",
  "pigId": "PIG-001",
  "report": "# 诊断报告\n...",
  "error": null,
  "metadata": {}
}
```

#### 生成检查报告（流式）
- **URL**: `POST /api/inspection/generate/stream`
- **Content-Type**: `text/event-stream`
- **响应**: Server-Sent Events流

#### AI服务健康检查
- **URL**: `GET /api/inspection/health`
- **响应**:
```json
{
  "status": "UP",
  "service": "pig-inspection-ai"
}
```

---

## 配置说明

### application.yml（主配置）

```yaml
server:
  servlet:
    context-path: /api

mybatis:
  mapper-locations: classpath*:mapper/*.xml
  configuration:
    map-underscore-to-camel-case: true

ai:
  fastapi:
    base-url: ${FASTAPI_BASE_URL:http://localhost:8000}
    connect-timeout-ms: ${FASTAPI_CONNECT_TIMEOUT_MS:3000}
    read-timeout-ms: ${FASTAPI_READ_TIMEOUT_MS:180000}
```

### 环境变量

- `FASTAPI_BASE_URL`: AI服务基础URL（默认：http://localhost:8000）
- `FASTAPI_CONNECT_TIMEOUT_MS`: AI服务连接超时（默认：3000ms）
- `FASTAPI_READ_TIMEOUT_MS`: AI服务读取超时（默认：180000ms）

---

## 构建和运行

### 构建项目
```bash
mvn clean package
```

### 运行项目
```bash
java -jar liangtouwu-app/target/liangtouwu-app-1.0.0-SNAPSHOT.jar
```

### 运行AI服务
```bash
python cot_inference_service.py
```

---

## 安全配置

### CORS配置
允许的源：
- http://localhost:5173
- http://127.0.0.1:5173
- http://localhost:3000
- http://127.0.0.1:3000

允许的方法：GET, POST, PUT, DELETE, PATCH, OPTIONS

### JWT认证
- 签名算法：HS256
- 令牌类型：Bearer
- 密码加密：BCrypt

---

## 依赖关系图

```
liangtouwu-app
    ├── liangtouwu-business
    │   ├── liangtouwu-domain
    │   └── liangtouwu-common
    │       └── liangtouwu-domain
    └── liangtouwu-common
        └── liangtouwu-domain
```

---

## 开发规范

### 分层架构
1. **Controller层**: 处理HTTP请求，参数验证
2. **Service层**: 业务逻辑处理
3. **Mapper层**: 数据访问
4. **Entity层**: 数据模型定义

### 命名规范
- Controller: `*Controller`
- Service: `*Service` / `*ServiceImpl`
- Mapper: `*Mapper`
- Entity: 实体类名
- DTO: 功能描述 + `Request` / `Response`

### 统一响应
所有接口使用`ApiResponse<T>`统一响应格式

---

## 测试账户

### 默认用户
- **管理员**
  - 用户名: `admin`
  - 密码: `password`
  - 角色: `admin`

- **普通用户**
  - 用户名: `user`
  - 密码: `password`
  - 角色: `user`

---

## 常见问题

### 1. 数据库连接失败
检查MySQL服务是否启动，配置文件中的数据库连接信息是否正确。

### 2. AI服务调用失败
检查AI服务是否启动，`FASTAPI_BASE_URL`配置是否正确。

### 3. CORS跨域问题
检查前端请求的URL是否在CORS允许的源列表中。

---

## 扩展建议

### 1. 添加新功能模块
在`liangtouwu-business`模块中创建新的Controller、Service和Mapper。

### 2. 添加新的实体
在`liangtouwu-domain`模块中创建新的Entity类。

### 3. 添加新的工具类
在`liangtouwu-common`模块的util包中创建工具类。

### 4. 集成新的AI服务
参考`InspectionServiceImpl`的实现方式，调用外部AI服务。

---

## 总结

两头乌后端采用标准的Spring Boot分层架构，模块划分清晰，职责明确。项目使用MyBatis进行数据持久化，Spring Security进行安全认证，JWT进行令牌管理。通过与AI服务的集成，实现了智能诊断功能。整体架构易于扩展和维护，适合中小型智能养殖系统的开发需求。