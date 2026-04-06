-- 每日简报表
CREATE TABLE IF NOT EXISTS daily_briefings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    briefing_date DATE NOT NULL,
    content TEXT,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 系统用户表
CREATE TABLE IF NOT EXISTS sys_user (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    nickname VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(20),
    avatar VARCHAR(255),
    status CHAR(1) DEFAULT '0',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 猪只信息表
CREATE TABLE IF NOT EXISTS pig (
    id VARCHAR(64) PRIMARY KEY COMMENT '猪只唯一标识 (耳标号)',
    score INT DEFAULT 100 COMMENT '健康评分 (0-100)',
    issue VARCHAR(255) COMMENT '异常问题描述',
    body_temp DECIMAL(10, 2) COMMENT '实时体温',
    activity_level INT COMMENT '活跃度 (0-100)',
    breed VARCHAR(32) NOT NULL COMMENT '品种',
    lifecycle JSON COMMENT '生命周期数据 (AI 预测使用)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 告警信息表
CREATE TABLE IF NOT EXISTS alert (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    pig_id VARCHAR(64) COMMENT '关联猪只 ID',
    area VARCHAR(100) COMMENT '发生位置',
    type VARCHAR(50) COMMENT '报警类型',
    risk VARCHAR(20) COMMENT '风险等级 (Low, Medium, High, Critical)',
    timestamp VARCHAR(50) COMMENT '报警时间戳',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 摄像头表
CREATE TABLE IF NOT EXISTS camera (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'online' COMMENT 'online/offline',
    location VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 环境趋势表
CREATE TABLE IF NOT EXISTS environment_trend (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    time VARCHAR(20) NOT NULL COMMENT '采样点 (如 08:00)',
    area VARCHAR(50) COMMENT '区域',
    temperature DECIMAL(10, 2) COMMENT '环境温度',
    humidity DECIMAL(10, 2) COMMENT '环境湿度'
);
