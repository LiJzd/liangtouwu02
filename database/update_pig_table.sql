-- ==========================================
-- 数据库更新脚本：为pig表添加生长曲线所需字段
-- ==========================================
-- 执行时间：2026-04-02
-- 目的：支持生长曲线功能

USE liangtowwu;

-- 1. 检查并添加area字段
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'liangtowwu' 
    AND TABLE_NAME = 'pig' 
    AND COLUMN_NAME = 'area'
);

SET @sql = IF(
    @col_exists = 0,
    'ALTER TABLE pig ADD COLUMN area VARCHAR(64) DEFAULT ''未分配区域'' COMMENT ''所在区域'' AFTER breed',
    'SELECT ''Column area already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. 检查并添加current_weight_kg字段
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'liangtowwu' 
    AND TABLE_NAME = 'pig' 
    AND COLUMN_NAME = 'current_weight_kg'
);

SET @sql = IF(
    @col_exists = 0,
    'ALTER TABLE pig ADD COLUMN current_weight_kg DECIMAL(10, 2) DEFAULT 0.0 COMMENT ''当前体重（kg）'' AFTER area',
    'SELECT ''Column current_weight_kg already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 3. 检查并添加current_month字段
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'liangtowwu' 
    AND TABLE_NAME = 'pig' 
    AND COLUMN_NAME = 'current_month'
);

SET @sql = IF(
    @col_exists = 0,
    'ALTER TABLE pig ADD COLUMN current_month INT DEFAULT 0 COMMENT ''当前月龄'' AFTER current_weight_kg',
    'SELECT ''Column current_month already exists'' AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 4. 更新现有数据（为PIG001和PIG002设置真实数据）
UPDATE pig SET 
    area = '猪舍A',
    current_weight_kg = 45.0,
    current_month = 3
WHERE id = 'PIG001';

UPDATE pig SET 
    area = '猪舍B',
    current_weight_kg = 40.5,
    current_month = 2
WHERE id = 'PIG002';

-- 5. 为其他猪只设置默认值（如果有的话）
UPDATE pig SET 
    area = CASE 
        WHEN id LIKE '%001%' THEN '猪舍A'
        WHEN id LIKE '%002%' THEN '猪舍B'
        ELSE '猪舍C'
    END,
    current_weight_kg = 30.0 + (RAND() * 40),
    current_month = 2 + FLOOR(RAND() * 4)
WHERE area IS NULL OR area = '未分配区域';

-- 6. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_pig_breed ON pig(breed);
CREATE INDEX IF NOT EXISTS idx_pig_area ON pig(area);
CREATE INDEX IF NOT EXISTS idx_pig_current_month ON pig(current_month);

-- 7. 验证更新结果
SELECT 
    '数据库更新完成' AS status,
    COUNT(*) AS total_pigs,
    SUM(CASE WHEN current_weight_kg IS NOT NULL AND current_weight_kg > 0 THEN 1 ELSE 0 END) AS pigs_with_weight,
    SUM(CASE WHEN current_month IS NOT NULL AND current_month > 0 THEN 1 ELSE 0 END) AS pigs_with_month
FROM pig;

-- 8. 显示示例数据
SELECT 
    id,
    breed,
    area,
    current_weight_kg,
    current_month,
    score,
    issue
FROM pig
LIMIT 5;
