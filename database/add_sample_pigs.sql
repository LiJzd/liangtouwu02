-- 批量导入生猪数据脚本 (两头乌专场)
-- 目的：扩充数据库规模，解决“全群 2 头”的问题，展示真实比例的猪场监控数据。

USE liangtowwu;

-- 预先清理可能重复的测试编号 (可选，根据实际需要执行)
-- DELETE FROM pig WHERE id LIKE 'PIG%';

-- 批量插入 100 条两头乌记录
INSERT IGNORE INTO pig (id, breed, score, issue, body_temp, activity_level, created_at) VALUES
('PIG003', '两头乌', 98, '健康', 38.4, 85, NOW()),
('PIG004', '两头乌', 92, '健康', 38.6, 78, NOW()),
('PIG005', '两头乌', 95, '健康', 38.4, 82, NOW()),
('PIG006', '两头乌', 91, '健康', 38.7, 75, NOW()),
('PIG007', '两头乌', 45, '食欲下降', 39.5, 40, NOW()),
('PIG008', '两头乌', 96, '健康', 38.5, 88, NOW()),
('PIG009', '两头乌', 88, '健康', 38.3, 70, NOW()),
('PIG010', '两头乌', 94, '健康', 38.6, 84, NOW()),
('PIG011', '两头乌', 97, '健康', 38.5, 90, NOW()),
('PIG012', '两头乌', 55, '精神不振', 39.2, 50, NOW()),
('PIG013', '两头乌', 93, '健康', 38.4, 80, NOW()),
('PIG014', '两头乌', 90, '健康', 38.8, 72, NOW()),
('PIG015', '两头乌', 95, '健康', 38.5, 85, NOW()),
('PIG016', '两头乌', 98, '健康', 38.4, 92, NOW()),
('PIG017', '两头乌', 62, '活跃度下降', 39.0, 35, NOW()),
('PIG018', '两头乌', 94, '健康', 38.6, 88, NOW()),
('PIG019', '两头乌', 91, '健康', 38.7, 78, NOW()),
('PIG020', '两头乌', 96, '健康', 38.5, 86, NOW());

-- 使用存储过程批量生成剩余数据
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS PopulatePigs()
BEGIN
    DECLARE i INT DEFAULT 21;
    DECLARE score_val INT;
    DECLARE temp_val DECIMAL(10,2);
    DECLARE issue_val VARCHAR(255);
    
    WHILE i <= 100 DO
        -- 模拟约 10% 的异常比例
        IF i % 10 = 0 THEN
            SET score_val = 40 + FLOOR(RAND() * 30);
            SET temp_val = 39.5 + (RAND() * 0.8);
            SET issue_val = '疑似热应激';
        ELSE
            SET score_val = 85 + FLOOR(RAND() * 15);
            SET temp_val = 38.2 + (RAND() * 0.6);
            SET issue_val = '健康';
        END IF;
        
        INSERT IGNORE INTO pig (id, breed, score, issue, body_temp, activity_level, created_at)
        VALUES (
            CONCAT('PIG', LPAD(i, 3, '0')),
            '两头乌',
            score_val,
            issue_val,
            temp_val,
            score_val - 10,
            NOW()
        );
        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

CALL PopulatePigs();
DROP PROCEDURE PopulatePigs;

-- 补齐迁移脚本中包含的扩展字段 (如果由于表结构已变更)
-- 注意：这些字段默认在 update_pig_table.sql 中已有降级填充逻辑，此处手动同步部分典型数据
UPDATE pig SET area = '一号舍-A区', current_weight_kg = 42.5, current_month = 3 WHERE id = 'PIG003';
UPDATE pig SET area = '二号舍-B区', current_weight_kg = 85.0, current_month = 7 WHERE id = 'PIG020';
UPDATE pig SET area = '隔离区', current_weight_kg = 35.5, current_month = 2 WHERE id IN ('PIG007', 'PIG012', 'PIG017');

-- 为所有“未分配区域”的猪只随机分配区域，统一品种为两头乌
UPDATE pig SET 
    breed = '两头乌',
    area = CASE 
        WHEN id LIKE '%1' THEN '一号舍-A区'
        WHEN id LIKE '%2' THEN '一号舍-B区'
        WHEN id LIKE '%3' THEN '二号舍-A区'
        WHEN id LIKE '%4' THEN '二号舍-B区'
        WHEN id LIKE '%5' THEN '三号舍-C区'
        WHEN id LIKE '%6' THEN '四号舍-D区'
        WHEN id LIKE '%7' THEN '育肥区'
        WHEN id LIKE '%8' THEN '母猪舍'
        ELSE '隔离区'
    END
WHERE area IS NULL OR area = '未分配区域';

-- 打印统计结果
SELECT '数据导入完成' AS message, COUNT(*) AS total_pigs FROM pig;
