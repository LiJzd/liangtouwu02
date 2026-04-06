-- ==========================================
-- 数据库迁移脚本：为pig表添加生长曲线所需字段
-- ==========================================
-- 执行时间：2026-04-02
-- 目的：支持生长曲线和每日简报功能

-- 1. 为pig表添加新字段
ALTER TABLE pig 
ADD COLUMN IF NOT EXISTS breed VARCHAR(32) DEFAULT '未知品种' COMMENT '猪的品种',
ADD COLUMN IF NOT EXISTS area VARCHAR(64) DEFAULT '未分配区域' COMMENT '所在区域',
ADD COLUMN IF NOT EXISTS current_weight_kg DECIMAL(10, 2) DEFAULT 0.0 COMMENT '当前体重（kg）',
ADD COLUMN IF NOT EXISTS current_month INT DEFAULT 0 COMMENT '当前月龄';

-- 2. 更新现有数据（示例数据）
UPDATE pig SET 
    breed = '杜洛克',
    area = '一号舍',
    current_weight_kg = 45.0,
    current_month = 3
WHERE id = 'PIG-001';

UPDATE pig SET 
    breed = '陆川猪',
    area = '一号舍',
    current_weight_kg = 52.3,
    current_month = 4
WHERE id = 'PIG-023';

UPDATE pig SET 
    breed = '两头乌',
    area = '三号舍',
    current_weight_kg = 40.5,
    current_month = 3
WHERE id = 'PIG-105';

-- 3. 为其他猪只设置默认值
UPDATE pig SET 
    breed = CASE 
        WHEN id LIKE '%001%' THEN '杜洛克'
        WHEN id LIKE '%002%' THEN '长白猪'
        WHEN id LIKE '%003%' THEN '大白猪'
        ELSE '两头乌'
    END,
    area = CASE 
        WHEN CAST(SUBSTRING(id, 5) AS UNSIGNED) % 3 = 0 THEN '一号舍'
        WHEN CAST(SUBSTRING(id, 5) AS UNSIGNED) % 3 = 1 THEN '二号舍'
        ELSE '三号舍'
    END,
    current_weight_kg = 30.0 + (RAND() * 30),
    current_month = 2 + FLOOR(RAND() * 4)
WHERE breed IS NULL OR breed = '未知品种';

-- 4. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_pig_breed ON pig(breed);
CREATE INDEX IF NOT EXISTS idx_pig_area ON pig(area);
CREATE INDEX IF NOT EXISTS idx_pig_current_month ON pig(current_month);

-- 5. 验证数据
SELECT 
    id,
    breed,
    area,
    current_weight_kg,
    current_month,
    score,
    issue
FROM pig
LIMIT 10;
