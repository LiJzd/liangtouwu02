-- 三端联调统一数据库初始化脚本 (MySQL)
-- 数据库名建议: liangtowwu

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS sys_user;
CREATE TABLE sys_user (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS pig;
CREATE TABLE pig (
    id VARCHAR(64) PRIMARY KEY COMMENT '猪只唯一标识 (耳标号)',
    score INT DEFAULT 100 COMMENT '健康评分 (0-100)',
    issue VARCHAR(255) COMMENT '异常问题描述',
    body_temp DECIMAL(10, 2) COMMENT '实时体温',
    activity_level INT COMMENT '活跃度 (0-100)',
    breed VARCHAR(32) NOT NULL COMMENT '品种',
    lifecycle JSON COMMENT '生命周期数据 (AI 预测使用)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS alert;
CREATE TABLE alert (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    pig_id VARCHAR(64) COMMENT '关联猪只 ID',
    area VARCHAR(100) COMMENT '发生位置',
    type VARCHAR(50) COMMENT '报警类型',
    risk VARCHAR(20) COMMENT '风险等级 (Low, Medium, High, Critical)',
    timestamp VARCHAR(50) COMMENT '报警时间戳',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS camera;
CREATE TABLE camera (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'online' COMMENT 'online/offline',
    location VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS daily_briefings;
CREATE TABLE daily_briefings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    briefing_date DATE NOT NULL,
    content TEXT,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS environment_trend;
CREATE TABLE environment_trend (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    time VARCHAR(20) NOT NULL COMMENT '采样点 (如 08:00)',
    area VARCHAR(50) COMMENT '区域',
    temperature DECIMAL(10, 2) COMMENT '环境温度',
    humidity DECIMAL(10, 2) COMMENT '环境湿度'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==========================================
-- 示例初始数据
-- ==========================================

-- 初始用户 (admin/admin123)
INSERT IGNORE INTO sys_user (username, password, nickname, status) 
VALUES ('admin', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.vK56.vT.4/E7fX8K0Z0D8T.', '管理员', '0');

-- 初始猪只数据 (扩容至 10 头以展示群体规模)
INSERT IGNORE INTO pig (id, breed, score, issue, body_temp, activity_level, lifecycle) VALUES
('PIG001', '两头乌', 95, '健康', 38.5, 80, JSON_ARRAY(
    JSON_OBJECT('month', 1, 'feed_count', 45, 'feed_duration_mins', 280, 'water_count', 80, 'water_duration_mins', 160, 'weight_kg', 12.5),
    JSON_OBJECT('month', 2, 'feed_count', 50, 'feed_duration_mins', 320, 'water_count', 88, 'water_duration_mins', 175, 'weight_kg', 24.8),
    JSON_OBJECT('month', 3, 'feed_count', 52, 'feed_duration_mins', 340, 'water_count', 92, 'water_duration_mins', 185, 'weight_kg', 38.2)
)),
('PIG002', '两头乌', 60, '疑似温热', 39.8, 30, JSON_ARRAY(
    JSON_OBJECT('month', 1, 'feed_count', 48, 'feed_duration_mins', 300, 'water_count', 85, 'water_duration_mins', 170, 'weight_kg', 13.2),
    JSON_OBJECT('month', 2, 'feed_count', 54, 'feed_duration_mins', 355, 'water_count', 93, 'water_duration_mins', 198, 'weight_kg', 25.5)
)),
('PIG003', '两头乌', 98, '健康', 38.4, 85, NULL),
('PIG004', '两头乌', 92, '健康', 38.6, 78, NULL),
('PIG005', '两头乌', 95, '健康', 38.4, 82, NULL),
('PIG006', '两头乌', 91, '健康', 38.7, 75, NULL),
('PIG007', '两头乌', 45, '食欲下降', 39.5, 40, NULL),
('PIG008', '两头乌', 96, '健康', 38.5, 88, NULL),
('PIG009', '两头乌', 88, '健康', 38.3, 70, NULL),
('PIG010', '两头乌', 94, '健康', 38.6, 84, NULL);

-- 初始摄像头
INSERT IGNORE INTO camera (name, status, location) VALUES 
('猪舍A-北区', 'online', '猪舍A'),
('育肥区-01', 'online', '育肥舍'),
('监控廊道', 'offline', '办公区');

-- 初始环境趋势 (24小时示例)
INSERT IGNORE INTO environment_trend (time, area, temperature, humidity) VALUES
('08:00', '猪舍A', 25.5, 60.0),
('12:00', '猪舍A', 28.2, 55.0),
('16:00', '猪舍A', 27.8, 58.0),
('20:00', '猪舍A', 24.5, 65.0);

SET FOREIGN_KEY_CHECKS = 1;
