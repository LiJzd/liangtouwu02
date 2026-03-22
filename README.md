# 两头乌智慧养殖系统

基于 AI 的智能猪场管理系统，集成视觉识别、数据分析和智能对话功能。

## 快速开始

### 一键启动所有服务
```bash
scripts\start-all.bat
```

### 访问地址
- 前端: http://localhost:5173
- 后端: http://localhost:8080
- AI服务: http://localhost:8000

## 项目结构

```
两头乌/
├── backend/        # Spring Boot 后端
├── frontend/       # Vue 3 前端
├── ai-service/     # FastAPI AI服务 (ReAct Agent + YOLO)
├── database/       # 数据库脚本
├── resources/      # 共享资源 (模型、视频)
├── scripts/        # 启动脚本
└── docs/           # 项目文档
```

## 主要功能

- 🐷 猪场实时监控
- 📊 数据可视化分析
- 🤖 AI 智能对话 (ReAct模式)
- 📷 视频图像识别 (YOLO)
- 💬 QQ Bot 集成

## 技术栈

- **后端**: Spring Boot + MySQL
- **前端**: Vue 3 + Vite + TailwindCSS
- **AI服务**: FastAPI + LangChain + YOLO + ChromaDB

## 文档

- [快速开始](docs/快速开始.md) - 5分钟快速启动指南
- [项目结构](docs/项目结构说明.md) - 详细的目录结构说明
- [项目架构](docs/项目架构.md) - 系统架构设计

## 开发环境

- Node.js 18+
- Java 17+
- Python 3.10+
- MySQL 8.0+

## 许可证

MIT License
