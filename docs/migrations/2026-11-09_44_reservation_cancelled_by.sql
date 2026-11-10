-- PR #44 예약 취소 주체: pickup_reservations.cancelled_by (docs/design/reservations.md)
-- 실행: docker compose exec -T postgres psql -U lastcall -d lastcall < docs/migrations/2026-11-09_44_reservation_cancelled_by.sql
-- 다시 실행해도 안전합니다.
BEGIN;

ALTER TABLE pickup_reservations ADD COLUMN IF NOT EXISTS cancelled_by VARCHAR(20);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'ck_reservation_cancelled_by'
                   AND conrelid = 'public.pickup_reservations'::regclass) THEN
    ALTER TABLE pickup_reservations ADD CONSTRAINT ck_reservation_cancelled_by
      CHECK (cancelled_by IN ('CUSTOMER', 'STORE', 'SYSTEM'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'ck_reservation_cancelled_by_status'
                   AND conrelid = 'public.pickup_reservations'::regclass) THEN
    ALTER TABLE pickup_reservations ADD CONSTRAINT ck_reservation_cancelled_by_status
      CHECK (cancelled_by IS NULL OR status = 'CANCELLED');
  END IF;
END $$;

COMMIT;
