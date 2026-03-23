# QQ 机器人图片发送配置指南

## 问题说明

QQ 机器人的 `post_c2c_file` API 需要一个可从公网访问的 HTTP URL 来上传图片。由于以下原因，图片发送功能需要额外配置：

1. QQ 服务器需要能够访问图片 URL
2. 免费图床服务不稳定或被 QQ 服务器屏蔽
3. 本地文件路径无法直接使用

## 解决方案

### 方案 1：使用内网穿透（推荐用于开发测试）

使用 ngrok、frp 或 cpolar 等工具将本地 FastAPI 服务暴露到公网：

#### 使用 ngrok

1. 下载并安装 ngrok：https://ngrok.com/download
2. 启动 FastAPI 服务（端口 8000）
3. 在另一个终端运行：
   ```bash
   ngrok http 8000
   ```
4. 复制 ngrok 提供的公网 URL（如 `https://xxxx.ngrok.io`）
5. 在 `.env` 文件中配置：
   ```
   PUBLIC_URL=https://xxxx.ngrok.io
   ```
6. 重启 QQ 机器人

#### 使用 cpolar（国内）

1. 注册并安装 cpolar：https://www.cpolar.com/
2. 启动 FastAPI 服务（端口 8000）
3. 运行：
   ```bash
   cpolar http 8000
   ```
4. 配置 PUBLIC_URL

### 方案 2：使用云服务器（推荐用于生产环境）

1. 将应用部署到有公网 IP 的云服务器（阿里云、腾讯云等）
2. 配置域名和 SSL 证书
3. 在 `.env` 中配置：
   ```
   PUBLIC_URL=https://your-domain.com
   ```

### 方案 3：使用有效的图床 API Key

如果有可靠的图床服务 API key，可以配置：

```env
IMGBB_API_KEY=your_valid_api_key
```

获取 ImgBB API Key：https://api.imgbb.com/

## 当前状态

目前图片发送功能已实现，但由于缺少公网访问配置，暂时只能发送文本消息。配置完成后，机器人将能够：

1. 调用 `capture_pig_farm_snapshot` 工具截取猪场视频
2. 使用 YOLO 进行目标检测并绘制检测框
3. 将图片上传到图床或本地服务器
4. 通过 QQ 机器人发送给用户

## 代码实现

图片发送逻辑位于 `ai-service/bot_runner.py` 的 `reply_func` 函数中，支持：

- 自动尝试多个图床服务
- 降级到本地静态文件服务（需要 PUBLIC_URL）
- 失败时自动降级为纯文本消息

## 测试

配置完成后，向机器人发送"我想看看猪场现在是怎么样的"，机器人应该能够返回带检测框的图片。
