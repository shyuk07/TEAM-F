-- PR #25 관리자 기능: 회원·포인트·상점·할인상품 컬럼과 CHECK 추가 (docs/design/admin.md 2.4절)
-- 실행: docker compose exec -T postgres psql -U lastcall -d lastcall < docs/migrations/2026-11-05_25_admin_columns.sql
-- 다시 실행해도 안전합니다(IF NOT EXISTS, pg_constraint 이름 확인).
BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'APPROVED';
ALTER TABLE users ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS rejected_reason VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_reason VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_until TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_reason VARCHAR(500);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'ck_users_status' AND conrelid = 'public.users'::regclass) THEN
    ALTER TABLE users ADD CONSTRAINT ck_users_status
      CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED', 'WITHDRAWN'));
  END IF;
END $$;

-- point_log의 point_type CHECK(ck_point_log_type)는 2026-11-06_30 파일이 최종 값으로 처리한다.
ALTER TABLE point_log ADD COLUMN IF NOT EXISTS reason VARCHAR(500);
ALTER TABLE point_log ADD COLUMN IF NOT EXISTS balance_after INTEGER;
ALTER TABLE point_log ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id);

ALTER TABLE stores ADD COLUMN IF NOT EXISTS suspended_reason VARCHAR(500);
ALTER TABLE stores ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ;
ALTER TABLE stores ADD COLUMN IF NOT EXISTS closed_reason VARCHAR(500);

ALTER TABLE discount_offers ADD COLUMN IF NOT EXISTS suspended_reason VARCHAR(500);
ALTER TABLE discount_offers ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ;

-- status CHECK는 옛 이름이 DB마다 다를 수 있다. ck_offer_status가 아닌 status CHECK는 모두 지우고,
-- ck_offer_status도 SUSPENDED가 없는 옛 정의면 지운 뒤 최신 정의로 다시 만든다.
DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN
    SELECT conname, pg_get_constraintdef(oid) AS def
    FROM pg_constraint
    WHERE conrelid = 'public.discount_offers'::regclass AND contype = 'c'
      AND pg_get_constraintdef(oid) ~ '\mstatus\M'
  LOOP
    IF r.conname <> 'ck_offer_status' OR r.def NOT LIKE '%SUSPENDED%' THEN
      EXECUTE format('ALTER TABLE discount_offers DROP CONSTRAINT %I', r.conname);
    END IF;
  END LOOP;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'ck_offer_status' AND conrelid = 'public.discount_offers'::regclass) THEN
    ALTER TABLE discount_offers ADD CONSTRAINT ck_offer_status
      CHECK (status IN ('SCHEDULED', 'ON_SALE', 'SOLD_OUT', 'CLOSED', 'SUSPENDED'));
  END IF;
END $$;

COMMIT;
