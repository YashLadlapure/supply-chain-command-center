-- Read-only database user for the question tool.
-- The password is passed in when the script runs, so it never appears in the repo.
-- Safe to run again: it keeps the user and resets the password.
--
--   psql -h localhost -U postgres -d supply_chain -v reader_password=YOUR_PASSWORD -f rag/setup_reader.sql
--
-- If psql is not installed (PowerShell):
--   Get-Content rag/setup_reader.sql | docker exec -i sc-postgres psql -U postgres -d supply_chain -v reader_password=YOUR_PASSWORD

SELECT 'CREATE ROLE rag_reader LOGIN'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rag_reader') \gexec

ALTER ROLE rag_reader PASSWORD :'reader_password';

GRANT CONNECT ON DATABASE supply_chain TO rag_reader;
GRANT USAGE ON SCHEMA public TO rag_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO rag_reader;

-- run_pipeline.py drops and recreates the tables, which removes the grant above.
-- This gives rag_reader SELECT on tables and views created from now on.
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO rag_reader;

-- Every session of this user starts read-only and stops any query after 5 seconds
ALTER ROLE rag_reader SET default_transaction_read_only = on;
ALTER ROLE rag_reader SET statement_timeout = '5s';
