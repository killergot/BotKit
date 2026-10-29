-- psql variables app_password, migration_password and db_name are supplied on stdin.
-- No tables or records are copied, recreated or removed.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'botkit_app') THEN
        CREATE ROLE botkit_app LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'botkit_migrator') THEN
        CREATE ROLE botkit_migrator LOGIN;
    END IF;
END $$;
ALTER ROLE botkit_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 12 PASSWORD :'app_password';
ALTER ROLE botkit_migrator WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 6 PASSWORD :'migration_password';
ALTER ROLE botkit_app SET statement_timeout = '30s';
ALTER ROLE botkit_app SET idle_in_transaction_session_timeout = '60s';
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CONNECT, TEMPORARY ON DATABASE :"db_name" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db_name" TO botkit_app, botkit_migrator;
GRANT USAGE ON SCHEMA public TO botkit_app;
GRANT USAGE, CREATE ON SCHEMA public TO botkit_migrator;
DO $$ DECLARE r record; BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname='public' LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO botkit_migrator', r.tablename);
    END LOOP;
    FOR r IN SELECT sequencename FROM pg_sequences WHERE schemaname='public' LOOP
        EXECUTE format('ALTER SEQUENCE public.%I OWNER TO botkit_migrator', r.sequencename);
    END LOOP;
END $$;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.users, public.medicine_kits, public.medicines,
    public.medicine_items, public.user_medicine_kits, public.reminders TO botkit_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO botkit_app;
REVOKE ALL ON public.alembic_version FROM botkit_app;
ALTER DEFAULT PRIVILEGES FOR ROLE botkit_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO botkit_app;
ALTER DEFAULT PRIVILEGES FOR ROLE botkit_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO botkit_app;
COMMIT;
