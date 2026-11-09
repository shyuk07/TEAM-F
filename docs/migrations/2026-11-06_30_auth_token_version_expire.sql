-- PR #30 인증: 토큰 버전·유지 jti, 포인트 유형 EXPIRE (docs/design/auth.md 15.3.3절)
-- 실행: docker compose exec -T postgres psql -U lastcall -d lastcall < docs/migrations/2026-11-06_30_auth_token_version_expire.sql
-- 다시 실행해도 안전합니다.
-- password_reset_codes 테이블은 서버 시작 시 create_all이 만들므로 CREATE 문이 없다.
-- 단 옛 모양으로 이미 있으면 아래 마지막 블록이 이름 있는 CHECK를 보충한다(C-4).
BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_keep_jti TEXT;

-- ck_point_log_type: 정의에 EXPIRE가 없으면 지우고 6개 값으로 다시 만든다.
DO $$
DECLARE def TEXT;
BEGIN
  SELECT pg_get_constraintdef(oid) INTO def
  FROM pg_constraint
  WHERE conname = 'ck_point_log_type' AND conrelid = 'public.point_log'::regclass;
  IF def IS NOT NULL AND def NOT LIKE '%EXPIRE%' THEN
    ALTER TABLE point_log DROP CONSTRAINT ck_point_log_type;
    def := NULL;
  END IF;
  IF def IS NULL THEN
    ALTER TABLE point_log ADD CONSTRAINT ck_point_log_type
      CHECK (point_type IN ('EARN', 'USE', 'RESTORE', 'REVOKE', 'GRANT', 'EXPIRE'));
  END IF;
END $$;

DO $$ BEGIN
  IF to_regclass('public.password_reset_codes') IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM pg_constraint
                     WHERE conname = 'ck_password_reset_attempts_nonneg'
                       AND conrelid = 'public.password_reset_codes'::regclass) THEN
    ALTER TABLE password_reset_codes
      ADD CONSTRAINT ck_password_reset_attempts_nonneg CHECK (failed_attempts >= 0);
  END IF;
END $$;

COMMIT;
