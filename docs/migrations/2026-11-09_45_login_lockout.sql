-- PR #45 로그인 잠금: users.failed_login_count, login_locked_until (docs/design/auth.md)
-- 실행: docker compose exec -T postgres psql -U lastcall -d lastcall < docs/migrations/2026-11-09_45_login_lockout.sql
-- 다시 실행해도 안전합니다.
BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS login_locked_until TIMESTAMPTZ;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'ck_users_failed_login_nonneg' AND conrelid = 'public.users'::regclass) THEN
    ALTER TABLE users ADD CONSTRAINT ck_users_failed_login_nonneg CHECK (failed_login_count >= 0);
  END IF;
END $$;

COMMIT;
