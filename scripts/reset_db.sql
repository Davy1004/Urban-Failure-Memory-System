-- Destructive. Wipes the entire UFMS database.
-- Only run this when you intend to lose every loaded row.
--   docker exec -i ufms-mysql mysql -uroot -proot < scripts/reset_db.sql
--   docker exec -i ufms-mysql mysql -uroot -proot < ufms_schema.sql
DROP DATABASE IF EXISTS ufms;
