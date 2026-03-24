-- 添加 last_login 字段到 users 表
-- 执行此 SQL 来添加缺失的列

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS last_login TIMESTAMP NULL;

-- 验证列是否添加成功
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'last_login';
