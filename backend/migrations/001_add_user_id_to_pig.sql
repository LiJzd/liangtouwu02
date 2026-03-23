-- ============================================
-- 数据库迁移脚本: 添加租户隔离字段
-- 版本: 001
-- 日期: 2026-03-22
-- 描述: 为 pig 表添加 user_id 字段实现租户隔离
-- ============================================

-- 检查字段是否已存在（MySQL 8.0+）
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() 
      AND TABLE_NAME = 'pig' 
      AND COLUMN_NAME = 'user_id'
);

-- 如果字段不存在，则添加
SET @sql = IF(
    @col_exists = 0,
    'ALTER TABLE pig ADD COLUMN user_id VARCHAR(64) NOT NULL DEFAULT ''default_user'' COMMENT ''用户ID（租户隔离）'' AFTER id',
    'SELECT ''Column user_id already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 为现有数据设置默认值（如果需要）
UPDATE pig 
SET user_id = 'demo_user_001' 
WHERE user_id = 'default_user';

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_pig_user_id ON pig(user_id);
CREATE INDEX IF NOT EXISTS idx_pig_user_score ON pig(user_id, score);

-- 验证迁移结果
SELECT 
    COUNT(*) AS total_records,
    COUNT(DISTINCT user_id) AS unique_users,
    user_id,
    COUNT(*) AS count_per_user
FROM pig
GROUP BY user_id;

-- ============================================
-- 迁移完成
-- ============================================
