-- ============================================
-- 回滚脚本: 移除租户隔离字段
-- 版本: 001
-- 日期: 2026-03-22
-- 警告: 此操作将删除 user_id 字段及相关索引
-- ============================================

-- 删除索引
DROP INDEX IF EXISTS idx_pig_user_score ON pig;
DROP INDEX IF EXISTS idx_pig_user_id ON pig;

-- 删除字段
ALTER TABLE pig DROP COLUMN IF EXISTS user_id;

-- 验证回滚结果
DESCRIBE pig;

-- ============================================
-- 回滚完成
-- ============================================
