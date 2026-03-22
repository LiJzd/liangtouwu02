-- ==========================================
-- 生猪信息表结构
-- ==========================================
-- 用于存储猪只的基本信息和完整生命周期数据

CREATE TABLE IF NOT EXISTS pig_info (
    -- 主键
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    
    -- 猪只标识
    pig_id VARCHAR(64) NOT NULL UNIQUE COMMENT '猪只唯一标识 ID',
    
    -- 基本信息
    breed VARCHAR(32) NOT NULL COMMENT '猪的品种（如：杜洛克、两头乌、长白、大白）',
    
    -- 生命周期数据（JSON 格式）
    lifecycle JSON NOT NULL COMMENT '生命周期数据，按月记录的数组',
    
    -- 当前状态（冗余字段，便于快速查询）
    current_month INT GENERATED ALWAYS AS (JSON_LENGTH(lifecycle)) STORED COMMENT '当前月份（根据 lifecycle 数组长度计算）',
    current_weight_kg DECIMAL(10, 2) GENERATED ALWAYS AS (
        CAST(JSON_EXTRACT(lifecycle, CONCAT('$[', JSON_LENGTH(lifecycle) - 1, '].weight_kg')) AS DECIMAL(10, 2))
    ) STORED COMMENT '当前体重（从最后一个月提取）',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX idx_pig_id (pig_id),
    INDEX idx_breed (breed),
    INDEX idx_current_month (current_month),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生猪基本信息表（含完整生命周期）';


-- ==========================================
-- 示例数据插入
-- ==========================================

INSERT INTO pig_info (pig_id, breed, lifecycle) VALUES
-- 杜洛克 1：3个月数据
('PIG001', '杜洛克', JSON_ARRAY(
    JSON_OBJECT('month', 1, 'feed_count', 45, 'feed_duration_mins', 280, 'water_count', 80, 'water_duration_mins', 160, 'weight_kg', 28.5),
    JSON_OBJECT('month', 2, 'feed_count', 50, 'feed_duration_mins', 320, 'water_count', 88, 'water_duration_mins', 175, 'weight_kg', 38.2),
    JSON_OBJECT('month', 3, 'feed_count', 52, 'feed_duration_mins', 340, 'water_count', 92, 'water_duration_mins', 185, 'weight_kg', 45.0)
)),

-- 杜洛克 2：3个月数据
('PIG002', '杜洛克', JSON_ARRAY(
    JSON_OBJECT('month', 1, 'feed_count', 48, 'feed_duration_mins', 300, 'water_count', 85, 'water_duration_mins', 170, 'weight_kg', 30.0),
    JSON_OBJECT('month', 2, 'feed_count', 54, 'feed_duration_mins', 355, 'water_count', 93, 'water_duration_mins', 198, 'weight_kg', 40.5),
    JSON_OBJECT('month', 3, 'feed_count', 56, 'feed_duration_mins', 365, 'water_count', 95, 'water_duration_mins', 200, 'weight_kg', 48.5)
)),

-- 长白 1：3个月数据（健康状况较差）
('PIG003', '长白', JSON_ARRAY(
    JSON_OBJECT('month', 1, 'feed_count', 42, 'feed_duration_mins', 260, 'water_count', 75, 'water_duration_mins', 150, 'weight_kg', 26.0),
    JSON_OBJECT('month', 2, 'feed_count', 44, 'feed_duration_mins', 280, 'water_count', 78, 'water_duration_mins', 155, 'weight_kg', 33.5),
    JSON_OBJECT('month', 3, 'feed_count', 46, 'feed_duration_mins', 290, 'water_count', 80, 'water_duration_mins', 160, 'weight_kg', 40.0)
)),

-- 大白：3个月数据（生长良好）
('PIG004', '大白', JSON_ARRAY(
    JSON_OBJECT('month', 1, 'feed_count', 50, 'feed_duration_mins', 310, 'water_count', 90, 'water_duration_mins', 180, 'weight_kg', 32.0),
    JSON_OBJECT('month', 2, 'feed_count', 55, 'feed_duration_mins', 360, 'water_count', 98, 'water_duration_mins', 195, 'weight_kg', 43.5),
    JSON_OBJECT('month', 3, 'feed_count', 58, 'feed_duration_mins', 380, 'water_count', 102, 'water_duration_mins', 205, 'weight_kg', 55.0)
)),

-- 长白 2：2个月数据
('PIG005', '长白', JSON_ARRAY(
    JSON_OBJECT('month', 1, 'feed_count', 40, 'feed_duration_mins', 250, 'water_count', 72, 'water_duration_mins', 145, 'weight_kg', 25.0),
    JSON_OBJECT('month', 2, 'feed_count', 43, 'feed_duration_mins', 270, 'water_count', 76, 'water_duration_mins', 152, 'weight_kg', 32.0)
)),

-- 两头乌 1：4个月数据
('PIG006', '两头乌', JSON_ARRAY(
    JSON_OBJECT('month', 1, 'feed_count', 38, 'feed_duration_mins', 230, 'water_count', 68, 'water_duration_mins', 135, 'weight_kg', 22.0),
    JSON_OBJECT('month', 2, 'feed_count', 40, 'feed_duration_mins', 245, 'water_count', 72, 'water_duration_mins', 142, 'weight_kg', 30.5),
    JSON_OBJECT('month', 3, 'feed_count', 42, 'feed_duration_mins', 260, 'water_count', 75, 'water_duration_mins', 148, 'weight_kg', 38.8),
    JSON_OBJECT('month', 4, 'feed_count', 44, 'feed_duration_mins', 275, 'water_count', 78, 'water_duration_mins', 155, 'weight_kg', 47.0)
)),

-- 两头乌 2：4个月数据（有健康问题）
('PIG007', '两头乌', JSON_ARRAY(
    JSON_OBJECT('month', 1, 'feed_count', 36, 'feed_duration_mins', 220, 'water_count', 65, 'water_duration_mins', 130, 'weight_kg', 21.0),
    JSON_OBJECT('month', 2, 'feed_count', 38, 'feed_duration_mins', 235, 'water_count', 68, 'water_duration_mins', 135, 'weight_kg', 28.5),
    JSON_OBJECT('month', 3, 'feed_count', 35, 'feed_duration_mins', 215, 'water_count', 62, 'water_duration_mins', 125, 'weight_kg', 35.2),
    JSON_OBJECT('month', 4, 'feed_count', 37, 'feed_duration_mins', 230, 'water_count', 65, 'water_duration_mins', 130, 'weight_kg', 42.0)
));
