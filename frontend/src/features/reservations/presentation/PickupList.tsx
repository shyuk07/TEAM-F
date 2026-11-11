import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { Skeleton } from '@/shared/ui/Skeleton';
import { PICKUP_MESSAGES } from '../domain/pickupMessages';
import type { StoreReservation } from '../domain/storeReservation';
import { PickupRow } from './PickupRow';
import type { PickupTab } from './PickupTabs';

// open-issues: O1 픽업 시간·고객 정보·픽업 코드는 목록에 없음
export type PickupListProps = {
  status: 'loading' | 'success' | 'error';
  reservations: StoreReservation[];
  tab: PickupTab;
  selectedId?: string | null;
  onSelect?: (reservation: StoreReservation) => void;
  onRetry?: () => void;
};

export function PickupList({
  status,
  reservations,
  tab,
  selectedId,
  onSelect,
  onRetry,
}: PickupListProps) {
  if (status === 'loading') {
    return (
      <div style={{ display: 'grid', gap: 'var(--s2)' }}>
        <Skeleton />
        <Skeleton />
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="warn" style={{ textAlign: 'center', padding: 'var(--s4) var(--s2)' }}>
        <p>{PICKUP_MESSAGES.LOAD_FAILED}</p>
        {onRetry && (
          <Button size="sm" onClick={onRetry} style={{ marginTop: 'var(--s2)' }}>
            {PICKUP_MESSAGES.RETRY}
          </Button>
        )}
      </div>
    );
  }

  if (reservations.length === 0) {
    const emptyMsg = tab === 'waiting' ? PICKUP_MESSAGES.EMPTY_WAITING : PICKUP_MESSAGES.EMPTY_DONE;
    return <EmptyState title={emptyMsg} />;
  }

  return (
    <div className="list">
      <div className="tr th">
        <span className="lbl">상품 · 수량</span>
        <span className="lbl">픽업 시간</span>
        <span className="lbl">금액</span>
        <span className="lbl">예약 시각</span>
        <span />
      </div>
      {reservations.map((r) => (
        <PickupRow
          key={r.id}
          reservation={r}
          isSelected={selectedId === r.id}
          onClick={onSelect ? () => onSelect(r) : undefined}
        />
      ))}
    </div>
  );
}
