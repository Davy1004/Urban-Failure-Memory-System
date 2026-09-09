-- Grants the test suite needs. Runs once, on first initialisation of the volume.
--
-- `tests/test_migrations.py` proves that `alembic upgrade head` and
-- `ufms_schema.sql` produce an identical `information_schema`. To do that it
-- builds a throwaway database each way, named `ufms_t_<something>`. The `ufms`
-- user created by docker-compose owns only the `ufms` database, so CREATE
-- DATABASE is denied and **the test skips instead of running**.
--
-- That skip is why this file exists. The check that caught 178 model-vs-schema
-- differences was silently not running on any machine but the one it was written
-- on, where the grant had been added by hand and recorded nowhere.
--
-- Scoped to the `ufms_t_` prefix on purpose: the test user gains no rights over
-- any other database on the server.
GRANT ALL PRIVILEGES ON `ufms\_t\_%`.* TO 'ufms'@'%';
FLUSH PRIVILEGES;
