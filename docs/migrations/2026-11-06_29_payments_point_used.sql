-- PR #29 결제 포인트 사용액: payments.point_used (docs/design/payments.md)
-- 실행: docker compose exec -T postgres psql -U lastcall -d lastcall < docs/migrations/2026-11-06_29_payments_point_used.sql
-- 다시 실행해도 안전합니다. 옛 인라인 CHECK(payments_point_used_check)가 있어도 이름 있는 제약을 추가하며 중복은 무해합니다.
BEGIN;

ALTER TABLE payments ADD COLUMN IF NOT EXISTS point_used INTEGER NOT NULL DEFAULT 0;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'ck_payments_point_used' AND conrelid = 'public.payments'::regclass) THEN
    ALTER TABLE payments ADD CONSTRAINT ck_payments_point_used CHECK (point_used >= 0);
  END IF;
END $$;

COMMIT;
