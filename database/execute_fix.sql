-- 生长曲线修复脚本
USE liangtowwu;

-- 添加area字段
ALTER TABLE pig ADD COLUMN IF NOT EXISTS area VARCHAR(64) DEFAULT '未分配区域' COMMENT '所在区域' AFTER breed;

-- 添加current_weight_kg字段
ALTER TABLE pig ADD COLUMN IF NOT EXISTS current_weight_kg DECIMAL(10, 2) DEFAULT 0.0 COMMENT '当前体重（kg）' AFTER area;

-- 添加current_month字段
ALTER TABLE pig ADD COLUMN IF NOT EXISTS current_month INT DEFAULT 0 COMMENT '当前月龄' AFTER current_weight_kg;

-- 更新PIG001数据
UPDATE pig SET 
    area = '猪舍A',
    current_weight_kg = 45.0,
    current_month = 3
WHERE id = 'PIG001';

-- 更新PIG002数据
UPDATE pig SET 
    area = '猪舍B',
    current_weight_kg = 40.5,
    current_month = 2
WHERE id = 'PIG002';

-- 验证结果
SELECT 'Database update completed!' AS status;
SELECT id, breed, area, current_weight_kg, current_month, score, issue FROM pig;
