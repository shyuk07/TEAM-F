import { Box } from '@/shared/ui/Box';
import { formatHm } from '@/shared/lib/format';
import { handoverLine } from '../domain/reservationFormat';
import type { StoreReservation } from '../domain/storeReservation';

export type HandoverNoticeProps = {
  lastDone: {
    reservation: StoreReservation;
    doneAt: Date;
  };
};

export function HandoverNotice({ lastDone }: HandoverNoticeProps) {
  const { reservation } = lastDone;

  return (
    <Box tone="done">
      <div className="row">
        <b style={{ color: 'var(--ok)' }}>✓ 픽업 완료</b>
        <span className="sp" />
        <span className="m">방금</span>
      </div>
      <div className="t" style={{ marginTop: 'var(--s1)' }}>
        {handoverLine(reservation)}
      </div>
      <div className="m" style={{ marginTop: 'var(--s1)' }}>
        {formatHm(reservation.createdAt)} 예약 · 완료 목록으로 옮겼어요
      </div>
    </Box>
  );
}
